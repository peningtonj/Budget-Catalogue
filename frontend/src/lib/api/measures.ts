import { apiRequest } from './client'
import type { MeasureDetail, MeasureSearchFilters, MeasureSearchResponse } from '../../features/catalogue/types'


export function searchMeasures(filters: MeasureSearchFilters) {
  const params = new URLSearchParams({ q: filters.query, limit: '20' })
  if (filters.documentSection) {
    params.set('document_section', filters.documentSection)
  }
  if (filters.portfolioName) {
    params.set('portfolio_name', filters.portfolioName)
  }
  for (const budgetRound of filters.budgetRounds) {
    params.append('budget_round', budgetRound)
  }
  return apiRequest<MeasureSearchResponse>(`/measures/search?${params.toString()}`)
}


export function getMeasureDetail(measureId: number) {
  return apiRequest<MeasureDetail>(`/measures/${measureId}`)
}
