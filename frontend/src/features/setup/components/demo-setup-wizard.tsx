import { useState } from "react"
import type { ReactNode } from "react"
import {
  Check,
  Circle,
  CircleDot,
  Folder,
  GitBranch,
  Loader2,
  RefreshCw,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { GlassPanel } from "@/components/glass-panel"
import { SetupBrand, SetupPasswordField } from "./setup-brand"
import {
  SETUP_API_KINDS,
  SETUP_BASE_PATH,
  SETUP_CRUMBS,
  SETUP_DIRS,
  type SetupKindFixture,
} from "@/demo/data-exports"
import type { ApiKind } from "@/features/settings/types"

const STEP_LABELS = [
  "Admin password",
  "Default LLM provider",
  "Default code repo path",
  "Review & finish",
]

const CHAT_PURPOSES = ["extraction", "classification", "reasoning"] as const

interface LLMDraft {
  kind: ApiKind
  base_url: string
  api_key: string
  fetched: boolean
  models: Record<string, string>
  reasoning: Record<string, boolean>
  skipped: boolean
}

const kindFixture = (kind: ApiKind): SetupKindFixture =>
  SETUP_API_KINDS.find((k) => k.kind === kind) ?? SETUP_API_KINDS[0]!

function StepPill({
  label,
  state,
  className,
}: {
  label: ReactNode
  state: "done" | "active" | "upcoming"
  className?: string
}) {
  const Icon =
    state === "done" ? Check : state === "active" ? CircleDot : Circle
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm whitespace-nowrap",
        className,
        state === "active" &&
          "border-primary/55 text-primary-text bg-primary/10",
        state === "done" && "border-success-edge/50 text-success-text bg-success-solid/8",
        state === "upcoming" && "border-border text-muted-foreground",
      )}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {label}
    </span>
  )
}

export function DemoSetupWizard({ onFinish }: { onFinish: () => void }) {
  const [step, setStep] = useState(0)
  const [finalizing, setFinalizing] = useState(false)
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const first = kindFixture("openai")
  const [llm, setLLM] = useState<LLMDraft>({
    kind: first.kind,
    base_url: first.base_url,
    api_key: "",
    fetched: false,
    models: {},
    reasoning: { reasoning: true },
    skipped: false,
  })
  const [repoSkipped, setRepoSkipped] = useState(false)
  const [selectedDirs, setSelectedDirs] = useState<string[]>(
    SETUP_DIRS.filter((d) => d.git).map((d) => d.name),
  )

  const fixture = kindFixture(llm.kind)
  const passwordOk =
    password.length >= 8 && password.length <= 128 && password === confirm
  // Named, not just a greyed-out Next: a short password used to block the
  // step with nothing but the grey helper line saying why.
  const passwordError =
    password.length > 0 && password.length < 8
      ? "At least 8 characters."
      : password.length > 128
        ? "At most 128 characters."
        : null
  // Mirrors the real wizard's step-2 gate (`missingRequiredModels`), so the
  // preview does not pass an empty provider through to the review.
  const requiredPurposes = [
    ...(fixture.supports_embedding ? ["embedding"] : []),
    ...CHAT_PURPOSES,
  ]
  const missingModels = requiredPurposes.filter(
    (p) => !(llm.models[p] ?? "").trim(),
  )
  const reviewedModels = Object.entries(llm.models).filter(
    ([, model]) => model !== "",
  )
  const nextBlocked =
    (step === 0 && !passwordOk) || (step === 1 && missingModels.length > 0)

  const pickKind = (kind: ApiKind) => {
    const fx = kindFixture(kind)
    setLLM((d) => ({
      ...d,
      kind,
      base_url: fx.base_url,
      fetched: false,
      models: {},
    }))
  }

  const fetchModels = () =>
    setLLM((d) => ({
      ...d,
      fetched: true,
      models: {
        embedding: fixture.supports_embedding ? fixture.models.embedding : "",
        extraction: fixture.models.extraction,
        classification: fixture.models.classification,
        reasoning: fixture.models.reasoning,
      },
    }))

  const finish = () => {
    setFinalizing(true)
    window.setTimeout(onFinish, 900)
  }

  const next = () => setStep((s) => Math.min(s + 1, 3))
  const back = () => setStep((s) => Math.max(s - 1, 0))

  return (
    <GlassPanel className="flex max-h-[90vh] w-full max-w-xl flex-col gap-4 overflow-y-auto p-6">
      <SetupBrand />

      {/* Below sm the four pills wrapped one per row and took a quarter of
          the panel; there only the current step shows, as the real wizard
          does. */}
      <div className="flex flex-wrap justify-center gap-1.5">
        {STEP_LABELS.map((label, i) => (
          <StepPill
            key={label}
            label={
              i === step ? (
                <>
                  <span className="sm:hidden">Step {i + 1} of 4 · </span>
                  <span className="hidden sm:inline">{i + 1}. </span>
                  {label}
                </>
              ) : (
                `${i + 1}. ${label}`
              )
            }
            state={i < step ? "done" : i === step ? "active" : "upcoming"}
            className={i === step ? undefined : "hidden sm:inline-flex"}
          />
        ))}
      </div>

      {step === 0 && (
        <div className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="setup-password" className="text-sm">
              Admin password
            </Label>
            <SetupPasswordField
              id="setup-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={passwordError ? true : undefined}
              aria-describedby="setup-password-help"
              autoFocus
            />
            <span
              id="setup-password-help"
              className="text-muted-foreground text-sm"
            >
              8–128 characters. This is the only admin credential — keep it
              safe.
            </span>
            {passwordError && (
              <span role="alert" className="text-destructive-text text-sm">
                {passwordError}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="setup-confirm" className="text-sm">
              Confirm password
            </Label>
            <SetupPasswordField
              id="setup-confirm"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              aria-invalid={
                confirm !== "" && confirm !== password ? true : undefined
              }
            />
            {confirm !== "" && confirm !== password && (
              <span role="alert" className="text-destructive-text text-sm">
                Passwords do not match.
              </span>
            )}
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="flex flex-col gap-3">
          <div className="border-border bg-card/60 flex flex-col gap-2.5 rounded-md border p-3">
            <span className="text-sm font-semibold">Provider</span>
            <div className="flex flex-col gap-1.5">
              <Label className="text-sm">API kind</Label>
              <Select
                value={llm.kind}
                onValueChange={(v) => pickKind(v as ApiKind)}
              >
                <SelectTrigger aria-label="API kind">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SETUP_API_KINDS.map((k) => (
                    <SelectItem key={k.kind} value={k.kind}>
                      {k.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="setup-base-url" className="text-sm">
                Base URL
              </Label>
              <Input
                id="setup-base-url"
                value={llm.base_url}
                onChange={(e) =>
                  setLLM((d) => ({ ...d, base_url: e.target.value }))
                }
                className="font-mono"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="setup-api-key" className="text-sm">
                API key
              </Label>
              <Input
                id="setup-api-key"
                type="password"
                value={llm.api_key}
                placeholder={
                  llm.kind === "ollama" ? "not required for ollama" : ""
                }
                onChange={(e) =>
                  setLLM((d) => ({ ...d, api_key: e.target.value }))
                }
                className="font-mono"
              />
            </div>
            <div className="flex items-center gap-2.5">
              <Switch
                checked={fixture.supports_embedding}
                disabled
                aria-label="Provider supports embeddings"
              />
              <span className="text-sm">
                Provider supports embeddings
                <span className="text-muted-foreground block text-sm">
                  Auto-set from API kind (off for Anthropic and DeepSeek).
                </span>
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2.5">
              <Button variant="outline" onClick={fetchModels}>
                <RefreshCw className="mr-1.5 size-3.5" />
                Fetch available models
              </Button>
              {llm.fetched && (
                <span className="text-muted-foreground text-sm">
                  {fixture.fetched_note}
                </span>
              )}
            </div>
          </div>
          <div className="border-border bg-card/60 flex flex-col gap-2 rounded-md border p-3">
            <span className="text-sm font-semibold">Per-purpose models</span>
            <div className="grid grid-cols-[104px_1fr_auto] items-center gap-2">
              <span className="text-sm font-semibold">
                embedding
                {fixture.supports_embedding && (
                  <span className="text-destructive-text">*</span>
                )}
              </span>
              <Input
                value={llm.models.embedding ?? ""}
                placeholder="model id"
                disabled={!fixture.supports_embedding}
                aria-label="embedding model"
                onChange={(e) =>
                  setLLM((d) => ({
                    ...d,
                    models: { ...d.models, embedding: e.target.value },
                  }))
                }
                className="font-mono"
              />
              <span />
              {CHAT_PURPOSES.map((purpose) => (
                <div key={purpose} className="contents">
                  <span className="text-sm font-semibold capitalize">
                    {purpose}
                    <span className="text-destructive-text">*</span>
                  </span>
                  <Input
                    value={llm.models[purpose] ?? ""}
                    placeholder="model id"
                    aria-label={`${purpose} model`}
                    onChange={(e) =>
                      setLLM((d) => ({
                        ...d,
                        models: { ...d.models, [purpose]: e.target.value },
                      }))
                    }
                    className="font-mono"
                  />
                  <span className="text-muted-foreground flex items-center gap-1.5 text-sm whitespace-nowrap">
                    <Switch
                      checked={llm.reasoning[purpose] ?? false}
                      onCheckedChange={(on) =>
                        setLLM((d) => ({
                          ...d,
                          reasoning: { ...d.reasoning, [purpose]: on },
                        }))
                      }
                      aria-label={`${purpose} reasoning`}
                    />
                    reasoning
                  </span>
                </div>
              ))}
            </div>
            <span className="text-muted-foreground text-sm">
              Required purposes (*) are extraction, classification, reasoning,
              and embedding when the provider supports it; summarization and
              reranker stay optional and inherit sensible defaults.
            </span>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-3">
          <div className="border-border bg-card/60 flex flex-col gap-2 rounded-md border p-3">
            <span className="text-sm font-semibold">
              Browse server filesystem
            </span>
            <div className="text-muted-foreground flex flex-wrap items-center gap-1 font-mono text-sm">
              {SETUP_CRUMBS.map((seg, i) => (
                <span key={seg} className="flex items-center gap-1">
                  <span
                    className={cn(
                      "rounded px-1.5 py-0.5",
                      i === SETUP_CRUMBS.length - 1 &&
                        "text-foreground bg-muted/50",
                    )}
                  >
                    {seg}
                  </span>
                  {i < SETUP_CRUMBS.length - 1 && <span>›</span>}
                </span>
              ))}
            </div>
            <div className="flex flex-col gap-1">
              {SETUP_DIRS.map((dir) => {
                const selected = selectedDirs.includes(dir.name)
                // A folder without .git cannot be imported; it is listed as
                // a plain muted row, not a disabled button that looks like a
                // control the demo forgot to wire.
                if (!dir.git) {
                  return (
                    <div
                      key={dir.name}
                      className="text-muted-foreground flex items-center gap-2 px-2 py-1.5 text-sm"
                    >
                      <Folder aria-hidden className="h-3.5 w-3.5" />
                      {dir.name}
                      <span className="ml-auto text-xs">
                        not a git repository
                      </span>
                    </div>
                  )
                }
                return (
                  <button
                    key={dir.name}
                    type="button"
                    aria-pressed={selected}
                    onClick={() =>
                      setSelectedDirs((prev) =>
                        selected
                          ? prev.filter((n) => n !== dir.name)
                          : [...prev, dir.name],
                      )
                    }
                    className={cn(
                      "flex items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left text-sm",
                      selected && "border-primary/50 bg-primary/8",
                    )}
                  >
                    <Folder
                      aria-hidden
                      className="text-muted-foreground h-3.5 w-3.5"
                    />
                    {dir.name}
                    <span className="border-success-edge/60 text-success-text ml-auto inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 font-mono text-xs">
                      <GitBranch aria-hidden className="h-2.5 w-2.5" />
                      git
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
          <span className="text-muted-foreground text-sm">
            Selected base path:{" "}
            <code className="font-mono">{SETUP_BASE_PATH}</code> — found{" "}
            <b className="text-foreground font-semibold">
              {selectedDirs.length}
            </b>{" "}
            {selectedDirs.length === 1 ? "repository" : "repositories"}.
            Detected .git folders are pre-selected; imported repositories start
            with auto-sync off.
          </span>
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-col gap-3">
          <div className="border-border bg-card/60 flex flex-col gap-1 rounded-md border p-3">
            <span className="text-sm font-semibold">Admin password</span>
            <span className="text-muted-foreground text-sm">Set</span>
          </div>
          <div className="border-border bg-card/60 flex flex-col gap-1.5 rounded-md border p-3">
            <span className="text-sm font-semibold">Default LLM provider</span>
            {llm.skipped ? (
              <span className="text-muted-foreground text-sm">
                Skipped — defaults to a local Ollama; change it later under
                Settings → LLM.
              </span>
            ) : (
              <>
                <span className="text-muted-foreground text-sm">
                  <b className="text-foreground font-semibold">{llm.kind}</b>
                </span>
                {reviewedModels.length > 0 ? (
                  <ul className="text-foreground ml-4 list-disc text-sm">
                    {reviewedModels.map(([purpose, model]) => (
                      <li key={purpose}>
                        {purpose}: <code className="font-mono">{model}</code>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-warning-text text-sm">
                    No models selected.
                  </span>
                )}
              </>
            )}
          </div>
          <div className="border-border bg-card/60 flex flex-col gap-1.5 rounded-md border p-3">
            <span className="text-sm font-semibold">
              Default code repo path
            </span>
            {repoSkipped ? (
              <span className="text-muted-foreground text-sm">
                Skipped — register repositories later from the Code page.
              </span>
            ) : (
              <>
                <span className="text-muted-foreground text-sm">
                  Base path:{" "}
                  <code className="font-mono">{SETUP_BASE_PATH}</code>
                </span>
                {selectedDirs.map((name) => (
                  <div
                    key={name}
                    className="border-border flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm"
                  >
                    <span className="bg-primary text-primary-foreground flex h-3.5 w-3.5 items-center justify-center rounded-sm">
                      <Check aria-hidden className="h-2.5 w-2.5" />
                    </span>
                    <span className="font-mono">{name}</span>
                  </div>
                ))}
                <span className="text-muted-foreground text-sm">
                  Imported repositories start with auto-sync{" "}
                  <b className="text-foreground font-semibold">off</b>.
                </span>
              </>
            )}
          </div>
          <span className="text-muted-foreground text-sm">
            Nothing has been sent yet — Finish applies these settings.
          </span>
        </div>
      )}

      <div className="border-border flex items-center justify-between gap-2 border-t border-dashed pt-3">
        <Button
          variant="ghost"
          disabled={step === 0 || finalizing}
          onClick={back}
        >
          Back
        </Button>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {step === 1 && missingModels.length > 0 && (
            <span className="text-muted-foreground text-sm">
              Add a model for: {missingModels.join(", ")}
            </span>
          )}
          {(step === 1 || step === 2) && (
            <Button
              variant="outline"
              disabled={finalizing}
              onClick={() => {
                if (step === 1) setLLM((d) => ({ ...d, skipped: true }))
                else setRepoSkipped(true)
                next()
              }}
            >
              Skip
            </Button>
          )}
          {step < 3 ? (
            <Button
              disabled={nextBlocked}
              onClick={() => {
                if (step === 1) setLLM((d) => ({ ...d, skipped: false }))
                if (step === 2) setRepoSkipped(false)
                next()
              }}
            >
              Next
            </Button>
          ) : (
            <Button disabled={finalizing} onClick={finish}>
              {finalizing && (
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              )}
              {finalizing ? "Finalizing…" : "Finish"}
            </Button>
          )}
        </div>
      </div>
      <span className="text-muted-foreground text-center text-xs">
        Demo mode — no real setup call is made; Finish opens the app.
      </span>
    </GlassPanel>
  )
}
