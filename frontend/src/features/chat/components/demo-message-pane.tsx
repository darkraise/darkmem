import { CircleCheck, MessageCircle, TriangleAlert } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { ChatInput } from "./chat-input"
import type { DemoChatThread } from "@/demo/types"

const STARTERS = [
  "Is the reranker on by default?",
  "What changed in cookie_secure this week?",
  "Summarize open review-queue disputes",
]

export function DemoMessagePane({
  thread,
  selectedTurnId,
  onSelectTurn,
  onSend,
}: {
  thread: DemoChatThread | undefined
  /** The assistant message whose context the panel shows. */
  selectedTurnId: string | null
  onSelectTurn: (messageId: string) => void
  onSend: (content: string) => void
}) {
  const send = (content: string) => {
    const trimmed = content.trim()
    if (trimmed === "") return
    onSend(trimmed)
  }

  return (
    <div className="border-border bg-card flex min-h-[24rem] flex-col overflow-hidden rounded-md border lg:min-h-0 lg:rounded-none lg:border-0 lg:bg-transparent">
      <div className="border-border flex flex-wrap items-center gap-2 border-b px-3.5 py-2.5">
        <span className="mr-auto text-sm font-semibold">
          {thread?.title ?? "New conversation"}
        </span>
      </div>

      {thread && thread.messages.length > 0 ? (
        <div className="flex flex-1 flex-col gap-3.5 overflow-y-auto p-3.5">
          {thread.messages.map((message) =>
            message.role === "user" ? (
              <div
                key={message.id}
                className="flex max-w-[86%] flex-col items-end gap-1 self-end"
              >
                <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
                  you
                </span>
                <div className="bg-primary text-primary-foreground rounded-md px-3 py-2 text-sm leading-relaxed">
                  {message.content}
                </div>
              </div>
            ) : (
              <div
                key={message.id}
                className="flex max-w-[86%] flex-col items-start gap-1 self-start"
              >
                <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
                  assistant
                </span>
                <div
                  className={cn(
                    "border-border bg-muted/50 space-y-2 rounded-md border px-3 py-2 text-sm leading-relaxed",
                    message.id === selectedTurnId && "border-primary/45",
                  )}
                >
                  <p>{message.content}</p>
                  {message.bullets && (
                    <ul className="text-muted-foreground list-disc space-y-0.5 pl-4">
                      {message.bullets.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  )}
                </div>
                {message.context && (
                  <button
                    type="button"
                    onClick={() => onSelectTurn(message.id)}
                    className={cn(
                      "inline-flex items-center gap-1.5 text-sm",
                      message.id === selectedTurnId
                        ? "text-primary-text"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {message.context.degraded ? (
                      <TriangleAlert
                        aria-hidden
                        className="text-warning-text h-3 w-3"
                      />
                    ) : (
                      <CircleCheck aria-hidden className="h-3 w-3" />
                    )}
                    {message.context.rows.length}{" "}
                    {message.context.rows.length === 1 ? "source" : "sources"}
                  </button>
                )}
              </div>
            ),
          )}
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2.5 p-7 text-center">
          <MessageCircle
            aria-hidden
            className="text-muted-foreground h-6 w-6"
          />
          <p className="text-sm font-semibold">
            Ask about your memory, facts, or code
          </p>
          <div className="mt-1 flex flex-wrap justify-center gap-2">
            {STARTERS.map((starter) => (
              <Button
                key={starter}
                variant="outline"
                className="rounded-full border-dashed whitespace-normal"
                onClick={() => send(starter)}
              >
                {starter}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* The real page's composer, so both builds of /chat share one
          multi-line input, its Enter / Shift+Enter hint and its labelling. */}
      <ChatInput onSend={send} placeholder="Ask about your memory…" />
    </div>
  )
}
