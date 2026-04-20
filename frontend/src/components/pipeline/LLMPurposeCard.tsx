import { useState, useEffect } from "react"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import { toast } from "sonner"
import { useUpdateLlmConfig, type LlmPurposeConfig, type PipelineState } from "@/hooks/api"
import { PROMPT_PURPOSE_MAP, type LLMPurpose } from "./prompt-map"
import { LLMPurposePromptEditor } from "./LLMPurposePromptEditor"

interface Props {
  purpose: LLMPurpose
  config: LlmPurposeConfig
  prompts: PipelineState["prompts"]
  onObsoleteDetected?: (counts: { memories: number; code_chunks: number; entities: number }) => void
}

export function LLMPurposeCard({ purpose, config, prompts, onObsoleteDetected }: Props) {
  const update = useUpdateLlmConfig()
  const [open, setOpen] = useState(purpose === "extraction")
  const [draft, setDraft] = useState<LlmPurposeConfig>(config)
  const [paramsText, setParamsText] = useState(
    Object.keys(config.params || {}).length ? JSON.stringify(config.params, null, 2) : "",
  )
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    // Don't stomp in-progress edits when the aggregator refetches (e.g. after
    // window-focus invalidation). Sync only when the card is clean.
    if (dirty) return
    setDraft(config)
    setParamsText(
      Object.keys(config.params || {}).length ? JSON.stringify(config.params, null, 2) : "",
    )
  }, [config, dirty])

  const promptKeys = PROMPT_PURPOSE_MAP[purpose]

  const save = () => {
    const payload: Record<string, unknown> = {
      provider: draft.provider,
      base_url: draft.base_url,
      model: draft.model,
      reasoning: draft.reasoning,
      tool_call_mode: draft.tool_call_mode,
    }
    if (draft.api_key && draft.api_key !== "***") payload.api_key = draft.api_key
    if (purpose === "embedding" && draft.dimensions) payload.dimensions = draft.dimensions
    if (paramsText.trim()) {
      try {
        payload.params = JSON.parse(paramsText)
      } catch {
        toast.error("Invalid JSON in params")
        return
      }
    }
    update.mutate({ [purpose]: payload }, {
      onSuccess: (data) => {
        setDirty(false)
        const obs = data.obsolete_after_change
        if (obs && (obs.memories > 0 || obs.code_chunks > 0 || obs.entities > 0)) {
          onObsoleteDetected?.(obs)
        } else {
          toast.success(`${purpose} updated`)
        }
      },
      onError: (err) => toast.error(`Save failed: ${err.message}`),
    })
  }

  const cancel = () => {
    setDraft(config)
    setParamsText(
      Object.keys(config.params || {}).length ? JSON.stringify(config.params, null, 2) : "",
    )
    setDirty(false)
  }

  return (
    <Card className={`${open ? "border-primary" : ""}`}>
      <button
        type="button"
        className="w-full text-left p-2 flex justify-between items-center"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="text-xs font-semibold capitalize">{open ? "▾" : "▸"} {purpose}</span>
        <span className="text-[10px] text-muted-foreground font-mono">
          {config.model}{config.dimensions ? ` · ${config.dimensions}d` : ""} · {config.provider}
        </span>
      </button>
      {open && (
        <CardContent className="space-y-3 pt-0">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Provider" value={draft.provider} onChange={(v) => patch({ provider: v })} />
            <Field label="Model" mono value={draft.model} onChange={(v) => patch({ model: v })} />
            <Field label="Base URL" mono value={draft.base_url} onChange={(v) => patch({ base_url: v })} />
            <Field label="API key" mono type="password" value={draft.api_key ?? ""} onChange={(v) => patch({ api_key: v })} />
            {purpose === "embedding" && (
              <Field
                label="Dimensions"
                value={String(draft.dimensions ?? "")}
                onChange={(v) => patch({ dimensions: Number(v) || null })}
              />
            )}
          </div>

          {purpose === "extraction" && (
            <div className="flex items-center gap-2">
              <Label className="text-xs">Mode</Label>
              <select
                value={draft.tool_call_mode}
                onChange={(e) => patch({ tool_call_mode: e.target.value })}
                className="h-7 text-xs rounded border border-border bg-background px-2"
              >
                <option value="json">JSON</option>
                <option value="flat">Flat tool call</option>
                <option value="nested">Nested tool call</option>
              </select>
            </div>
          )}

          {purpose !== "embedding" && (
            <div className="flex items-center gap-2">
              <Label className="text-xs">Reasoning mode</Label>
              <Switch checked={draft.reasoning} onCheckedChange={(v) => patch({ reasoning: v })} />
            </div>
          )}

          <details>
            <summary className="text-[10px] text-muted-foreground cursor-pointer">More… (JSON params)</summary>
            <Textarea
              value={paramsText}
              onChange={(e) => {
                setParamsText(e.target.value)
                setDirty(true)
              }}
              rows={3}
              className="text-xs font-mono mt-1"
              placeholder='{"temperature": 0.2}'
            />
          </details>

          {dirty && (
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={cancel} disabled={update.isPending}>Cancel</Button>
              <Button size="sm" onClick={save} disabled={update.isPending}>
                {update.isPending ? "Saving…" : "Save"}
              </Button>
            </div>
          )}

          <LLMPurposePromptEditor keys={promptKeys} prompts={prompts} />
        </CardContent>
      )}
    </Card>
  )

  function patch(p: Partial<LlmPurposeConfig>) {
    setDraft((d) => ({ ...d, ...p }))
    setDirty(true)
  }
}

function Field({
  label,
  value,
  onChange,
  mono,
  type,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  mono?: boolean
  type?: string
}) {
  return (
    <div>
      <Label className="text-[10px] text-muted-foreground">{label}</Label>
      <Input
        type={type ?? "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`h-7 text-xs ${mono ? "font-mono" : ""}`}
      />
    </div>
  )
}
