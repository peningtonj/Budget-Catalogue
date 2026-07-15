from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DocumentSection = Literal["payment", "receipt"]


class MeasureSearchFilters(BaseModel):
    query: str = ""
    document_section: DocumentSection | None = None
    portfolio_name: str | None = None
    budget_rounds: list[str] = Field(default_factory=list)
    limit: int = 20


class MeasureSearchItem(BaseModel):
    id: int
    measure_title: str
    portfolio_name: str
    budget_round: str
    document_section: DocumentSection
    source_page: int | None
    headline_financial_total_million: int | float | None
    full_measure_text: str


class MeasureSearchResponse(BaseModel):
    query: str
    document_section: DocumentSection | None = None
    portfolio_name: str | None = None
    budget_rounds: list[str] = Field(default_factory=list)
    total: int
    available_portfolios: list[str]
    available_budget_rounds: list[str]
    results: list[MeasureSearchItem]


class MeasureHeadlineFinancialValue(BaseModel):
    fiscal_year: str
    value_kind: str
    value_numeric_million: int | float | None
    value_raw: str | None


class MeasureHeadlineFinancial(BaseModel):
    impact_type: str
    is_related: bool
    department_name: str
    ordinal: int
    values: list[MeasureHeadlineFinancialValue]


class MeasureComponentImpactValue(BaseModel):
    fiscal_year: str
    value_kind: str
    value_numeric_million: int | float | None
    value_raw: str | None


class MeasureComponent(BaseModel):
    id: int
    parent_component_id: int | None
    level: int
    marker: str
    ordinal: int
    component_text: str
    amount_raw: str | None
    amount_million: int | float | None
    start_fiscal_year: str | None
    duration_years: int | None
    allocation_status: str
    impact_values: list[MeasureComponentImpactValue]


class MeasureRelatedMeasure(BaseModel):
    ordinal: int
    related_measure_title: str
    linked_measure_id: int | None = None


class MeasureIncomingRelatedMeasure(BaseModel):
    measure_id: int
    measure_title: str
    portfolio_name: str
    budget_round: str


class MeasureDetail(BaseModel):
    id: int
    measure_title: str
    portfolio_name: str
    budget_round: str
    document_section: DocumentSection
    source_page: int | None
    full_measure_text: str
    headline_financials: list[MeasureHeadlineFinancial]
    components: list[MeasureComponent]
    related_measures: list[MeasureRelatedMeasure]
    incoming_related_measures: list[MeasureIncomingRelatedMeasure]
