import { useReducer, useRef, useCallback, useEffect } from "react"
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
  /** The key of the conversation the turn was sent from: its id, or the
   *  caller's own key for an unsaved draft. The turn shows only there. */
  conversationId: string | null
  retryDraft: string | null
  uncertainDraft: string | null
  isStreaming: boolean
  streamingContent: string
  sources: ChatSources | null
  error: string | null
  pendingUserMessage: string | null
}

interface StreamEntry {
  state: ChatStreamState
  controller: AbortController
}

const idle = (conversationId: string | null): ChatStreamState => ({
  conversationId,
  retryDraft: null,
  uncertainDraft: null,
  isStreaming: false,
  streamingContent: "",
  sources: null,
  error: null,
  pendingUserMessage: null,
})

const NO_CONVERSATION = "\u0000none"
const keyOf = (id: string | null) => id ?? NO_CONVERSATION

/** One stream per conversation: a send aborts only an earlier turn of its
 *  own conversation, so a reader can switch conversations, or send in
 *  another, while a turn is still answering. Every stream ends with the
 *  hook's owner. */
export function useChatStream(activeConversationId?: string | null) {
  const streams = useRef(new Map<string, StreamEntry>())
  // A draft has no id until its first turn's events name one; from then the
  // turn is also found under that id.
  const named = useRef(new Map<string, string>())
  const lastSent = useRef<string | null>(null)
  const [, rerender] = useReducer((n: number) => n + 1, 0)
  const qc = useQueryClient()

  useEffect(() => {
    const owned = streams.current
    return () => {
      for (const entry of owned.values()) entry.controller.abort()
    }
  }, [])

  const entryFor = useCallback((key: string) => {
    const direct = streams.current.get(key)
    if (direct) return direct
    const alias = named.current.get(key)
    return alias === undefined ? undefined : streams.current.get(alias)
  }, [])

  const sendMessage = useCallback(
    async (
      conversationId: string | null,
      content: string,
      context?: Record<string, unknown>,
      // A draft has no id until its first turn creates one, so a caller with
      // several drafts names which one is sending; it defaults to the id.
      owner: string | null = conversationId,
    ) => {
      const key = keyOf(owner)
      streams.current.get(key)?.controller.abort()
      named.current.delete(key)
      const controller = new AbortController()
      const entry: StreamEntry = {
        controller,
        state: { ...idle(owner), isStreaming: true, pendingUserMessage: content },
      }
      streams.current.set(key, entry)
      lastSent.current = key
      rerender()

      let resultConversationId: string | null = conversationId
      let completed = false
      let failed = false
      const updateState = (update: (previous: ChatStreamState) => ChatStreamState) => {
        if (streams.current.get(key) !== entry || controller.signal.aborted) return
        entry.state = update(entry.state)
        rerender()
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
          if (controller.signal.aborted || streams.current.get(key) !== entry) {
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
                if (event.conversation_id !== key && !streams.current.has(event.conversation_id)) {
                  named.current.set(event.conversation_id, key)
                }
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

  const activeKey =
    activeConversationId === undefined ? lastSent.current : keyOf(activeConversationId)
  const active = activeKey === null ? undefined : entryFor(activeKey)

  const abort = useCallback(() => {
    if (!active) return
    active.controller.abort()
    active.state = { ...active.state, isStreaming: false, pendingUserMessage: null }
    rerender()
  }, [active])

  return {
    ...(active?.state ?? idle(activeConversationId ?? null)),
    sendMessage,
    abort,
  }
}
