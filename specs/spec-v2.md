# Feature Specification — <feature name>

> Template for the Week 5 session and assignment. One feature per specification. If you are standing
> up a new system rather than adding to an existing one, you want a directory of these, not one long
> document.
>
> Fill every section. If a section does not apply, write *"n/a — <why>"* rather than deleting it; the
> empty section is information too.

**Status:** draft 
**Author:** Gulnar Aldasheva
**Reviewers:**
**Date:** October 2, 2026

---

## 1. Intent

Production Support teams must quickly understand incoming tickets and get them to the appropriate team best able to help. Inconsistent or delayed triage can leave urgent issues waiting or route requests to the wrong team. This feature adds an automated triage step: every incoming ticket is assigned a category, priority, and suggested team, plus a draft first reply, and queued for a human support agent to accept or change — not sent automatically.  

## 2. User stories

- As a support agent, I want each incoming ticket categorized, prioritized, and matched to a suggested team so that I can route it efficiently. 

- As a support agent, I want a suggested first reply saved as a draft so that I can respond faster without sending unreviewed text. 

- As a support agent with override permission, I want to change a suggested priority so that an underestimated urgent ticket isn't stuck behind the model's judgment. 

- As a support agent, I want to accept or correct the ticket suggestions so that the final triage reflects human judgment. 

## 3. Acceptance criteria

Numbered, concrete, and testable. Each one should be something you can write an assertion against.

1. Given a submitted ticket has a non-empty subject, body, or both, when it is classified successfully, then the response is HTTP 201 and contains its original text, category, priority, suggested team, draft reply, `pending_review` status, and model confidence and version.  
2. Given only the subject or only the body contains non-whitespace text, when the ticket is submitted, then classification succeeds using the provided text and the ticket enters `pending_review`.  
3. Given both subject and body are empty or whitespace-only, or either field exceeds its maximum length (500 characters for subject, 10,000 for body), when the ticket is submitted, then the API returns HTTP 422 and creates no ticket.  
4. Given no tickets are pending review, when the agent lists the default queue, then the response is HTTP 200 with `items: []` and `total: 0`.  
5. Given a ticket has been classified, when classification completes, then the ticket remains pending_review, no reply is sent, and no team assignment occurs until a human accepts or changes it. 
6. Given a ticket is pending review, when the agent submits `{"action": "accept"}`, then the response is HTTP 200, status becomes `accepted`, and the category, priority, team, and draft reply are unchanged.  
7. Given a ticket is pending review, when the agent submits `{"action": "change", ...}` with at least one valid replacement field, then the response is HTTP 200, status becomes `changed`, supplied values replace the suggestions, and omitted fields remain unchanged.  
8. Given an agent does not have permission to review a ticket, when they attempt to accept or change the ticket, then the system returns HTTP 403 and the ticket remains unchanged.
9. Given a requested ticket ID does not exist, when the agent submits a review for it, then the API returns HTTP 404 with code `not_found`.  
10. Given the model is unavailable, when a ticket is submitted, then the API returns HTTP 503 with code `model_unavailable` and creates no ticket.  
11. Given the model call times out, when a ticket is submitted, then the API returns HTTP 504 with code `model_timeout` and creates no ticket.  
12. Given two agents submit changes for the same pending ticket concurrently, when both requests complete, then exactly one returns HTTP 200, the other returns HTTP 409, and the ticket contains only the successful review's values.  

**Include the unhappy paths.** Empty input, bad input, no results, permission denied, the thing being down. This is where specifications earn their keep — it is the part an agent will not invent for you.

## 4. Scope and non-goals

**In scope:**
Classifying a submitted ticket into category, priority, suggested team, and a draft first reply via POST /tickets; exposing the model's confidence, version, and latency alongside its suggestions; listing tickets pending review via GET /tickets; letting a human agent accept a ticket's suggestions as-is or change one or more fields via PATCH /tickets/{ticket_id}/review; guaranteeing that no draft reply is ever sent and no ticket is ever routed automatically — every ticket requires an explicit human accept or change before it leaves pending_review.

**Explicitly out of scope:** 
Sending replies to ticket submitters; automatically routing or assigning tickets to teams; merging duplicate tickets; detecting spam or fraud; managing users, teams; reporting, analytics, and service-level-agreement tracking; changing or deleting tickets after human review.

## 5. Interfaces and contracts

Endpoints, function signatures, data shapes, events. Request and response examples. What callers can
rely on, and what is allowed to change later.

### `POST /tickets` — submit and classify an incoming ticket

Request body (at least one field must contain non-whitespace text):

```json
{"subject": "Refund for duplicate charge", "body": "I was billed twice for September."}
```

Returns HTTP 201 with the created ticket. The ticket is `pending_review`; classification suggestions are not approved or sent automatically.

```json
{
  "id": "T-031",
  "subject": "Refund for duplicate charge",
  "body": "I was billed twice for September.",
  "category": "billing",
  "priority": "normal",
  "team": "finance-ops",
  "draft_reply": "Thanks for writing in. I can see the charge you mean and I am checking it now.",
  "status": "pending_review",
  "model": {
    "value": {
      "category": "billing",
      "priority": "normal",
      "team": "finance-ops",
      "draft_reply": "Thanks for writing in. I can see the charge you mean and I am checking it now."
    },
    "confidence": 0.86,
    "model_version": "v1",
    "latency_ms": 0
  }
}
```

`category` is one of `billing`, `access`, `data`, `outage`, or `general`; `priority` is one of `low`, `normal`, or `high`. `team` and `draft_reply` are non-empty strings when supplied by the model. `model` preserves the raw model result, its confidence, version, and latency. An empty subject or empty body is allowed if the other has text; both empty or whitespace-only returns HTTP 422.

### `GET /tickets` — list the review queue

Query parameters: `status` (defaults to `pending_review`; accepted values: `untriaged`, `pending_review`, `accepted`, `changed`), `limit` (default 50, range 1–200), and `offset` (default 0, minimum 0). Returns HTTP 200 in the standard page shape; an empty queue returns `items: []` and `total: 0`.

```json
{
  "items": [{
    "id": "T-031",
    "subject": "Refund for duplicate charge",
    "body": "I was billed twice for September.",
    "category": "billing",
    "priority": "normal",
    "team": "finance-ops",
    "draft_reply": "Thanks for writing in. I can see the charge you mean and I am checking it now.",
    "status": "pending_review",
    "model": {
      "value": {
        "category": "billing",
        "priority": "normal",
        "team": "finance-ops",
        "draft_reply": "Thanks for writing in. I can see the charge you mean and I am checking it now."
      },
      "confidence": 0.86,
      "model_version": "v1",
      "latency_ms": 0
    }
  }],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### `PATCH /tickets/{ticket_id}/review` — accept or change suggestions

Accept the model's suggestions with `{"action": "accept"}`. To correct suggestions, send `{"action": "change", ...}` with at least one replacement field; allowed replacement fields are `category`, `priority`, `team`, and `draft_reply`. Fields omitted from a change request retain their current values. Returns HTTP 200 with the updated ticket and status `accepted` or `changed`, respectively. Neither action sends the draft reply.

```json
{"action": "change", "category": "access", "priority": "high", "team": "identity"}
```

Returns HTTP 200 with the complete updated ticket. Values not included in a `change` request, including the draft reply in this example, remain unchanged; the model result continues to show the original suggestions and their provenance.

```json
{
  "id": "T-031",
  "subject": "Refund for duplicate charge",
  "body": "I was billed twice for September.",
  "category": "access",
  "priority": "high",
  "team": "identity",
  "draft_reply": "Thanks for writing in. I can see the charge you mean and I am checking it now.",
  "status": "changed",
  "model": {
    "value": {
      "category": "billing",
      "priority": "normal",
      "team": "finance-ops",
      "draft_reply": "Thanks for writing in. I can see the charge you mean and I am checking it now."
    },
    "confidence": 0.86,
    "model_version": "v1",
    "latency_ms": 0
  }
}
```

### Errors and stable behavior

- Invalid request data—including an empty or whitespace-only subject/body pair, unsupported enum values, or invalid pagination values—returns HTTP 422. In this app, route-level validation uses the standard app error contract (`{"detail": "...", "code": "error"}` unless the status code is mapped to a documented contract code such as `404`, `409`, `503`, or `504`), while direct Pydantic validation failures can still surface FastAPI's default validation payload.

- A ticket ID that does not exist returns HTTP 404 with `{ "detail": "...", "code": "not_found" }`. A review submitted for a ticket that is no longer pending review returns HTTP 409 with `{ "detail": "...", "code": "conflict" }`; the existing ticket values remain unchanged.

- If the model is unavailable, ticket creation returns HTTP 503 with code `model_unavailable`. If the model times out, it returns HTTP 504 with code `model_timeout`. In either case, no ticket is created from that request.

- If two reviews race to resolve the same pending ticket, one may succeed; the other returns HTTP 409. The ticket has only one resulting set of reviewed values and one terminal status.

- The public interface is the ticket queue at `GET /tickets`; there is no separate single-ticket fetch endpoint in this increment. The list response exposes the current queue state after each review, and callers can rely on the field names, enum values, status transitions, pagination shape, and per-ticket model provenance described above. Model wording, confidence scores, latency, and suggested values may vary between calls and model versions. Suggestions remain unreviewed until a human resolves the ticket; the system does not automatically route tickets or send draft replies.

## 6. Constraints

Only the rows that apply to your feature; delete the rest.

- **Design system / UI:** n/a — this increment exposes an API only; no user interface is being added.
- **Security and privacy:** Do not log ticket bodies or draft replies. This feature does not add authentication or authorization; deployment must use the service's existing trusted access boundary. Ticket content is user-provided and must be treated as untrusted input.
- **Performance and input limits:** A subject is at most 500 characters and a body is at most 10,000 characters; at least one must contain non-whitespace text. Classify one ticket per request; bulk classification is out of scope. Queue pages default to 50 tickets and cannot exceed 200; `offset` is a non-negative integer. Do not promise a fixed successful response time because classification latency depends on the model; map model timeouts to HTTP 504.
- **API and compatibility:** Declare request and response shapes in `app/models.py`. List responses use `{items, total, limit, offset}`. Model calls use `app.model_client.get_client()` and responses preserve the model's raw value, confidence, version, and latency. Keep existing library and summary endpoints unchanged. Do not add an ORM, a new error shape, or business logic to `app/main.py`; use the existing status/error contract (404, 409, 503, 504 with `{detail, code}`, and FastAPI validation responses for 422).
- **Testing:** Use the `client` fixture backed by a throwaway database and the `stub` model fixture. Name tests after their acceptance criterion (`test_ac<N>_...`) and run the complete suite with `make test`.
- **Other:** No reply is sent and no ticket is automatically routed as part of this feature. No additional localization or accessibility requirements apply to the API-only scope.

## 7. Test plan

### Unit

- Validate the input rules and review-field constraints for AC3. Include whitespace-only input,
  subject/body length boundaries, and unsupported category or priority values.
- Exercise accept/change state behavior for AC6 and AC7: accept preserves all suggestions; change
  replaces only supplied values and retains omitted values.
- These tests supplement, but do not replace, the HTTP integration assertions below.

### Integration

Use the `client` fixture with its throwaway database for HTTP behavior and the `stub` model fixture
for deterministic classification. Name tests `test_ac<N>_...` so each test points to its acceptance
criterion.

| Acceptance criterion | Integration test(s) and observable assertions |
| --- | --- |
| AC1 | `test_ac1_classification_returns_created_ticket`: HTTP 201; original text, all suggestions, `pending_review`, confidence, model version, and model provenance are present. |
| AC2 | `test_ac2_subject_only_is_classified` and `test_ac2_body_only_is_classified`: each text-only request succeeds and enters `pending_review`. |
| AC3 | `test_ac3_invalid_ticket_input_returns_422_without_creation`: empty/whitespace-only content, over-limit subject/body, and invalid enum values return 422; verify no ticket was added. |
| AC4 | `test_ac4_empty_review_queue_returns_empty_page`: HTTP 200 with `items: []`, `total: 0`, and the requested page metadata. |
| AC5 | `test_ac5_low_confidence_suggestion_remains_pending`: configure the stub to return a score below 0.5; assert HTTP 201, status remains `pending_review`, and the model payload still exposes the suggestion and the low-confidence score. |
| AC6 | `test_ac6_accept_preserves_suggestions`: HTTP 200, status `accepted`, and category, priority, team, and draft reply unchanged. |
| AC7 | `test_ac7_change_replaces_only_supplied_fields`: HTTP 200, status `changed`, submitted values updated, omitted values unchanged, and original model provenance retained. |
| AC8 | `test_ac8_unauthorized_review_returns_403_without_change`: establish an unauthorized agent context; assert HTTP 403 and unchanged ticket. This requires an authorization mechanism/test seam, while §6 currently says this increment adds no authorization. |
| AC9 | `test_ac9_review_of_missing_ticket_returns_not_found`: HTTP 404 with code `not_found`. |
| AC10 | `test_ac10_model_unavailable_returns_503_without_creation`: configure the stub to be unavailable; assert HTTP 503, code `model_unavailable`, and no ticket created. |
| AC11 | `test_ac11_model_timeout_returns_504_without_creation`: configure a non-sleeping stub timeout; assert HTTP 504, code `model_timeout`, and no ticket created. |
| AC12 | `test_ac12_concurrent_reviews_allow_exactly_one_change`: race two reviews for one pending ticket; assert exactly one HTTP 200, one HTTP 409, and only the successful review's values persisted. |

### End to end

n/a — this increment exposes an API only and has no deployed-client or UI workflow beyond the HTTP
and database behavior covered by integration tests.

Run the complete suite with `make test`. Configure model failures/timeouts through the stub or its
test environment controls; do not wait on real latency. AC8 cannot be fully exercised until its
authorization prerequisite is reconciled with the no-authorization constraint in §6.

## 8. Open questions

Things you do not know yet, and who can answer them. An honest open question is worth more than a
confident guess, because the guess is what the agent will build.
- I'm not sure about UI - do we need to enchance it as well.
---

## Review checklist

Before this specification goes to an agent:

- [ ] Could someone who has never spoken to me build from this without asking me a question?
- [ ] Is every acceptance criterion testable as written?
- [ ] Are the unhappy paths covered?
- [ ] Does §4 name what we are *not* building?
- [ ] Are the constraints specific enough to constrain? ("Follow our design system" is not; naming the
      library and the components is.)
- [ ] Have the people who own the constraints — UX, QE, security — actually seen this?
