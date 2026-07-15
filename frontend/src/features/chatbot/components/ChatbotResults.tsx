import { Link } from 'react-router-dom'

import type { ChatMeasureQueryResponse } from '../types'


type ChatbotResultsProps = {
  response: ChatMeasureQueryResponse
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


export function ChatbotResults({ response }: ChatbotResultsProps) {
  return (
    <section className="chat-results">
      <div className="chat-summary-card">
        <p className="catalogue-kicker">Chatbot Summary</p>
        <p className="chat-summary-text">{response.answer_summary}</p>
        {response.expanded_terms.length > 0 ? (
          <div className="chat-term-row">
            {response.expanded_terms.map((term) => (
              <span key={term} className="chat-term-pill">
                {term}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="results-grid">
        {response.results.map((result) => (
          <article key={result.measure_id} className="result-card">
            <div className="result-topline">
              <span className="result-badge">{result.budget_round}</span>
              <span className="result-badge">{result.document_section}</span>
            </div>

            <h2 className="result-title">
              <Link
                to={`/measures/${result.measure_id}`}
                state={{ returnTo: '/chat', returnLabel: 'Back to chatbot results' }}
                className="result-link"
              >
                {result.measure_title}
              </Link>
            </h2>

            <p className="result-portfolio">{result.portfolio_name}</p>

            <dl className="result-summary">
              <div>
                <dt>Source Page</dt>
                <dd>{result.source_page ?? 'Unknown'}</dd>
              </div>
              <div>
                <dt>Headline financial total</dt>
                <dd>{formatHeadlineFinancialTotal(result.headline_financial_total_million)}</dd>
              </div>
            </dl>

            <p className="chat-match-reason">{result.match_reason}</p>
            <p className="result-snippet">{result.excerpt}</p>
          </article>
        ))}
      </div>
    </section>
  )
}