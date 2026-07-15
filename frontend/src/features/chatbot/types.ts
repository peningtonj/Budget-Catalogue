export type ChatMeasureQueryRequest = {
  question: string
  conversation_context: string[]
  limit?: number
}

export type ChatMeasureResult = {
  measure_id: number
  measure_title: string
  portfolio_name: string
  budget_round: string
  document_section: 'payment' | 'receipt'
  source_page: number | null
  headline_financial_total_million: number | null
  match_reason: string
  relevance_score: number
  excerpt: string
}

export type ChatMeasureQueryResponse = {
  question: string
  expanded_terms: string[]
  candidate_count: number
  filtered_count: number
  returned_count: number
  answer_summary: string
  results: ChatMeasureResult[]
}

export type ChatMeasureStreamEvent =
  | {
      event: 'expanded_terms'
      data: {
        question: string
        expanded_terms: string[]
        retrieval_queries: string[]
      }
    }
  | {
      event: 'candidates_found'
      data: {
        question: string
        candidate_count: number
      }
    }
  | {
      event: 'filtered_results'
      data: {
        question: string
        candidate_count: number
        filtered_count: number
        returned_count: number
      }
    }
  | {
      event: 'complete'
      data: ChatMeasureQueryResponse
    }
  | {
      event: 'error'
      data: {
        message: string
      }
    }

export type ChatMeasureStreamProgress = {
  question: string
  stage: 'idle' | 'expanded_terms' | 'candidates_found' | 'filtered_results' | 'complete' | 'error'
  expandedTerms: string[]
  retrievalQueries: string[]
  candidateCount: number | null
  filteredCount: number | null
  returnedCount: number | null
  errorMessage: string | null
}