import { useRef, useCallback, useEffect, useId } from "react"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { Textarea } from "darkraise-ui/components/textarea"
import { Alert, AlertDescription } from "darkraise-ui/components/alert"
import { SendHorizonal, Square, X } from "lucide-react"

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  isStreaming?: boolean
  disabled?: boolean
  placeholder?: string
  contextLabel?: string | null
  onClearContext?: () => void
  error?: string | null
  retryDraft?: string | null
  uncertainDraft?: string | null
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "Ask about your memories…",
  contextLabel,
  onClearContext,
  error,
  retryDraft,
  uncertainDraft,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const hintId = useId()

  useEffect(() => {
    if (retryDraft && textareaRef.current && !textareaRef.current.value) {
      textareaRef.current.value = retryDraft
      autoResize()
    }
  }, [retryDraft])

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
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {uncertainDraft && (
        <Textarea
          aria-label="Unconfirmed message"
          value={uncertainDraft}
          readOnly
        />
      )}
      {contextLabel && (
        <Badge variant="secondary" className="gap-1">
          Context: {contextLabel}
          <Button
            variant="ghost"
            size="icon"
            aria-label="Clear context"
            className="h-6 w-6"
            onClick={onClearContext}
          >
            <X className="h-3 w-3" />
          </Button>
        </Badge>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-label="Message"
          aria-describedby={hintId}
          className="max-h-[120px] min-h-[40px] flex-1 resize-none"
        />
        {isStreaming ? (
          <Button
            variant="outline"
            size="icon"
            aria-label="Stop generating"
            className="shrink-0"
            onClick={onStop}
          >
            <Square className="h-3.5 w-3.5" />
          </Button>
        ) : (
          <Button
            size="icon"
            aria-label="Send message"
            className="shrink-0"
            onClick={handleSubmit}
            disabled={disabled}
          >
            <SendHorizonal className="h-4 w-4" />
          </Button>
        )}
      </div>
      {/* The composer's only instructions: plain muted text (about 7:1),
          not the /30 tint that measured 1.6:1. */}
      <p id={hintId} className="text-muted-foreground text-center text-sm">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
