import type { ChatMeasureQueryResponse, ChatMeasureStreamProgress } from '../types'


type ChatbotProgressProps = {
  question: string
  progress: ChatMeasureStreamProgress | null
  response: ChatMeasureQueryResponse | null
}

type ProgressStep = {
  label: string
  detail: string
  metric?: string
}

const MAX_VISIBLE_TERMS = 4
const STOP_WORDS = new Set([
  'a',
  'about',
  'an',
  'and',
  'are',
  'for',
  'find',
  'how',
  'i',
  'in',
  'is',
  'me',
  'measures',
  'of',
  'on',
  'related',
  'show',
  'tell',
  'the',
  'to',
  'what',
])


function previewExpandedTerms(question: string) {
  const tokens = question
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((token) => token.length > 2 && !STOP_WORDS.has(token))

  const uniqueTokens = Array.from(new Set(tokens))
  if (uniqueTokens.length === 0) {
    return []
  }

  const bigrams: string[] = []
  for (let index = 0; index < uniqueTokens.length - 1; index += 1) {
    bigrams.push(`${uniqueTokens[index]} ${uniqueTokens[index + 1]}`)
  }

  return [...bigrams, ...uniqueTokens].slice(0, 6)
}


function formatExpansionFlow(question: string, expandedTerms: string[]) {
  if (expandedTerms.length === 0) {
    return {
      flow: question,
      sample: 'No additional terms were needed.',
    }
  }

  const visibleTerms = expandedTerms.slice(0, MAX_VISIBLE_TERMS)
  const hiddenCount = Math.max(expandedTerms.length - visibleTerms.length, 0)

  return {
    flow: [question, ...visibleTerms].join(' -> '),
    sample:
      hiddenCount > 0
        ? `${visibleTerms.join(', ')}, +${hiddenCount} more`
        : visibleTerms.join(', '),
  }
}


function currentStageIndex(stage: ChatMeasureStreamProgress['stage'] | 'idle') {
  switch (stage) {
    case 'expanded_terms':
      return 0
    case 'candidates_found':
      return 1
    case 'filtered_results':
      return 2
    case 'complete':
      return 3
    case 'error':
      return 3
    case 'idle':
    default:
      return -1
  }
}


function statusForStep(stepIndex: number, activeIndex: number, isComplete: boolean) {
  if (isComplete) {
    return 'done'
  }
  if (activeIndex === stepIndex) {
    return 'active'
  }
  if (activeIndex > stepIndex) {
    return 'done'
  }
  return 'waiting'
}


export function ChatbotProgress({ question, progress, response }: ChatbotProgressProps) {
  const resolvedQuestion = response?.question ?? progress?.question ?? question
  const resolvedExpandedTerms = response?.expanded_terms ?? progress?.expandedTerms ?? []
  const resolvedCandidateCount = response?.candidate_count ?? progress?.candidateCount ?? null
  const resolvedFilteredCount = response?.filtered_count ?? progress?.filteredCount ?? null
  const resolvedReturnedCount = response?.returned_count ?? progress?.returnedCount ?? null
  const resolvedRetrievalQueries = progress?.retrievalQueries ?? []
  const stage = response ? 'complete' : (progress?.stage ?? 'idle')
  const activeIndex = currentStageIndex(stage)
  const expansion = formatExpansionFlow(resolvedQuestion, resolvedExpandedTerms)
  const previewTerms = previewExpandedTerms(resolvedQuestion)
  const previewExpansion = formatExpansionFlow(resolvedQuestion, previewTerms)

  const steps: ProgressStep[] = [
    {
      label: 'Expanded the search terms',
      metric:
        resolvedExpandedTerms.length > 0
          ? `${resolvedExpandedTerms.length} terms`
          : previewTerms.length > 0
            ? `${previewTerms.length} preview terms`
            : 'LLM step',
      detail:
        resolvedExpandedTerms.length > 0
          ? `Flow: ${expansion.flow}. Sample: ${expansion.sample}.${resolvedRetrievalQueries.length > 0 ? ` Retrieval queries: ${resolvedRetrievalQueries.slice(0, 3).join('; ')}${resolvedRetrievalQueries.length > 3 ? ', ...' : ''}.` : ''}`
          : `Starting from: ${resolvedQuestion}. Preview flow: ${previewExpansion.flow}.`,
    },
    {
      label: 'Searched the measure database',
      metric: resolvedCandidateCount !== null ? `${resolvedCandidateCount} found` : activeIndex >= 1 ? 'Searching now' : 'Retrieval step',
      detail:
        resolvedCandidateCount !== null
          ? `Found ${resolvedCandidateCount} matching measures in the initial retrieval pass.`
          : activeIndex >= 1
            ? 'Running retrieval across the catalogue using the expanded terms.'
            : 'This step will show how many measures were found in the initial retrieval pass.',
    },
    {
      label: 'Applied secondary filtering',
      metric: resolvedFilteredCount !== null ? `${resolvedFilteredCount} kept` : activeIndex >= 2 ? 'Filtering now' : 'Relevance step',
      detail:
        resolvedFilteredCount !== null
          ? `Reduced the set to ${resolvedFilteredCount} measures that match the question closely.`
          : activeIndex >= 2
            ? 'Checking the retrieved measures against your question and removing weak matches.'
            : 'This step will show how many measures remain after the LLM checks them against your question.',
    },
    {
      label: 'Prepared the final answer',
      metric: resolvedReturnedCount !== null ? `${resolvedReturnedCount} shown` : activeIndex >= 3 ? 'Summarising now' : 'Summary step',
      detail:
        resolvedReturnedCount !== null
          ? `Showing ${resolvedReturnedCount} measures in the final response.`
          : activeIndex >= 3
            ? 'Writing the final answer summary and assembling the remaining measures for display.'
            : 'This step will show how many measures make it into the final answer.',
    },
  ]

  return (
    <section className="chat-progress-card">
      <p className="catalogue-kicker">Chatbot Process</p>
      {progress?.stage === 'error' && progress.errorMessage ? (
        <p className="chat-progress-error">{progress.errorMessage}</p>
      ) : null}
      <ol className="chat-progress-list">
        {steps.map((step, index) => {
          const status = statusForStep(index, activeIndex, response !== null)
          return (
            <li key={step.label} className={`chat-progress-item chat-progress-item--${status}`}>
              <span className="chat-progress-marker" aria-hidden="true" />
              <div>
                <div className="chat-progress-heading">
                  <p className="chat-progress-label">{step.label}</p>
                  {step.metric ? <span className="chat-progress-metric">{step.metric}</span> : null}
                </div>
                <p className="chat-progress-detail">{step.detail}</p>
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}