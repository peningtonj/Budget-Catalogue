export type MeasureSearchResult = {
  id: number
  measure_title: string
  portfolio_name: string
  budget_round: string
  document_section: 'payment' | 'receipt'
  source_page: number | null
  headline_financial_total_million: number | null
  full_measure_text: string
}

export type MeasureSearchResponse = {
  query: string
  document_section: 'payment' | 'receipt' | null
  portfolio_name: string | null
  budget_rounds: string[]
  total: number
  available_portfolios: string[]
  available_budget_rounds: string[]
  results: MeasureSearchResult[]
}

export type MeasureSearchFilters = {
  query: string
  documentSection: 'payment' | 'receipt' | ''
  portfolioName: string
  budgetRounds: string[]
}

export type MeasureHeadlineFinancialValue = {
  fiscal_year: string
  value_kind: string
  value_numeric_million: number | null
  value_raw: string | null
}

export type MeasureHeadlineFinancial = {
  impact_type: string
  is_related: boolean
  department_name: string
  ordinal: number
  values: MeasureHeadlineFinancialValue[]
}

export type MeasureComponentImpactValue = {
  fiscal_year: string
  value_kind: string
  value_numeric_million: number | null
  value_raw: string | null
}

export type MeasureComponent = {
  id: number
  parent_component_id: number | null
  level: number
  marker: string
  ordinal: number
  component_text: string
  amount_raw: string | null
  amount_million: number | null
  start_fiscal_year: string | null
  duration_years: number | null
  allocation_status: string
  impact_values: MeasureComponentImpactValue[]
}

export type MeasureRelatedMeasure = {
  ordinal: number
  related_measure_title: string
  linked_measure_id: number | null
}

export type MeasureIncomingRelatedMeasure = {
  measure_id: number
  measure_title: string
  portfolio_name: string
  budget_round: string
}

export type MeasureDetail = {
  id: number
  measure_title: string
  portfolio_name: string
  budget_round: string
  document_section: 'payment' | 'receipt'
  source_page: number | null
  full_measure_text: string
  headline_financials: MeasureHeadlineFinancial[]
  components: MeasureComponent[]
  related_measures: MeasureRelatedMeasure[]
  incoming_related_measures: MeasureIncomingRelatedMeasure[]
}
