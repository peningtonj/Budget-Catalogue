import type { ChatMeasureQueryRequest, ChatMeasureQueryResponse, ChatMeasureStreamEvent } from '../../features/chatbot/types'


type StreamEventHandler = (event: ChatMeasureStreamEvent) => void


function parseServerSentEvent(block: string): ChatMeasureStreamEvent | null {
  const lines = block
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length === 0) {
    return null
  }

  const eventLine = lines.find((line) => line.startsWith('event:'))
  const dataLine = lines.find((line) => line.startsWith('data:'))
  if (!eventLine || !dataLine) {
    return null
  }

  const event = eventLine.slice('event:'.length).trim()
  const data = JSON.parse(dataLine.slice('data:'.length).trim())
  return { event, data } as ChatMeasureStreamEvent
}


export async function queryMeasuresWithChatbot(
  request: ChatMeasureQueryRequest,
  onEvent?: StreamEventHandler,
): Promise<ChatMeasureQueryResponse> {
  const response = await fetch('http://127.0.0.1:8000/chat/measures/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok || !response.body) {
    throw new Error(`API request failed with status ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResponse: ChatMeasureQueryResponse | null = null

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })

    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''

    for (const chunk of chunks) {
      const event = parseServerSentEvent(chunk)
      if (!event) {
        continue
      }

      onEvent?.(event)

      if (event.event === 'complete') {
        finalResponse = event.data
      }

      if (event.event === 'error') {
        throw new Error(event.data.message)
      }
    }

    if (done) {
      break
    }
  }

  if (!finalResponse) {
    throw new Error('Chatbot stream ended before returning a final response')
  }

  return finalResponse
}