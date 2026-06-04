import { useRef, useCallback } from "react"
import { Button } from "darkraise-ui/components/button"
import { Textarea } from "darkraise-ui/components/textarea"
import { SendHorizonal, Square } from "lucide-react"
import { ChatGradientButton } from "./chat-gradient-button"

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  isStreaming?: boolean
  disabled?: boolean
  placeholder?: string
  contextLabel?: string | null
  onClearContext?: () => void
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "Ask about your memories... (@ to mention)",
  contextLabel,
  onClearContext,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value.trim()
    if (!value || isStreaming || disabled) return
    onSend(value)
    if (textareaRef.current) textareaRef.current.value = ""
    autoResize()
  }, [onSend, isStreaming, disabled])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit],
  )

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 120) + "px"
  }

  return (
    <div className="border-border space-y-2 border-t p-3">
      {contextLabel && (
        <div className="text-muted-foreground flex items-center gap-1.5 text-base">
          <span className="inline-flex items-center gap-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-2 py-0.5 text-indigo-300">
            Context: {contextLabel}
            <Button
              variant="ghost"
              size="icon"
              aria-label="Clear context"
              className="hover:text-foreground ml-0.5 h-6 w-6"
              onClick={onClearContext}
            >
              ×
            </Button>
          </span>
        </div>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="text-foreground placeholder:text-muted-foreground/50 border-border bg-card max-h-[120px] min-h-[40px] flex-1 resize-none rounded-2xl border px-4 py-2.5 text-base transition-all focus:border-indigo-500/40 focus:shadow-[0_0_20px_rgba(99,102,241,0.06)] focus:ring-2 focus:ring-primary/30 focus:outline-none"
        />
        {isStreaming ? (
          <Button
            variant="outline"
            aria-label="Stop generating"
            className="mb-0.5 h-9 w-9 shrink-0 rounded-xl p-0"
            onClick={onStop}
          >
            <Square className="h-3.5 w-3.5" />
          </Button>
        ) : (
          <ChatGradientButton
            aria-label="Send message"
            className="mb-0.5 h-9 w-9 shrink-0 rounded-xl p-0"
            onClick={handleSubmit}
            disabled={disabled}
          >
            <SendHorizonal className="h-4 w-4 text-white" />
          </ChatGradientButton>
        )}
      </div>
      <p className="text-muted-foreground/30 text-center text-base">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
