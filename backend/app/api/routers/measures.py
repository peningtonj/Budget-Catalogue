from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.domain.measures.models import DocumentSection, MeasureDetail, MeasureSearchFilters, MeasureSearchResponse
from app.domain.measures.service import MeasureService


router = APIRouter(prefix="/measures", tags=["measures"])

service = MeasureService()


@router.get("/search", response_model=MeasureSearchResponse)
def search_catalogue_measures(
    q: str = Query(default="", description="Free-text search over measure title, portfolio, and text."),
    document_section: DocumentSection | None = Query(default=None),
    portfolio_name: str | None = Query(default=None),
    budget_round: list[str] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=100),
) -> MeasureSearchResponse:
    return service.search(
        MeasureSearchFilters(
            query=q,
            document_section=document_section,
            portfolio_name=portfolio_name,
            budget_rounds=budget_round,
            limit=limit,
        )
    )


@router.get("/{measure_id}", response_model=MeasureDetail)
def get_measure_detail(measure_id: int) -> MeasureDetail:
    measure = service.get_detail(measure_id)
    if measure is None:
        raise HTTPException(status_code=404, detail="Measure not found")
    return measure
