"""Acceptance criteria for the ticket triage flow."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

import app.model_client as mc


def _create_ticket(client, monkeypatch, *, stub=None, subject="Refund for duplicate charge", body="I was billed twice for September."):
    client_stub = stub or mc.StubModelClient()
    monkeypatch.setattr(mc, "_default_client", client_stub)
    response = client.post("/tickets", json={"subject": subject, "body": body})
    assert response.status_code == 201, response.text
    return response.json()


def test_ac1_classification_returns_created_ticket(client, monkeypatch, stub):
    monkeypatch.setattr(mc, "_default_client", stub)

    response = client.post(
        "/tickets",
        json={"subject": "Refund for duplicate charge", "body": "I was billed twice for September."},
    )
    body = response.json()

    assert response.status_code == 201
    assert body["subject"] == "Refund for duplicate charge"
    assert body["body"] == "I was billed twice for September."
    assert body["category"] == "billing"
    assert body["priority"] == "normal"
    assert body["team"] == "finance-ops"
    assert body["status"] == "pending_review"
    assert body["draft_reply"]
    assert body["model"]["value"]["category"] == "billing"
    assert body["model"]["model_version"] == "v1"
    assert body["model"]["confidence"] > 0


def test_ac2_subject_only_is_classified(client, monkeypatch, stub):
    monkeypatch.setattr(mc, "_default_client", stub)

    response = client.post("/tickets", json={"subject": "Refund for duplicate charge", "body": ""})
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"

    response = client.post("/tickets", json={"subject": "", "body": "I was billed twice for September."})
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"


def test_ac3_invalid_ticket_input_returns_422_without_creation(client, monkeypatch, stub):
    monkeypatch.setattr(mc, "_default_client", stub)

    response = client.post("/tickets", json={"subject": "   ", "body": "   "})
    assert response.status_code == 422
    assert client.get("/tickets").json()["total"] == 0

    response = client.post("/tickets", json={"subject": "x" * 501, "body": "body"})
    assert response.status_code == 422
    assert client.get("/tickets").json()["total"] == 0

    created = _create_ticket(client, monkeypatch, stub=stub)
    response = client.patch(
        f"/tickets/{created['id']}/review",
        json={"action": "change", "category": "not-a-valid-category"},
    )
    assert response.status_code == 422
    assert client.get("/tickets", params={"status": "pending_review"}).json()["total"] == 1


def test_ac4_empty_review_queue_returns_empty_page(client):
    response = client.get("/tickets")
    body = response.json()

    assert response.status_code == 200
    assert body["items"] == []
    assert body["total"] == 0
    assert body["limit"] == 50
    assert body["offset"] == 0


def test_ac5_low_confidence_suggestion_remains_pending(client, monkeypatch, stub):
    stub.config.wrongness = 1.0
    monkeypatch.setattr(mc, "_default_client", stub)

    response = client.post(
        "/tickets",
        json={"subject": "Refund for duplicate charge", "body": "I was billed twice for September."},
    )
    body = response.json()

    assert response.status_code == 201
    assert body["status"] == "pending_review"
    assert body["model"]["confidence"] < 0.5


def test_ac6_accept_preserves_suggestions(client, monkeypatch, stub):
    ticket = _create_ticket(client, monkeypatch, stub=stub)

    response = client.patch(f"/tickets/{ticket['id']}/review", json={"action": "accept"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "accepted"
    assert body["category"] == ticket["category"]
    assert body["priority"] == ticket["priority"]
    assert body["team"] == ticket["team"]
    assert body["draft_reply"] == ticket["draft_reply"]


def test_ac7_change_replaces_only_supplied_fields(client, monkeypatch, stub):
    ticket = _create_ticket(client, monkeypatch, stub=stub)

    response = client.patch(
        f"/tickets/{ticket['id']}/review",
        json={"action": "change", "priority": "high", "team": "identity"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "changed"
    assert body["priority"] == "high"
    assert body["team"] == "identity"
    assert body["category"] == ticket["category"]
    assert body["draft_reply"] == ticket["draft_reply"]
    assert body["model"] == ticket["model"]


@pytest.mark.skip(reason="Authorization is not implemented in this API yet.")
def test_ac8_unauthorized_review_returns_403_without_change(client, monkeypatch, stub):
    ticket = _create_ticket(client, monkeypatch, stub=stub)

    response = client.patch(
        f"/tickets/{ticket['id']}/review",
        json={"action": "accept"},
        headers={"X-User-Role": "readonly"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_ac9_review_of_missing_ticket_returns_not_found(client):
    response = client.patch("/tickets/T-999/review", json={"action": "accept"})
    body = response.json()

    assert response.status_code == 404
    assert body["code"] == "not_found"


def test_ac10_model_unavailable_returns_503_without_creation(client, monkeypatch, stub):
    stub.config.failure_rate = 1.0
    monkeypatch.setattr(mc, "_default_client", stub)

    response = client.post("/tickets", json={"subject": "Refund", "body": "I was billed twice"})
    body = response.json()

    assert response.status_code == 503
    assert body["code"] == "model_unavailable"
    assert client.get("/tickets").json()["total"] == 0


def test_ac11_model_timeout_returns_504_without_creation(client, monkeypatch, stub):
    stub.config.latency_ms = 10
    stub.config.timeout_ms = 1
    stub.config.sleep = False
    monkeypatch.setattr(mc, "_default_client", stub)

    response = client.post("/tickets", json={"subject": "Refund", "body": "I was billed twice"})
    body = response.json()

    assert response.status_code == 504
    assert body["code"] == "model_timeout"
    assert client.get("/tickets").json()["total"] == 0


def test_ac12_concurrent_reviews_allow_exactly_one_change(client, monkeypatch, stub):
    ticket = _create_ticket(client, monkeypatch, stub=stub)

    def review(payload):
        return client.patch(f"/tickets/{ticket['id']}/review", json=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(review, {"action": "change", "priority": "high"}),
            executor.submit(review, {"action": "change", "team": "identity"}),
        ]
        responses = [future.result() for future in futures]

    result_codes = sorted(r.status_code for r in responses)
    assert result_codes == [200, 409]

    final = client.get("/tickets", params={"status": "changed"}).json()
    assert final["total"] == 1
    assert final["items"][0]["status"] == "changed"
    assert final["items"][0]["team"] in {"identity", "finance-ops"}
