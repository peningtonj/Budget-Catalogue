from __future__ import annotations

import json
from collections.abc import Sequence

from openai import OpenAI

from app.core.config import Settings
from app.domain.chat.models import (
    CandidateDecisionItem,
    CandidateFilterResult,
    ChatMeasureCandidate,
    ChatMeasureQueryRequest,
    ChatMeasureResult,
    QueryExpansionResponse,
)


class OpenAIChatbotClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_chat_model

    def expand_query(self, request: ChatMeasureQueryRequest) -> tuple[list[str], list[str]]:
        prompt = (
            "You expand Australian budget policy questions into short retrieval terms. "
            "They are for searching a catalogue of Australian budget measures which are stored in a vector database."
            "Focus on the policy of the question rather than the text which is just context or natural language."
            "Return JSON with expanded_terms and retrieval_queries. "
            "Keep terms concise, policy-oriented, and grounded in the user question."
        )
        payload = {
            "question": request.question,
            "conversation_context": request.conversation_context,
            "limit": 6,
        }
        response = self._complete_json(prompt, payload)
        parsed = QueryExpansionResponse.model_validate_json(response)
        expanded_terms = [term.strip() for term in parsed.expanded_terms if term.strip()]
        retrieval_queries = [query.strip() for query in parsed.retrieval_queries if query.strip()]
        if request.question not in retrieval_queries:
            retrieval_queries.insert(0, request.question)
        if not expanded_terms:
            expanded_terms = [request.question]
        if not retrieval_queries:
            retrieval_queries = [request.question]
        return expanded_terms[:6], retrieval_queries[:8]

    def filter_candidates(
        self,
        request: ChatMeasureQueryRequest,
        candidates: Sequence[ChatMeasureCandidate],
    ) -> list[CandidateDecisionItem]:
        prompt = (
            "You evaluate which budget measures answer the user's question. "
            "Return JSON with a decisions array. For each candidate, decide keep true or false, "
            "assign a relevance_score between 0 and 1, and write a short reason tied to the question."
        )
        payload = {
            "question": request.question,
            "conversation_context": request.conversation_context,
            "candidates": [candidate.model_dump() for candidate in candidates],
        }
        response = self._complete_json(prompt, payload)
        parsed = CandidateFilterResult.model_validate_json(response)
        return parsed.decisions

    def summarize_results(
        self,
        request: ChatMeasureQueryRequest,
        results: Sequence[ChatMeasureResult],
    ) -> str:
        prompt = (
            "You summarise Australian budget measures for an end user. "
            "Write 2 to 4 sentences grounded only in the provided results."
        )
        payload = {
            "question": request.question,
            "conversation_context": request.conversation_context,
            "results": [result.model_dump() for result in results],
        }
        return self._complete_text(prompt, payload)

    def _complete_json(self, instruction: str, payload: dict[str, object]) -> str:
        completion = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")
        return content

    def _complete_text(self, instruction: str, payload: dict[str, object]) -> str:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")
        return content.strip()