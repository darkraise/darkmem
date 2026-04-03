import { useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { SendHorizonal, Square } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
  contextLabel?: string | null;
  onClearContext?: () => void;
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value.trim();
    if (!value || isStreaming || disabled) return;
    onSend(value);
    if (textareaRef.current) textareaRef.current.value = "";
    autoResize();
  }, [onSend, isStreaming, disabled]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  return (
    <div className="border-t border-border p-3">
      {contextLabel && (
        <div className="flex items-center gap-1.5 mb-2 text-xs text-muted-foreground">
          <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full">
            Context: {contextLabel}
          </span>
          <button className="hover:text-foreground" onClick={onClearContext}>×</button>
        </div>
      )}
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="flex-1 bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:border-primary min-h-[36px] max-h-[120px]"
        />
        {isStreaming ? (
          <Button size="sm" variant="outline" className="h-9 w-9 p-0" onClick={onStop}>
            <Square className="w-3.5 h-3.5" />
          </Button>
        ) : (
          <Button size="sm" className="h-9 w-9 p-0" onClick={handleSubmit} disabled={disabled}>
            <SendHorizonal className="w-3.5 h-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
