import type { MeasureSearchResult } from '../types'
import { Link } from 'react-router-dom'

import { formatMeasureSnippet } from '../../../lib/formatting/measureText'


type MeasureResultsProps = {
  results: MeasureSearchResult[]
}

function formatHeadlineFinancialTotal(total: number | null) {
  if (total === null) {
    return 'Not available'
  }

  return `${new Intl.NumberFormat('en-AU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(total)}m`
}


export function MeasureResults({ results }: MeasureResultsProps) {
  if (results.length === 0) {
    return <section className="results-empty">No measures matched the current search.</section>
  }

  return (
    <section className="results-grid">
      {results.map((result) => (
        <article className="result-card" key={result.id}>
          <div className="result-topline">
            <span className="result-badge">{result.document_section}</span>
            {result.source_page !== null ? <span className="result-badge">page {result.source_page}</span> : null}
          </div>
          <h2 className="result-title">
            <Link className="result-link" to={`/measures/${result.id}`}>
              {result.measure_title}
            </Link>
          </h2>
          <p className="result-portfolio">{result.portfolio_name}</p>
          <dl className="result-summary">
            <div>
              <dt>Budget round</dt>
              <dd>{result.budget_round}</dd>
            </div>
            <div>
              <dt>Headline financial total</dt>
              <dd>{formatHeadlineFinancialTotal(result.headline_financial_total_million)}</dd>
            </div>
          </dl>
          <p className="result-snippet">{formatMeasureSnippet(result.full_measure_text)}</p>
        </article>
      ))}
    </section>
  )
}
