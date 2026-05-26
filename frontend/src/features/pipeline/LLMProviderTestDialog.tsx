import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Label } from "darkraise-ui/components/label"
import { Badge } from "darkraise-ui/components/badge"
import { toast } from "darkraise-ui/components/sonner"
import {
  useProviderModels,
  useTestLlmProvider,
  type LlmProviderTestResponse,
} from "@/hooks/api"

interface Props {
  providerName: string | null
  mode: "chat" | "embedding"
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function LLMProviderTestDialog({ providerName, mode, open, onOpenChange }: Props) {
  const { data: modelsResp, isLoading: modelsLoading, error: modelsError, refetch } =
    useProviderModels(providerName, open)
  const test = useTestLlmProvider()
  const [model, setModel] = useState<string>("")
  const [result, setResult] = useState<LlmProviderTestResponse | null>(null)

  useEffect(() => {
    if (open) {
      setResult(null)
      setModel("")
    }
  }, [open, providerName, mode])

  // Default model selection: pick the first available once models load.
  useEffect(() => {
    if (modelsResp?.models && modelsResp.models.length > 0 && !model) {
      setModel(modelsResp.models[0])
    }
  }, [modelsResp, model])

  const runTest = () => {
    if (!providerName || !model) return
    test.mutate(
      { name: providerName, body: { mode, model } },
      {
        onSuccess: (r) => {
          setResult(r)
          if (r.ok) {
            toast.success(`${providerName}: ${mode} probe OK (${r.latency_ms} ms)`)
          } else {
            toast.error(
              `${providerName}: ${mode} probe failed${r.status_code ? ` (HTTP ${r.status_code})` : ""}`,
            )
          }
        },
        onError: (err) => {
          setResult({
            ok: false,
            status_code: null,
            latency_ms: 0,
            url: "",
            message: err.message,
          })
          toast.error(`Test request failed: ${err.message}`)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            Test {mode === "chat" ? "Chat" : "Embedding"} — {providerName ?? "(no provider)"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <Label className="text-xs">Model</Label>
            {modelsLoading && (
              <p className="text-[10px] text-muted-foreground mt-1">Fetching models…</p>
            )}
            {modelsError && (
              <p className="text-[10px] text-destructive mt-1">
                Could not fetch models: {(modelsError as Error).message}
              </p>
            )}
            {modelsResp?.error && (
              <p className="text-[10px] text-destructive mt-1">
                Provider returned: {modelsResp.error}
              </p>
            )}
            {modelsResp && modelsResp.models.length === 0 && !modelsResp.error && (
              <p className="text-[10px] text-muted-foreground mt-1">
                Provider returned an empty model list. You can type a model name below.
              </p>
            )}
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="h-9 w-full text-sm rounded border border-border bg-background px-2 mt-1"
              disabled={!modelsResp || modelsResp.models.length === 0}
            >
              {modelsResp?.models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            {modelsResp && modelsResp.models.length === 0 && (
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="model id (e.g. gpt-4o-mini)"
                className="h-9 w-full text-sm rounded border border-border bg-background px-2 mt-2 font-mono"
              />
            )}
            {modelsResp?.fetched_via && (
              <p className="text-[10px] text-muted-foreground mt-1">
                Fetched via {modelsResp.fetched_via}
              </p>
            )}
          </div>

          {result && (
            <div className="rounded-md border border-border p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant={result.ok ? "default" : "destructive"} className="text-[10px]">
                  {result.ok ? "OK" : "FAIL"}
                </Badge>
                {result.status_code !== null && (
                  <span className="text-xs">HTTP {result.status_code}</span>
                )}
                <span className="text-xs text-muted-foreground">{result.latency_ms} ms</span>
              </div>
              {result.url && (
                <p className="text-[10px] text-muted-foreground font-mono break-all">
                  {result.url}
                </p>
              )}
              {result.message && (
                <p className="text-[10px] text-muted-foreground break-all">
                  {result.message}
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => refetch()} disabled={modelsLoading}>
            Refresh models
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={runTest} disabled={!model || test.isPending}>
            {test.isPending ? "Testing…" : "Run test"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
