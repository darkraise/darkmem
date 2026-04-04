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
    <div className="border-t border-border p-3 space-y-2">
      {contextLabel && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
            Context: {contextLabel}
            <button className="hover:text-foreground ml-0.5" onClick={onClearContext}>×</button>
          </span>
        </div>
      )}
      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={placeholder}
            onInput={autoResize}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className="w-full bg-[#0c1018] border border-[rgba(99,102,241,0.12)] rounded-2xl px-4 py-2.5 pr-12 text-sm text-foreground placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40 focus:shadow-[0_0_20px_rgba(99,102,241,0.06)] transition-all min-h-[40px] max-h-[120px]"
          />
          <div className="absolute right-2 bottom-1.5">
            {isStreaming ? (
              <Button size="sm" variant="outline" className="h-7 w-7 p-0 rounded-xl" onClick={onStop}>
                <Square className="w-3 h-3" />
              </Button>
            ) : (
              <Button size="sm" className="h-7 w-7 p-0 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 border-0" onClick={handleSubmit} disabled={disabled}>
                <SendHorizonal className="w-3.5 h-3.5 text-white" />
              </Button>
            )}
          </div>
        </div>
      </div>
      <p className="text-xs text-muted-foreground/30 text-center">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
