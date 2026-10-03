"""Ticket triage queue and review workflow."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db
from app.model_client import ModelTimeout, ModelUnavailable, get_client
from app.models import (
    ModelPayload,
    Ticket,
    TicketCreate,
    TicketPage,
    TicketReviewChange,
    TicketStatus,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

VALID_CATEGORIES = {"billing", "access", "data", "outage", "general"}
VALID_PRIORITIES = {"low", "normal", "high"}


def _ticket_from_row(row: sqlite3.Row) -> Ticket:
    payload = json.loads(row["model_value"]) if row["model_value"] else {}
    return Ticket(
        id=row["id"],
        subject=row["subject"],
        body=row["body"],
        category=row["category"],
        priority=row["priority"],
        team=row["team"],
        draft_reply=row["draft_reply"],
        status=row["status"],
        model=ModelPayload(
            value=payload,
            confidence=float(row["model_confidence"]),
            model_version=row["model_version"],
            latency_ms=int(row["model_latency_ms"]),
        ),
    )


def _validate_ticket_input(subject: str, body: str) -> None:
    if len(subject) > 500 or len(body) > 10_000:
        raise HTTPException(status_code=422, detail="subject and body must be within the configured length limits")
    if not subject.strip() and not body.strip():
        raise HTTPException(status_code=422, detail="subject or body must contain non-whitespace text")


@router.post("", response_model=Ticket, status_code=201)
def create_ticket(body: TicketCreate, db: sqlite3.Connection = Depends(get_db)) -> Ticket:
    """Submit a ticket for model-based triage and human review."""
    subject = body.subject or ""
    issue = body.body or ""
    model_subject = subject if subject.strip() else ""
    model_body = issue if issue.strip() else ""
    _validate_ticket_input(subject, issue)

    try:
        result = get_client().complete("classify_ticket", {"subject": model_subject, "body": model_body})
    except ModelTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    raw = result.value if isinstance(result.value, dict) else {"category": "general", "priority": "normal", "team": "triage", "draft_reply": str(result.value)}
    category = str(raw.get("category", "general"))
    priority = str(raw.get("priority", "normal"))
    team = str(raw.get("team", "triage")).strip()
    draft_reply = str(raw.get("draft_reply", "Thanks for writing in. I am taking a look and will come back to you.")).strip()

    if category not in VALID_CATEGORIES:
        category = "general"
    if priority not in VALID_PRIORITIES:
        priority = "normal"
    if not team:
        team = "triage"
    if not draft_reply:
        draft_reply = "Thanks for writing in. I am taking a look and will come back to you."

    row_count = db.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]
    ticket_id = f"T-{row_count + 1:03d}"
    model_value = json.dumps(raw)

    db.execute(
        "INSERT INTO tickets (id, subject, body, category, priority, team, draft_reply, status, model_value, model_confidence, model_version, model_latency_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ticket_id,
            subject,
            issue,
            category,
            priority,
            team,
            draft_reply,
            "pending_review",
            model_value,
            float(result.confidence),
            result.model_version,
            result.latency_ms,
        ),
    )
    db.commit()

    row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return _ticket_from_row(row)


@router.get("", response_model=TicketPage)
def list_tickets(
    status: TicketStatus = Query("pending_review"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> TicketPage:
    """List the review queue by status."""
    total = db.execute("SELECT COUNT(*) AS n FROM tickets WHERE status = ?", (status,)).fetchone()["n"]
    rows = db.execute(
        "SELECT * FROM tickets WHERE status = ? ORDER BY id LIMIT ? OFFSET ?",
        (status, limit, offset),
    ).fetchall()
    return TicketPage(items=[_ticket_from_row(r) for r in rows], total=total, limit=limit, offset=offset)


@router.patch("/{ticket_id}/review", response_model=Ticket)
def review_ticket(
    ticket_id: str,
    body: TicketReviewChange,
    db: sqlite3.Connection = Depends(get_db),
) -> Ticket:
    """Accept the model's recommendation or replace a subset of it."""
    # Lock before reading the state. Otherwise two requests can both observe
    # pending_review before either attempts its conditional update.
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"no ticket with id {ticket_id}", headers={})

    if body.action == "accept":
        cur = db.execute(
            "UPDATE tickets SET status = ? WHERE id = ? AND status = 'pending_review'",
            ("accepted", ticket_id),
        )
        if cur.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=409, detail=f"ticket {ticket_id} is no longer pending review")
    else:
        touched = [
            ("category", body.category),
            ("priority", body.priority),
            ("team", body.team),
            ("draft_reply", body.draft_reply),
        ]
        if not any(value is not None for _, value in touched):
            raise HTTPException(status_code=422, detail="at least one review field must be supplied")
        assignments = []
        values: list[Any] = []
        for column, value in touched:
            if value is not None:
                if isinstance(value, str) and not value.strip():
                    raise HTTPException(status_code=422, detail=f"{column} must contain non-whitespace text")
                assignments.append(f"{column} = ?")
                values.append(value)
        assignments.append("status = ?")
        values.extend(["changed", ticket_id])
        cur = db.execute(
            f"UPDATE tickets SET {', '.join(assignments)} WHERE id = ? AND status = 'pending_review'",
            values,
        )
        if cur.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=409, detail=f"ticket {ticket_id} is no longer pending review")

    final = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    db.commit()
    return _ticket_from_row(final)
