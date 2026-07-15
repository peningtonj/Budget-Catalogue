import { useState } from 'react'
import { Link } from 'react-router-dom'

import { SearchForm } from '../components/SearchForm'
import { MeasureResults } from '../components/MeasureResults'
import { useMeasureSearch } from '../hooks/useMeasureSearch'
import type { MeasureSearchFilters } from '../types'


export function CatalogueSearchPage() {
  const [draftFilters, setDraftFilters] = useState<MeasureSearchFilters>({
    query: '',
    documentSection: '',
    portfolioName: '',
    budgetRounds: [],
  })
  const [submittedFilters, setSubmittedFilters] = useState<MeasureSearchFilters>({
    query: '',
    documentSection: '',
    portfolioName: '',
    budgetRounds: [],
  })
  const searchQuery = useMeasureSearch(submittedFilters)
  const portfolioOptions = searchQuery.data?.available_portfolios ?? []
  const budgetRoundOptions = searchQuery.data?.available_budget_rounds ?? []

  function addBudgetRound(value: string) {
    setDraftFilters((current) => ({
      ...current,
      budgetRounds: current.budgetRounds.includes(value) ? current.budgetRounds : [...current.budgetRounds, value],
    }))
  }

  function removeBudgetRound(value: string) {
    setDraftFilters((current) => ({
      ...current,
      budgetRounds: current.budgetRounds.filter((budgetRound) => budgetRound !== value),
    }))
  }

  return (
    <main className="app-shell">
      <div className="catalogue-page">
        <section className="catalogue-hero">
          <p className="catalogue-kicker">Australian Budget Catalogue</p>
          <h1 className="catalogue-title">Search Budget Measures</h1>
          <p className="page-link-row">
            <Link to="/chat" className="page-link">
              Try the chatbot workflow
            </Link>
          </p>
        </section>

        <section className="search-panel">
          <SearchForm
            filters={draftFilters}
            portfolioOptions={portfolioOptions}
            budgetRoundOptions={budgetRoundOptions}
            onQueryChange={(value) => setDraftFilters((current) => ({ ...current, query: value }))}
            onDocumentSectionChange={(value) =>
              setDraftFilters((current) => ({ ...current, documentSection: value }))
            }
            onPortfolioChange={(value) => setDraftFilters((current) => ({ ...current, portfolioName: value }))}
            onBudgetRoundAdd={addBudgetRound}
            onBudgetRoundRemove={removeBudgetRound}
            onBudgetRoundClear={() => setDraftFilters((current) => ({ ...current, budgetRounds: [] }))}
            onSubmit={() => setSubmittedFilters({ ...draftFilters, query: draftFilters.query.trim() })}
          />
        </section>

        {searchQuery.isError ? <section className="results-error">Unable to reach the backend search API.</section> : null}
        {searchQuery.isSuccess ? <MeasureResults results={searchQuery.data.results} /> : null}
      </div>
    </main>
  )
}

