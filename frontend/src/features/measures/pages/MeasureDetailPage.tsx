import { Link, useLocation, useParams } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useMeasureDetail } from '../hooks/useMeasureDetail'
import { HeadlineFinancialTable } from '../components/HeadlineFinancialTable'
import { RelatedMeasuresList } from '../components/RelatedMeasuresList'
import { formatMeasureText } from '../../../lib/formatting/measureText'
import type { MeasureRelatedMeasure } from '../../catalogue/types'


function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}


function normalizeRelatedTitle(value: string) {
  return value.replace(/[’']/g, "'").replace(/\s*-\s*/g, '-').replace(/\s+/g, ' ').trim().toLocaleLowerCase()
}


function relatedTitlePattern(value: string) {
  const hyphenToken = '__HYPHEN__'

  return escapeRegex(value.replace(/\s*-\s*/g, hyphenToken))
    .replaceAll(hyphenToken, '\\s*-\\s*')
    .replace(/[’']/g, "['’]")
    .replace(/\s+/g, '\\s+')
}


function linkifyMeasureText(text: string, relatedMeasures: MeasureRelatedMeasure[]) {
  const linkedMeasures = relatedMeasures
    .filter((measure) => measure.linked_measure_id !== null)
    .sort((left, right) => right.related_measure_title.length - left.related_measure_title.length)
  const lines = text.split('\n')

  if (linkedMeasures.length === 0) {
    return lines.map((line, index) => (
      <span key={`line-${index}`}>
        {line}
        {index < lines.length - 1 ? <br /> : null}
      </span>
    ))
  }

  const linkedMeasureMap = new Map(
    linkedMeasures.map((measure) => [normalizeRelatedTitle(measure.related_measure_title), measure]),
  )

  const pattern = new RegExp(
    linkedMeasures.map((measure) => relatedTitlePattern(measure.related_measure_title)).join('|'),
    'gi',
  )

  return lines.map((line, lineIndex) => {
    const content: ReactNode[] = []
    let cursor = 0

    line.replace(pattern, (match, offset) => {
      if (offset > cursor) {
        content.push(line.slice(cursor, offset))
      }

      const relatedMeasure = linkedMeasureMap.get(normalizeRelatedTitle(match))

      if (relatedMeasure && relatedMeasure.linked_measure_id !== null) {
        content.push(
          <Link key={`${lineIndex}-${offset}-${relatedMeasure.linked_measure_id}`} className="detail-inline-link" to={`/measures/${relatedMeasure.linked_measure_id}`}>
            {match}
          </Link>,
        )
      } else {
        content.push(match)
      }

      cursor = offset + match.length
      return match
    })

    if (cursor < line.length) {
      content.push(line.slice(cursor))
    }

    return (
      <span key={`line-${lineIndex}`}>
        {content}
        {lineIndex < lines.length - 1 ? <br /> : null}
      </span>
    )
  })
}


export function MeasureDetailPage() {
  const location = useLocation()
  const params = useParams()
  const measureId = Number(params.measureId)
  const detailQuery = useMeasureDetail(measureId)
  const returnTo = typeof location.state?.returnTo === 'string' ? location.state.returnTo : '/'
  const returnLabel = typeof location.state?.returnLabel === 'string' ? location.state.returnLabel : 'Back to search'

  if (detailQuery.isLoading) {
    return <main className="app-shell"><div className="catalogue-page"><section className="results-empty">Loading measure detail...</section></div></main>
  }

  if (detailQuery.isError || !detailQuery.data) {
    return <main className="app-shell"><div className="catalogue-page"><section className="results-error">Unable to load this measure.</section></div></main>
  }

  const measure = detailQuery.data
  const formattedMeasureText = formatMeasureText(measure.full_measure_text)
  const linkedMeasureText = linkifyMeasureText(formattedMeasureText, measure.related_measures)

  return (
    <main className="app-shell">
      <div className="catalogue-page">
        <section className="catalogue-hero">
          <p className="catalogue-kicker">Measure Detail</p>
          <h1 className="catalogue-title detail-title">{measure.measure_title}</h1>
          <p className="catalogue-copy">{measure.portfolio_name}</p>
          <p className="detail-round">{measure.budget_round}</p>
          <p className="detail-backlink"><Link to={returnTo}>{returnLabel}</Link></p>
        </section>

        <section className="detail-panel">
          <h2 className="detail-section-title">Headline financials</h2>
          <HeadlineFinancialTable rows={measure.headline_financials} />
        </section>

        <section className="detail-panel">
          <h2 className="detail-section-title">Measure text</h2>
          <p className="detail-body">{linkedMeasureText}</p>
        </section>

        <section className="detail-panel">
          <h2 className="detail-section-title">Related measures</h2>
          <RelatedMeasuresList relatedMeasures={measure.incoming_related_measures} />
        </section>
      </div>
    </main>
  )
}