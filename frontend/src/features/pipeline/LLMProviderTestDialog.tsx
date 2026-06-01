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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Input } from "darkraise-ui/components/input"
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

export function LLMProviderTestDialog({
  providerName,
  mode,
  open,
  onOpenChange,
}: Props) {
  const {
    data: modelsResp,
    isLoading: modelsLoading,
    error: modelsError,
    refetch,
  } = useProviderModels(providerName, open)
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
      setModel(modelsResp.models[0] ?? "")
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
            toast.success(
              `${providerName}: ${mode} probe OK (${r.latency_ms} ms)`,
            )
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
            Test {mode === "chat" ? "Chat" : "Embedding"} —{" "}
            {providerName ?? "(no provider)"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <Label className="text-base">Model</Label>
            {modelsLoading && (
              <p className="text-muted-foreground mt-1 text-sm">
                Fetching models…
              </p>
            )}
            {modelsError && (
              <p className="text-destructive mt-1 text-sm">
                Could not fetch models: {(modelsError as Error).message}
              </p>
            )}
            {modelsResp?.error && (
              <p className="text-destructive mt-1 text-sm">
                Provider returned: {modelsResp.error}
              </p>
            )}
            {modelsResp &&
              modelsResp.models.length === 0 &&
              !modelsResp.error && (
                <p className="text-muted-foreground mt-1 text-sm">
                  Provider returned an empty model list. You can type a model
                  name below.
                </p>
              )}
            {modelsResp && modelsResp.models.length > 0 ? (
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger className="mt-1 h-9 w-full text-base">
                  <SelectValue placeholder="Select a model…" />
                </SelectTrigger>
                <SelectContent>
                  {modelsResp.models.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="model id (e.g. gpt-4o-mini)"
                className="mt-2 h-9 w-full font-mono text-base"
              />
            )}
            {modelsResp?.fetched_via && (
              <p className="text-muted-foreground mt-1 text-sm">
                Fetched via {modelsResp.fetched_via}
              </p>
            )}
          </div>

          {result && (
            <div className="border-border space-y-2 rounded-md border p-3">
              <div className="flex items-center gap-2">
                <Badge
                  variant={result.ok ? "default" : "destructive"}
                  className="text-sm"
                >
                  {result.ok ? "OK" : "FAIL"}
                </Badge>
                {result.status_code !== null && (
                  <span className="text-base">HTTP {result.status_code}</span>
                )}
                <span className="text-muted-foreground text-base">
                  {result.latency_ms} ms
                </span>
              </div>
              {result.url && (
                <p className="text-muted-foreground font-mono text-sm break-all">
                  {result.url}
                </p>
              )}
              {result.message && (
                <p className="text-muted-foreground text-sm break-all">
                  {result.message}
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => refetch()}
            disabled={modelsLoading}
          >
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
