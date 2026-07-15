from __future__ import annotations

from functools import lru_cache
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.domain.chat.models import ChatMeasureQueryRequest, ChatMeasureQueryResponse
from app.domain.chat.service import AnswerSummarizer, CandidateFilter, ChatbotService, MeasureRetriever, QueryExpander
from app.infrastructure.db.measure_repository import MeasureRepository
from app.infrastructure.llm.client import OpenAIChatbotClient
from app.infrastructure.vector.chroma_measure_index import ChromaMeasureIndex


class OpenAIQueryExpander(QueryExpander):
    def __init__(self, client: OpenAIChatbotClient) -> None:
        self._client = client

    def expand(self, request: ChatMeasureQueryRequest) -> tuple[list[str], list[str]]:
        return self._client.expand_query(request)


class OpenAICandidateFilter(CandidateFilter):
    def __init__(self, client: OpenAIChatbotClient) -> None:
        self._client = client

    def filter(self, request: ChatMeasureQueryRequest, candidates):
        return self._client.filter_candidates(request, candidates)


class OpenAIAnswerSummarizer(AnswerSummarizer):
    def __init__(self, client: OpenAIChatbotClient) -> None:
        self._client = client

    def summarize(self, request: ChatMeasureQueryRequest, results) -> str:
        return self._client.summarize_results(request, results)


class ChromaMeasureRetriever(MeasureRetriever):
    def __init__(self, index: ChromaMeasureIndex) -> None:
        self._index = index

    def search_many(self, queries, limit: int):
        return self._index.search_many(queries, limit)


router = APIRouter(prefix="/chat", tags=["chat"])


@lru_cache
def _chatbot_service() -> ChatbotService:
    settings = get_settings()
    repository = MeasureRepository(db_path=settings.sqlite_db_path)
    llm_client = OpenAIChatbotClient(settings)
    index = ChromaMeasureIndex(settings=settings, repository=repository)
    return ChatbotService(
        expander=OpenAIQueryExpander(llm_client),
        retriever=ChromaMeasureRetriever(index),
        candidate_filter=OpenAICandidateFilter(llm_client),
        summarizer=OpenAIAnswerSummarizer(llm_client),
    )


def _stream_error(message: str) -> str:
    return f"event: error\ndata: {json.dumps({'message': message}, ensure_ascii=True)}\n\n"


@router.post("/measures/query")
def query_measures(request: ChatMeasureQueryRequest) -> StreamingResponse:
    def event_stream():
        try:
            yield from _chatbot_service().stream_answer(request)
        except Exception as error:
            yield _stream_error(str(error))

    return StreamingResponse(event_stream(), media_type="text/event-stream")