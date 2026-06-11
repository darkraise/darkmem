import { useState, useEffect } from "react"
import { Textarea } from "darkraise-ui/components/textarea"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { Label } from "darkraise-ui/components/label"
import { toast } from "darkraise-ui/components/sonner"
import { useUpdateSystemPrompts, type PipelineState } from "@/hooks/api"

interface Props {
  keys: string[]
  prompts: PipelineState["prompts"]
}

export function LLMPurposePromptEditor({ keys, prompts }: Props) {
  const update = useUpdateSystemPrompts()
  const [selected, setSelected] = useState(keys[0] ?? "")
  const [draft, setDraft] = useState("")
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!selected) return
    const p = prompts[selected]
    setDraft(p?.override || p?.default || "")
    setDirty(false)
  }, [selected, prompts])

  if (keys.length === 0) return null

  const current = prompts[selected]
  const isOverridden = Boolean(current?.override)
  const isDefault = (current?.default ?? "") === draft

  const save = () => {
    const body = isDefault
      ? { overrides: { [selected]: "" } }
      : { overrides: { [selected]: draft } }
    update.mutate(body, {
      onSuccess: () =>
        toast.success(
          isDefault
            ? `Reverted ${selected} to default`
            : `Saved override for ${selected}`,
        ),
      onError: (err) => toast.error(`Failed: ${err.message}`),
    })
    setDirty(false)
  }

  const loadDefault = () => {
    setDraft(current?.default ?? "")
    setDirty(true)
  }

  return (
    <div>
      <Label className="text-muted-foreground text-sm uppercase">
        System prompts
      </Label>
      {keys.length > 1 && (
        <div className="my-1 flex flex-wrap gap-1">
          {keys.map((k) => (
            <Button
              variant="ghost"
              key={k}
              type="button"
              onClick={() => setSelected(k)}
              className={`rounded border px-2 py-0.5 text-sm ${
                selected === k
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground"
              }`}
            >
              {shortLabel(k)}
              {prompts[k]?.override && (
                <Badge variant="secondary" className="ml-1 text-sm">
                  custom
                </Badge>
              )}
            </Button>
          ))}
        </div>
      )}

      <Textarea
        className="min-h-[120px] font-mono"
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value)
          setDirty(true)
        }}
      />
      <div className="mt-1 flex items-center justify-between">
        <span className="text-muted-foreground text-sm">
          {draft.length.toLocaleString()} / 20,000 ·{" "}
          {isOverridden ? "overridden" : "using default"}
        </span>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            onClick={loadDefault}
            disabled={update.isPending}
          >
            Load default
          </Button>
          <Button onClick={save} disabled={update.isPending || !dirty}>
            {isDefault ? "Clear override" : "Save override"}
          </Button>
        </div>
      </div>
    </div>
  )
}

function shortLabel(key: string): string {
  return key.replace(/^extraction_/, "")
}
