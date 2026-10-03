"""Request and response shapes. Everything crossing the API boundary is declared here."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Kind = Literal["central", "branch", "bookmobile", "research"]


class Library(BaseModel):
    """One facility. This is the record type the whole app is built around."""

    id: int
    name: str
    city: str
    state: str = Field(min_length=2, max_length=2)
    kind: Kind
    year_founded: int
    annual_visits: int
    has_makerspace: bool


class LibraryCreate(BaseModel):
    """The write path. Note that ``id`` is assigned by the server, never by the caller."""

    name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=2, max_length=2)
    kind: Kind
    year_founded: int = Field(ge=1700, le=2100)
    annual_visits: int = Field(ge=0)
    has_makerspace: bool = False


class Page(BaseModel):
    """Every list endpoint returns this shape. Copy it for new list endpoints."""

    items: list[Library]
    total: int
    limit: int
    offset: int


TicketCategory = Literal["billing", "access", "data", "outage", "general"]
TicketPriority = Literal["low", "normal", "high"]
TicketStatus = Literal["untriaged", "pending_review", "accepted", "changed"]


class Ticket(BaseModel):
    """One support ticket in the human review queue."""

    id: str
    subject: str = Field(min_length=0, max_length=500)
    body: str = Field(min_length=0, max_length=10_000)
    category: TicketCategory
    priority: TicketPriority
    team: str = Field(min_length=1)
    draft_reply: str = Field(min_length=1)
    status: TicketStatus
    model: ModelPayload


class TicketCreate(BaseModel):
    """Incoming ticket payload. At least one of subject or body must contain text."""

    subject: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=10_000)

    @model_validator(mode="after")
    def require_text(self) -> "TicketCreate":
        if not self.subject.strip() and not self.body.strip():
            raise ValueError("subject or body must contain non-whitespace text")
        return self


class TicketReviewChange(BaseModel):
    """Review action for a queued ticket."""

    action: Literal["accept", "change"]
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None
    team: Optional[str] = Field(default=None, min_length=1, max_length=200)
    draft_reply: Optional[str] = Field(default=None, min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_change_payload(self) -> "TicketReviewChange":
        if self.action == "change":
            has_value = any(
                value is not None
                for value in (self.category, self.priority, self.team, self.draft_reply)
            )
            if not has_value:
                raise ValueError("at least one review field must be supplied")
            if self.team is not None and not self.team.strip():
                raise ValueError("team must contain non-whitespace text")
            if self.draft_reply is not None and not self.draft_reply.strip():
                raise ValueError("draft_reply must contain non-whitespace text")
        return self


class TicketPage(BaseModel):
    """List responses for ticket review queues."""

    items: list[Ticket]
    total: int
    limit: int
    offset: int


class ModelPayload(BaseModel):
    """How a model-backed endpoint reports what the model said.

    Every model-backed response embeds this, so a caller can always see the
    confidence and which model version produced the answer.
    """

    value: object
    confidence: float
    model_version: str
    latency_ms: int


class DescribeResponse(BaseModel):
    library_id: int
    description: str
    model: ModelPayload


class ErrorBody(BaseModel):
    """The one error shape. Every 4xx and 5xx this app raises looks like this."""

    detail: str
    code: str


class SummaryResponse(BaseModel):
    """`GET /libraries/summary` — see specs/filtered-summary.md §5."""

    count: int
    filters: dict
    summary: Optional[str]
    word_count: int
    truncated: bool
    cached: bool
    model: Optional[ModelPayload]
    model_error: Optional[str]
