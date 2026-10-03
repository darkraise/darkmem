import { useState, useRef, useCallback, useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { handleUnauthorized } from "@/lib/api"
import type {
  ChatContextFact,
  ChatContextRow,
  ChatRetrievalEnvelope,
} from "../lib/retrieval"

export interface ChatSources {
  memories: ChatContextRow[]
  facts: ChatContextFact[]
  entities: {
    id?: string
    name?: string
    entity_type?: string
    [key: string]: unknown
  }[]
  /** Doc 07 §8's envelope, emitted since chat converged onto the composition. */
  envelope: ChatRetrievalEnvelope | null
}

interface ChatStreamState {
  conversationId: string | null
  retryDraft: string | null
  uncertainDraft: string | null
  isStreaming: boolean
  streamingContent: string
  sources: ChatSources | null
  error: string | null
  pendingUserMessage: string | null
}

export function useChatStream(activeConversationId?: string | null) {
  const [state, setState] = useState<ChatStreamState>({
    conversationId: null,
    retryDraft: null,
    uncertainDraft: null,
    isStreaming: false,
    streamingContent: "",
    sources: null,
    error: null,
    pendingUserMessage: null,
  })
  const abortRef = useRef<AbortController | null>(null)
  const qc = useQueryClient()

  useEffect(() => () => abortRef.current?.abort(), [])

  const sendMessage = useCallback(
    async (
      conversationId: string | null,
      content: string,
      context?: Record<string, unknown>,
    ) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setState({
        conversationId,
        retryDraft: null,
        uncertainDraft: null,
        isStreaming: true,
        streamingContent: "",
        sources: null,
        error: null,
        pendingUserMessage: content,
      })

      let resultConversationId: string | null = conversationId
      let completed = false
      let failed = false
      const updateState = (update: (previous: ChatStreamState) => ChatStreamState) => {
        if (abortRef.current === controller && !controller.signal.aborted) setState(update)
      }
      const fail = (message: string, retryable = false) => {
        failed = true
        updateState((previous) => ({
          ...previous,
          error: retryable ? message : `${message}. Your message may already be saved; check the conversation before sending it again.`,
          retryDraft: retryable ? content : null,
          uncertainDraft: retryable ? null : content,
        }))
      }

      const refreshAfterStream = () => {
        if (resultConversationId) {
          qc.invalidateQueries({ queryKey: ["conversation", resultConversationId] })
        }
        // The sidebar list also shows each conversation's updated_at/message_count,
        // which change on every message — refresh it too, not only for new threads.
        qc.invalidateQueries({ queryKey: ["conversations"] })
      }

      try {
        const res = await fetch("/api/v1/chat/completions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            conversation_id: conversationId,
            content,
            context: context ?? null,
          }),
          signal: controller.signal,
        })

        if (!res.ok) {
          if (res.status === 401) handleUnauthorized()
          const err = await res.text()
          fail(err, res.status >= 400 && res.status < 500 && res.status !== 408)
          return
        }

        const reader = res.body?.getReader()
        if (!reader) {
          fail("No stream")
          return
        }

        const decoder = new TextDecoder()
        let buffer = ""
        let accumulated = ""

        while (true) {
          const { done, value } = await reader.read()
          if (controller.signal.aborted || abortRef.current !== controller) {
            await reader.cancel()
            return
          }
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n\n")
          buffer = lines.pop() ?? ""

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue
            const json = line.slice(6)
            try {
              const event = JSON.parse(json)
              if (event.conversation_id) {
                resultConversationId = event.conversation_id
              }
              switch (event.type) {
                case "sources":
                  updateState((previous) => ({
                    ...previous,
                    sources: {
                      memories: event.memories,
                      facts: event.facts ?? [],
                      entities: event.entities,
                      envelope: event.envelope ?? null,
                    },
                  }))
                  break
                case "token":
                  accumulated += event.content
                  updateState((previous) => ({ ...previous, streamingContent: accumulated }))
                  break
                case "error":
                  fail(event.message)
                  break
                case "done":
                  completed = true
                  break
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }

        if (!completed && !failed) fail("Stream ended before completion")

        return resultConversationId
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          fail((err as Error).message)
          return resultConversationId
        }
      } finally {
        updateState((previous) => ({ ...previous, isStreaming: false, pendingUserMessage: null }))
        refreshAfterStream()
      }
    },
    [qc],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setState((s) => ({ ...s, isStreaming: false, pendingUserMessage: null }))
  }, [])

  return {
    ...(activeConversationId === undefined || state.conversationId === activeConversationId ? state : {
      conversationId: activeConversationId,
      isStreaming: false,
      streamingContent: "",
      sources: null,
      error: null,
      pendingUserMessage: null,
      retryDraft: null,
      uncertainDraft: null,
    }),
    sendMessage,
    abort,
  }
}
