import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ChatbotProgress } from '../components/ChatbotProgress'
import { ChatbotResults } from '../components/ChatbotResults'
import { useChatbotQuery } from '../hooks/useChatbotQuery'
import type { ChatMeasureQueryResponse, ChatMeasureStreamEvent, ChatMeasureStreamProgress } from '../types'


const STARTER_PROMPTS = [
  'Tell me about measures related to housing affordability',
  'What budget measures relate to childcare and early education?',
  'Find measures connected to clean energy investment',
]

const CHATBOT_PAGE_STATE_KEY = 'chatbot-page-state'

type ChatbotPageSnapshot = {
  question: string
  submittedQuestion: string
  streamProgress: ChatMeasureStreamProgress | null
  response: ChatMeasureQueryResponse | null
}


function readStoredSnapshot(): ChatbotPageSnapshot | null {
  if (typeof window === 'undefined') {
    return null
  }

  const storedValue = window.sessionStorage.getItem(CHATBOT_PAGE_STATE_KEY)
  if (!storedValue) {
    return null
  }

  try {
    return JSON.parse(storedValue) as ChatbotPageSnapshot
  } catch {
    window.sessionStorage.removeItem(CHATBOT_PAGE_STATE_KEY)
    return null
  }
}


export function ChatbotPage() {
  const [question, setQuestion] = useState(() => readStoredSnapshot()?.question || STARTER_PROMPTS[0])
  const [submittedQuestion, setSubmittedQuestion] = useState(
    () => readStoredSnapshot()?.submittedQuestion || readStoredSnapshot()?.question || STARTER_PROMPTS[0],
  )
  const [streamProgress, setStreamProgress] = useState<ChatMeasureStreamProgress | null>(
    () => readStoredSnapshot()?.streamProgress ?? null,
  )
  const [chatResponse, setChatResponse] = useState<ChatMeasureQueryResponse | null>(
    () => readStoredSnapshot()?.response ?? null,
  )
  const chatbotQuery = useChatbotQuery()

  useEffect(() => {
    const snapshot: ChatbotPageSnapshot = {
      question,
      submittedQuestion,
      streamProgress,
      response: chatResponse,
    }
    window.sessionStorage.setItem(CHATBOT_PAGE_STATE_KEY, JSON.stringify(snapshot))
  }, [question, submittedQuestion, streamProgress, chatResponse])

  function handleStreamEvent(event: ChatMeasureStreamEvent) {
    setStreamProgress((current) => {
      const base: ChatMeasureStreamProgress = current ?? {
        question: submittedQuestion,
        stage: 'idle',
        expandedTerms: [],
        retrievalQueries: [],
        candidateCount: null,
        filteredCount: null,
        returnedCount: null,
        errorMessage: null,
      }

      switch (event.event) {
        case 'expanded_terms':
          return {
            ...base,
            question: event.data.question,
            stage: 'expanded_terms',
            expandedTerms: event.data.expanded_terms,
            retrievalQueries: event.data.retrieval_queries,
            errorMessage: null,
          }
        case 'candidates_found':
          return {
            ...base,
            question: event.data.question,
            stage: 'candidates_found',
            candidateCount: event.data.candidate_count,
            errorMessage: null,
          }
        case 'filtered_results':
          return {
            ...base,
            question: event.data.question,
            stage: 'filtered_results',
            candidateCount: event.data.candidate_count,
            filteredCount: event.data.filtered_count,
            returnedCount: event.data.returned_count,
            errorMessage: null,
          }
        case 'complete':
          setChatResponse(event.data)
          return {
            ...base,
            question: event.data.question,
            stage: 'complete',
            expandedTerms: event.data.expanded_terms,
            candidateCount: event.data.candidate_count,
            filteredCount: event.data.filtered_count,
            returnedCount: event.data.returned_count,
            errorMessage: null,
          }
        case 'error':
          return {
            ...base,
            stage: 'error',
            errorMessage: event.data.message,
          }
      }
    })
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedQuestion = question.trim()
    setSubmittedQuestion(trimmedQuestion)
    chatbotQuery.reset()
    setChatResponse(null)
    setStreamProgress({
      question: trimmedQuestion,
      stage: 'idle',
      expandedTerms: [],
      retrievalQueries: [],
      candidateCount: null,
      filteredCount: null,
      returnedCount: null,
      errorMessage: null,
    })
    chatbotQuery.mutate({
      request: {
        question: trimmedQuestion,
        conversation_context: [],
      },
      onEvent: handleStreamEvent,
    })
  }

  return (
    <main className="app-shell">
      <div className="catalogue-page">
        <section className="catalogue-hero">
          <p className="catalogue-kicker">Australian Budget Catalogue</p>
          <h1 className="catalogue-title">Ask the Budget Chatbot</h1>
          <p className="catalogue-copy">
            Ask for measures related to a policy theme. The chatbot expands your query, searches the catalogue,
            checks the results against your intent, and returns a grounded summary.
          </p>
          <p className="page-link-row">
            <Link to="/" className="page-link">
              Browse direct search
            </Link>
          </p>
        </section>

        <section className="search-panel">
          <form className="search-form" onSubmit={handleSubmit}>
            <label className="search-filter-field">
              <span className="search-filter-label">Question</span>
              <textarea
                className="chat-input"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Tell me about measures related to housing affordability"
                rows={5}
              />
            </label>

            <div className="chat-starter-row">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="chat-starter-pill"
                  onClick={() => setQuestion(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="search-form-row">
              <div className="search-meta">
                The current flow uses OpenAI for query expansion, relevance filtering, and answer summarisation.
              </div>
              <button type="submit" className="search-button" disabled={chatbotQuery.isPending || !question.trim()}>
                {chatbotQuery.isPending ? 'Thinking...' : 'Ask chatbot'}
              </button>
            </div>
          </form>
        </section>

        <ChatbotProgress
          question={submittedQuestion.trim() || STARTER_PROMPTS[0]}
          progress={streamProgress}
          response={chatResponse}
        />

        {chatbotQuery.isError ? (
          <section className="results-error">Unable to reach the chatbot backend. Check the API server and OpenAI configuration.</section>
        ) : null}

        {chatResponse ? <ChatbotResults response={chatResponse} /> : null}
      </div>
    </main>
  )
}