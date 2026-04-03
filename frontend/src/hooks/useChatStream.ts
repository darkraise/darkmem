import { useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAuthToken } from "@/lib/api";

interface ChatSources {
  memories: { index: number; content: string; source: string; tags: string[]; score: number }[];
  entities: { id?: string; name?: string; entity_type?: string; [key: string]: unknown }[];
}

interface ChatStreamState {
  isStreaming: boolean;
  streamingContent: string;
  sources: ChatSources | null;
  error: string | null;
}

export function useChatStream() {
  const [state, setState] = useState<ChatStreamState>({
    isStreaming: false,
    streamingContent: "",
    sources: null,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const qc = useQueryClient();

  const sendMessage = useCallback(
    async (
      conversationId: string | null,
      content: string,
      context?: Record<string, unknown>,
    ) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState({ isStreaming: true, streamingContent: "", sources: null, error: null });

      try {
        const token = getAuthToken();
        const res = await fetch("/api/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            conversation_id: conversationId,
            content,
            context: context ?? null,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const err = await res.text();
          setState((s) => ({ ...s, isStreaming: false, error: err }));
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          setState((s) => ({ ...s, isStreaming: false, error: "No stream" }));
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let accumulated = "";
        let resultConversationId: string | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const json = line.slice(6);
            try {
              const event = JSON.parse(json);
              switch (event.type) {
                case "sources":
                  setState((s) => ({
                    ...s,
                    sources: { memories: event.memories, entities: event.entities },
                  }));
                  break;
                case "token":
                  accumulated += event.content;
                  setState((s) => ({ ...s, streamingContent: accumulated }));
                  break;
                case "done":
                  resultConversationId = event.conversation_id;
                  break;
                case "error":
                  setState((s) => ({ ...s, error: event.message }));
                  break;
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }

        setState((s) => ({ ...s, isStreaming: false }));
        if (resultConversationId) {
          qc.invalidateQueries({ queryKey: ["conversation", resultConversationId] });
          qc.invalidateQueries({ queryKey: ["conversations"] });
        }

        return resultConversationId;
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setState((s) => ({ ...s, isStreaming: false, error: (err as Error).message }));
        }
      }
    },
    [qc],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return {
    ...state,
    sendMessage,
    abort,
  };
}
