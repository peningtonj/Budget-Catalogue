from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.measures.models import DocumentSection


class ChatMeasureQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_context: list[str] = Field(default_factory=list)
    limit: int = Field(default=30, ge=1, le=50)


class ChatMeasureCandidate(BaseModel):
    measure_id: int
    measure_title: str
    portfolio_name: str
    budget_round: str
    document_section: DocumentSection
    source_page: int | None
    headline_financial_total_million: int | float | None
    full_measure_text: str
    semantic_score: float = Field(ge=0)


class ChatMeasureRelevanceDecision(BaseModel):
    measure_id: int
    keep: bool
    relevance_score: float = Field(ge=0, le=1)
    reason: str


class ChatMeasureResult(BaseModel):
    measure_id: int
    measure_title: str
    portfolio_name: str
    budget_round: str
    document_section: DocumentSection
    source_page: int | None
    headline_financial_total_million: int | float | None
    match_reason: str
    relevance_score: float = Field(ge=0, le=1)
    excerpt: str


class ChatMeasureQueryResponse(BaseModel):
    question: str
    expanded_terms: list[str]
    candidate_count: int = Field(ge=0)
    filtered_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    answer_summary: str
    results: list[ChatMeasureResult]


class QueryExpansionResult(BaseModel):
    search_terms: list[str] = Field(default_factory=list)


class QueryExpansionResponse(BaseModel):
    expanded_terms: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)


class CandidateDecisionItem(BaseModel):
    measure_id: int
    keep: bool
    relevance_score: float = Field(ge=0, le=1)
    reason: str


class CandidateFilterResult(BaseModel):
    decisions: list[CandidateDecisionItem] = Field(default_factory=list)


class AnswerSummaryResult(BaseModel):
    answer_summary: str
    follow_up_suggestions: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str