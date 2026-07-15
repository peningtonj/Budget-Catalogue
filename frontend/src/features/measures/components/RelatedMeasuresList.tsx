import { Link } from 'react-router-dom'

import type { MeasureIncomingRelatedMeasure } from '../../catalogue/types'


type RelatedMeasuresListProps = {
  relatedMeasures: MeasureIncomingRelatedMeasure[]
}


export function RelatedMeasuresList({ relatedMeasures }: RelatedMeasuresListProps) {
  if (relatedMeasures.length === 0) {
    return <div className="detail-empty">No other measures reference this measure.</div>
  }

  return (
    <ul className="related-measures-list">
      {relatedMeasures.map((measure) => (
        <li key={measure.measure_id}>
          <Link className="detail-inline-link" to={`/measures/${measure.measure_id}`}>
            {measure.measure_title}
          </Link>
          <div className="detail-subtle">
            {measure.portfolio_name} · {measure.budget_round}
          </div>
        </li>
      ))}
    </ul>
  )
}
