from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.domain.chat.models import ChatMeasureCandidate
from app.infrastructure.db.measure_repository import MeasureRepository


MISSING_HEADLINE_TOTAL = "not_available"


def _semantic_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(distance, 0.0))


def _decode_headline_total(value: object) -> float | None:
    if value in (None, MISSING_HEADLINE_TOTAL):
        return None
    return float(value)


class ChromaMeasureIndex:
    def __init__(self, settings: Settings, repository: MeasureRepository | None = None) -> None:
        try:
            import chromadb
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "chromadb is required for chatbot retrieval. Install backend dependencies before using /chat endpoints."
            ) from error

        self._settings = settings
        self._repository = repository or MeasureRepository(db_path=settings.sqlite_db_path)
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self._client: Any = chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection = self._client.get_or_create_collection(name=settings.chroma_collection_name)

    def search_many(self, queries: Sequence[str], limit: int) -> list[ChatMeasureCandidate]:
        self._ensure_index()
        deduped: dict[int, ChatMeasureCandidate] = {}
        per_query_limit = max(1, min(limit, 10))

        for query in queries:
            stripped_query = query.strip()
            if not stripped_query:
                continue
            response = self._collection.query(
                query_texts=[stripped_query],
                n_results=per_query_limit,
                include=["documents", "metadatas", "distances"],
            )
            metadatas = response.get("metadatas", [[]])[0]
            documents = response.get("documents", [[]])[0]
            distances = response.get("distances", [[]])[0]

            for metadata, document, distance in zip(metadatas, documents, distances, strict=False):
                if metadata is None or document is None:
                    continue
                measure_id = int(metadata["measure_id"])
                candidate = ChatMeasureCandidate(
                    measure_id=measure_id,
                    measure_title=str(metadata["measure_title"]),
                    portfolio_name=str(metadata["portfolio_name"]),
                    budget_round=str(metadata["budget_round"]),
                    document_section=str(metadata["document_section"]),
                    source_page=(
                        int(metadata["source_page"])
                        if metadata.get("source_page") is not None and int(metadata["source_page"]) >= 0
                        else None
                    ),
                    headline_financial_total_million=_decode_headline_total(
                        metadata.get("headline_financial_total_million")
                    ),
                    full_measure_text=str(document),
                    semantic_score=_semantic_score(float(distance) if distance is not None else None),
                )
                previous = deduped.get(measure_id)
                if previous is None or candidate.semantic_score > previous.semantic_score:
                    deduped[measure_id] = candidate

        return sorted(deduped.values(), key=lambda candidate: candidate.semantic_score, reverse=True)[:limit]

    def rebuild(self) -> int:
        documents = self._repository.list_index_documents()
        self._replace_documents(documents)
        return len(documents)

    def _ensure_index(self) -> None:
        expected_count = self._repository.count_measures()
        current_count = self._collection.count()
        if expected_count == 0:
            return

        if current_count == expected_count:
            sample = self._collection.get(limit=1, include=["metadatas"])
            metadatas = sample.get("metadatas") or []
            sample_metadata = metadatas[0] if metadatas else None
            if isinstance(sample_metadata, list):
                sample_metadata = sample_metadata[0] if sample_metadata else None
            if isinstance(sample_metadata, dict) and "headline_financial_total_million" in sample_metadata:
                return

        documents = self._repository.list_index_documents()
        self._replace_documents(documents)

    def _replace_documents(self, documents: Sequence[ChatMeasureCandidate]) -> None:
        self._collection.delete(where={"measure_id": {"$gte": 0}})
        if not documents:
            return

        self._collection.add(
            ids=[str(document.measure_id) for document in documents],
            documents=[document.full_measure_text for document in documents],
            metadatas=[
                {
                    "measure_id": document.measure_id,
                    "measure_title": document.measure_title,
                    "portfolio_name": document.portfolio_name,
                    "budget_round": document.budget_round,
                    "document_section": document.document_section,
                    "source_page": document.source_page if document.source_page is not None else -1,
                    "headline_financial_total_million": (
                        document.headline_financial_total_million
                        if document.headline_financial_total_million is not None
                        else MISSING_HEADLINE_TOTAL
                    ),
                }
                for document in documents
            ],
        )