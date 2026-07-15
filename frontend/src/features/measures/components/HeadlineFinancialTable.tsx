import type { MeasureHeadlineFinancial } from '../../catalogue/types'


type HeadlineFinancialTableProps = {
  rows: MeasureHeadlineFinancial[]
}


function formatValue(value: { value_kind: string; value_numeric_million: number | null; value_raw: string | null }) {
  if (value.value_kind === 'numeric') {
    return value.value_numeric_million?.toString() ?? '0'
  }
  return value.value_raw ?? '-'
}


export function HeadlineFinancialTable({ rows }: HeadlineFinancialTableProps) {
  if (rows.length === 0) {
    return <div className="detail-empty">No headline financials extracted.</div>
  }

  const years = rows[0]?.values.map((value) => value.fiscal_year) ?? []

  return (
    <div className="detail-table-wrap">
      <table className="detail-table">
        <thead>
          <tr>
            <th>Department</th>
            {years.map((year) => (
              <th key={year}>{year}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.impact_type}-${row.ordinal}-${row.department_name}`}>
              <td>
                <strong>{row.department_name}</strong>
                <div className="detail-subtle">
                  {row.impact_type}
                  {row.is_related ? ' related' : ''}
                </div>
              </td>
              {row.values.map((value) => (
                <td key={`${row.ordinal}-${value.fiscal_year}`}>{formatValue(value)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
