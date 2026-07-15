import type { MeasureSearchFilters } from '../types'


type SearchFormProps = {
  filters: MeasureSearchFilters
  portfolioOptions: string[]
  budgetRoundOptions: string[]
  onQueryChange: (value: string) => void
  onDocumentSectionChange: (value: MeasureSearchFilters['documentSection']) => void
  onPortfolioChange: (value: string) => void
  onBudgetRoundAdd: (value: string) => void
  onBudgetRoundRemove: (value: string) => void
  onBudgetRoundClear: () => void
  onSubmit: () => void
}


export function SearchForm({
  filters,
  portfolioOptions,
  budgetRoundOptions,
  onQueryChange,
  onDocumentSectionChange,
  onPortfolioChange,
  onBudgetRoundAdd,
  onBudgetRoundRemove,
  onBudgetRoundClear,
  onSubmit,
}: SearchFormProps) {
  return (
    <form
      className="search-form"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <div className="search-form-row">
        <input
          className="search-input"
          type="search"
          value={filters.query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search titles, portfolios, or measure text"
          aria-label="Search measures"
        />
        <button className="search-button" type="submit">
          Search measures
        </button>
      </div>
      <div className="search-filter-row">
        <label className="search-filter-field">
          <span className="search-filter-label">Section</span>
          <select
            className="search-select"
            value={filters.documentSection}
            onChange={(event) => onDocumentSectionChange(event.target.value as MeasureSearchFilters['documentSection'])}
          >
            <option value="">All sections</option>
            <option value="payment">Payments</option>
            <option value="receipt">Receipts</option>
          </select>
        </label>
        <label className="search-filter-field">
          <span className="search-filter-label">Portfolio</span>
          <select
            className="search-select"
            value={filters.portfolioName}
            onChange={(event) => onPortfolioChange(event.target.value)}
          >
            <option value="">All portfolios</option>
            {portfolioOptions.map((portfolio) => (
              <option key={portfolio} value={portfolio}>
                {portfolio}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="search-filter-field">
        <div className="search-filter-heading">
          <span className="search-filter-label">Budget rounds</span>
          {filters.budgetRounds.length > 0 ? (
            <button className="search-clear-button" type="button" onClick={onBudgetRoundClear}>
              Clear
            </button>
          ) : null}
        </div>
        <select
          className="search-select"
          value=""
          onChange={(event) => {
            if (event.target.value) {
              onBudgetRoundAdd(event.target.value)
            }
          }}
        >
          <option value="">Add a budget round</option>
          {budgetRoundOptions.map((budgetRound) => (
            <option key={budgetRound} value={budgetRound} disabled={filters.budgetRounds.includes(budgetRound)}>
              {budgetRound}
            </option>
          ))}
        </select>
        {filters.budgetRounds.length > 0 ? (
          <div className="search-pill-row" role="list" aria-label="Selected budget rounds">
            {filters.budgetRounds.map((budgetRound) => (
              <button
                key={budgetRound}
                className="search-pill"
                type="button"
                role="listitem"
                onClick={() => onBudgetRoundRemove(budgetRound)}
                aria-label={`Remove ${budgetRound} budget round filter`}
              >
                <span>{budgetRound}</span>
                <span className="search-pill-close" aria-hidden="true">
                  ×
                </span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </form>
  )
}
