import { useMutation } from '@tanstack/react-query'

import { queryMeasuresWithChatbot } from '../../../lib/api/chat'
import type { ChatMeasureQueryRequest, ChatMeasureStreamEvent } from '../types'


type ChatbotQueryVariables = {
  request: ChatMeasureQueryRequest
  onEvent?: (event: ChatMeasureStreamEvent) => void
}


export function useChatbotQuery() {
  return useMutation({
    mutationFn: ({ request, onEvent }: ChatbotQueryVariables) => queryMeasuresWithChatbot(request, onEvent),
  })
}