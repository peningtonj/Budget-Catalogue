from __future__ import annotations

from collections.abc import Sequence
import json

from app.domain.chat.models import CandidateDecisionItem, ChatMeasureCandidate, ChatMeasureQueryRequest, ChatMeasureResult
from app.domain.chat.service import AnswerSummarizer, CandidateFilter, ChatbotService, MeasureRetriever, QueryExpander


class StubQueryExpander(QueryExpander):
    def expand(self, request: ChatMeasureQueryRequest) -> tuple[list[str], list[str]]:
        return ["housing affordability", "rent assistance"], [request.question, "rent assistance"]


class StubRetriever(MeasureRetriever):
    def search_many(self, queries: Sequence[str], limit: int) -> list[ChatMeasureCandidate]:
        return [
            ChatMeasureCandidate(
                measure_id=101,
                measure_title="Housing support for renters",
                portfolio_name="Housing",
                budget_round="2025-26 Budget",
                document_section="payment",
                source_page=33,
                headline_financial_total_million=250.0,
                full_measure_text="This measure expands rent assistance for lower income households.",
                semantic_score=0.88,
            ),
            ChatMeasureCandidate(
                measure_id=102,
                measure_title="Unrelated roads program",
                portfolio_name="Infrastructure",
                budget_round="2025-26 Budget",
                document_section="payment",
                source_page=51,
                headline_financial_total_million=1200.0,
                full_measure_text="This measure funds road upgrades.",
                semantic_score=0.64,
            ),
        ]


class StubFilter(CandidateFilter):
    def filter(
        self,
        request: ChatMeasureQueryRequest,
        candidates: Sequence[ChatMeasureCandidate],
    ) -> list[CandidateDecisionItem]:
        return [
            CandidateDecisionItem(
                measure_id=101,
                keep=True,
                relevance_score=0.93,
                reason="Directly addresses rental affordability through rent assistance.",
            ),
            CandidateDecisionItem(
                measure_id=102,
                keep=False,
                relevance_score=0.12,
                reason="Road funding is not responsive to the housing question.",
            ),
        ]


class StubSummarizer(AnswerSummarizer):
    def summarize(self, request: ChatMeasureQueryRequest, results: Sequence[ChatMeasureResult]) -> str:
        assert len(results) == 1
        return "The strongest match is a renter support measure focused on affordability."


def test_chatbot_service_returns_filtered_ranked_results() -> None:
    service = ChatbotService(
        expander=StubQueryExpander(),
        retriever=StubRetriever(),
        candidate_filter=StubFilter(),
        summarizer=StubSummarizer(),
    )

    response = service.answer(ChatMeasureQueryRequest(question="Tell me about housing affordability measures", limit=5))

    assert response.expanded_terms == ["housing affordability", "rent assistance"]
    assert response.answer_summary == "The strongest match is a renter support measure focused on affordability."
    assert response.candidate_count == 2
    assert response.filtered_count == 1
    assert response.returned_count == 1
    assert [result.measure_id for result in response.results] == [101]
    assert response.results[0].match_reason == "Directly addresses rental affordability through rent assistance."
    assert response.results[0].headline_financial_total_million == 250.0


def test_chatbot_service_returns_empty_summary_when_no_candidates() -> None:
    class EmptyRetriever(MeasureRetriever):
        def search_many(self, queries: Sequence[str], limit: int) -> list[ChatMeasureCandidate]:
            return []

    service = ChatbotService(
        expander=StubQueryExpander(),
        retriever=EmptyRetriever(),
        candidate_filter=StubFilter(),
        summarizer=StubSummarizer(),
    )

    response = service.answer(ChatMeasureQueryRequest(question="Tell me about housing affordability measures", limit=5))

    assert response.candidate_count == 0
    assert response.filtered_count == 0
    assert response.returned_count == 0
    assert response.results == []
    assert response.answer_summary == "No matching measures were found in the catalogue for that question."


def test_chatbot_service_streams_expected_events() -> None:
    service = ChatbotService(
        expander=StubQueryExpander(),
        retriever=StubRetriever(),
        candidate_filter=StubFilter(),
        summarizer=StubSummarizer(),
    )

    chunks = list(service.stream_answer(ChatMeasureQueryRequest(question="Tell me about housing affordability measures", limit=5)))

    assert len(chunks) == 4

    expanded_event, candidates_event, filtered_event, complete_event = chunks

    assert expanded_event.startswith("event: expanded_terms\n")
    assert candidates_event.startswith("event: candidates_found\n")
    assert filtered_event.startswith("event: filtered_results\n")
    assert complete_event.startswith("event: complete\n")

    complete_payload = json.loads(complete_event.split("data:", maxsplit=1)[1].strip())
    assert complete_payload["candidate_count"] == 2
    assert complete_payload["filtered_count"] == 1
    assert complete_payload["returned_count"] == 1