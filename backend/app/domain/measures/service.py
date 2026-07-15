from __future__ import annotations

from app.domain.measures.models import MeasureDetail, MeasureSearchFilters, MeasureSearchResponse
from app.infrastructure.db.measure_repository import MeasureRepository


class MeasureService:
    def __init__(self, repository: MeasureRepository | None = None) -> None:
        self.repository = repository or MeasureRepository()

    def search(self, filters: MeasureSearchFilters) -> MeasureSearchResponse:
        results = self.repository.search(filters)
        portfolios = self.repository.list_portfolios()
        budget_rounds = self.repository.list_budget_rounds()
        return MeasureSearchResponse(
            query=filters.query,
            document_section=filters.document_section,
            portfolio_name=filters.portfolio_name,
            budget_rounds=filters.budget_rounds,
            total=len(results),
            available_portfolios=portfolios,
            available_budget_rounds=budget_rounds,
            results=results,
        )

    def get_detail(self, measure_id: int) -> MeasureDetail | None:
        return self.repository.get_detail(measure_id)
