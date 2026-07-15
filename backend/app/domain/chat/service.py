from __future__ import annotations

from collections.abc import Generator, Sequence
from dataclasses import dataclass
import json

from app.domain.chat.models import (
    CandidateDecisionItem,
    ChatMeasureCandidate,
    ChatMeasureQueryRequest,
    ChatMeasureQueryResponse,
    ChatMeasureResult,
)


def _excerpt(text: str, limit: int = 280) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "..."


def _sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"


class QueryExpander:
    def expand(self, request: ChatMeasureQueryRequest) -> tuple[list[str], list[str]]:
        raise NotImplementedError


class MeasureRetriever:
    def search_many(self, queries: Sequence[str], limit: int) -> list[ChatMeasureCandidate]:
        raise NotImplementedError


class CandidateFilter:
    def filter(
        self,
        request: ChatMeasureQueryRequest,
        candidates: Sequence[ChatMeasureCandidate],
    ) -> list[CandidateDecisionItem]:
        raise NotImplementedError


class AnswerSummarizer:
    def summarize(
        self,
        request: ChatMeasureQueryRequest,
        results: Sequence[ChatMeasureResult],
    ) -> str:
        raise NotImplementedError


@dataclass
class ChatbotService:
    expander: QueryExpander
    retriever: MeasureRetriever
    candidate_filter: CandidateFilter
    summarizer: AnswerSummarizer

    def answer(self, request: ChatMeasureQueryRequest) -> ChatMeasureQueryResponse:
        expanded_terms, retrieval_queries = self.expander.expand(request)
        candidates = self.retriever.search_many(
            retrieval_queries,
            limit=max(request.limit * 4, 20),
        )

        return self._build_response(request, expanded_terms, candidates)

    def stream_answer(self, request: ChatMeasureQueryRequest) -> Generator[str, None, None]:
        expanded_terms, _ = self.expander.expand(request)
        yield _sse_event(
            "expanded_terms",
            {
                "question": request.question,
                "expanded_terms": expanded_terms
            },
        )

        candidates = self.retriever.search_many(
            expanded_terms,
            limit=max(request.limit * 4, 20),
        )
        yield _sse_event(
            "candidates_found",
            {
                "question": request.question,
                "candidate_count": len(candidates),
            },
        )

        response = self._build_response(request, expanded_terms, candidates)
        yield _sse_event(
            "filtered_results",
            {
                "question": request.question,
                "candidate_count": response.candidate_count,
                "filtered_count": response.filtered_count,
                "returned_count": response.returned_count,
            },
        )
        yield _sse_event("complete", response.model_dump(mode="json"))

    def _build_response(
        self,
        request: ChatMeasureQueryRequest,
        expanded_terms: list[str],
        candidates: Sequence[ChatMeasureCandidate],
    ) -> ChatMeasureQueryResponse:

        if not candidates:
            return ChatMeasureQueryResponse(
                question=request.question,
                expanded_terms=expanded_terms,
                candidate_count=0,
                filtered_count=0,
                returned_count=0,
                answer_summary="No matching measures were found in the catalogue for that question.",
                results=[],
            )

        decisions = self.candidate_filter.filter(request, candidates)
        kept_by_id = {
            decision.measure_id: decision
            for decision in decisions
            if decision.keep and decision.relevance_score > 0
        }
        semantic_scores_by_id = {
            candidate.measure_id: candidate.semantic_score
            for candidate in candidates
        }

        ranked_results = [
            ChatMeasureResult(
                measure_id=candidate.measure_id,
                measure_title=candidate.measure_title,
                portfolio_name=candidate.portfolio_name,
                budget_round=candidate.budget_round,
                document_section=candidate.document_section,
                source_page=candidate.source_page,
                headline_financial_total_million=candidate.headline_financial_total_million,
                match_reason=kept_by_id[candidate.measure_id].reason,
                relevance_score=kept_by_id[candidate.measure_id].relevance_score,
                excerpt=_excerpt(candidate.full_measure_text),
            )
            for candidate in candidates
            if candidate.measure_id in kept_by_id
        ]

        ranked_results.sort(
            key=lambda result: (result.relevance_score, semantic_scores_by_id.get(result.measure_id, 0.0)),
            reverse=True,
        )
        ranked_results = ranked_results[: request.limit]

        if ranked_results:
            answer_summary = self.summarizer.summarize(request, ranked_results)
        else:
            answer_summary = "I found related catalogue entries, but none were strong enough matches to return confidently."

        return ChatMeasureQueryResponse(
            question=request.question,
            expanded_terms=expanded_terms,
            candidate_count=len(candidates),
            filtered_count=len(kept_by_id),
            returned_count=len(ranked_results),
            answer_summary=answer_summary,
            results=ranked_results,
        )