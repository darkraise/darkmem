import { toast } from "darkraise-ui/components/sonner"
import { DEMO } from "@/lib/demo-flag"
import { useDemoLLM } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type {
  DemoCodeBucket,
  DemoLLMPurpose,
  LLMPurposeName,
} from "@/features/settings/types"
import {
  useHealth,
  useLlmConfig,
  useUpdateLlmConfig,
  type HealthStatus,
  type LlmPurposeConfig,
} from "@/hooks/api"
import { TIER_C_LLM_PURPOSES, type TierCLLMPurpose } from "./llm-tier-c-purposes"

/** Documentation copy for the seven writable purposes in real (non-demo)
 *  mode — the six always-live ones plus `synthesis` (T2.106). Connection
 *  fields (model/api_kind/base_url/...) come from the API; this is only the
 *  descriptive text the demo fixture also carries, kept short here rather
 *  than imported from the demo module (real code should not depend on
 *  `@/demo/**` fixture data). */
const LIVE_PURPOSE_META: Record<LLMPurposeName, { role: string }> = {
  embedding: {
    role: "embeds memories, entities, code and search queries",
  },
  extraction: {
    role: "extracts entities and relations from new memories",
  },
  classification: {
    role: "labels and summarises new memories",
  },
  reasoning: {
    role: "memory reasoning, chat and background refinement",
  },
  summarization: {
    role: "code summaries and the code wiki",
  },
  reranker: {
    role: "re-scores the top search results when the reranker is on",
  },
  synthesis: {
    role: "article and research write-ups",
  },
}

const LIVE_PURPOSES = Object.keys(LIVE_PURPOSE_META) as Array<
  keyof typeof LIVE_PURPOSE_META
>

export interface TierCPurposeView extends TierCLLMPurpose {
  model: string
  api_kind: string
  provider_name: string
}

/** Demo mode has no backend row for the one remaining Tier-C purpose (the
 *  demo store's `CURATED_LLM_PURPOSES` fixture covers the seven writable
 *  ones, `synthesis` included since T2.106), so this is a small demo-only
 *  display fixture — not a mirror of backend truth the way the retired
 *  hardcoded constant was, just the same kind of placeholder every other
 *  demo fixture in this tab already is. */
const DEMO_TIER_C_CONNECTION: Record<
  TierCLLMPurpose["purpose"],
  { model: string; api_kind: string; provider_name: string }
> = {
  verification: {
    model: "qwen2.5:3b",
    api_kind: "ollama",
    provider_name: "ollama-local",
  },
}

function toDemoPurpose(
  purpose: keyof typeof LIVE_PURPOSE_META,
  cfg: LlmPurposeConfig | undefined,
): DemoLLMPurpose {
  const meta = LIVE_PURPOSE_META[purpose]
  return {
    purpose,
    role: meta.role,
    provider_name: cfg?.provider_name ?? "",
    model: cfg?.model ?? "",
    api_kind: (cfg?.api_kind as DemoLLMPurpose["api_kind"]) ?? "openai",
    base_url: cfg?.base_url ?? "",
    api_key: cfg?.api_key ?? "",
    params: JSON.stringify(cfg?.params ?? {}),
    dimensions: purpose === "embedding" ? (cfg?.dimensions ?? undefined) : undefined,
    reasoning: purpose === "embedding" ? undefined : (cfg?.reasoning ?? false),
  }
}

function toWirePatch(
  patch: Partial<Omit<DemoLLMPurpose, "purpose">>,
): Record<string, unknown> {
  const wire: Record<string, unknown> = { ...patch }
  if (typeof patch.params === "string") {
    const trimmed = patch.params.trim()
    wire.params = trimmed === "" ? {} : JSON.parse(trimmed)
  }
  if (typeof patch.dimensions === "string") {
    wire.dimensions = Number(patch.dimensions) || null
  }
  return wire
}

export interface LLMTabBinding {
  purposes: DemoLLMPurpose[]
  /** The one remaining Tier-C purpose, read-only (see
   *  llm-tier-c-purposes.ts). `synthesis` moved into `purposes` above. */
  tierCPurposes: TierCPurposeView[]
  classifierKind: "llm" | "local"
  /** `/health` says the stored `local` classifier cannot load here, so
   *  classification runs on the LLM classifier. Never true in demo mode. */
  classifierUnavailable: boolean
  /** `/health`'s `pipeline_state`; null in demo mode and before it answers. */
  pipelineState: HealthStatus["pipeline_state"] | null
  /** null = not live-bound in this mode (real mode has no buckets endpoint
   *  yet — there is no backend table for these, demo or otherwise). */
  buckets: DemoCodeBucket[] | null
  /** Resolves once the write lands, announcing it; rejects with the
   *  server's refusal, which the purpose dialog shows. */
  savePurpose: (
    purpose: LLMPurposeName,
    patch: Partial<Omit<DemoLLMPurpose, "purpose">>,
  ) => Promise<void>
  setClassifierKind: (kind: "llm" | "local") => void
  saveCodeBucket: ((key: DemoCodeBucket["key"], model: string) => void) | null
  isLoading: boolean
  /** The configuration read failed: `purposes` and `tierCPurposes` are then
   *  empty, never placeholders that would read as the stored values. */
  error: Error | null
  retry: () => void
}

/** Binds the LLM tab to `/config/llm` outside demo mode; in demo mode it
 * keeps the store fixture so the showcase still needs no backend — the
 * same gate `useContributionCalendar` established for the dashboard
 * calendar. Both query hooks run unconditionally (rules of hooks); only
 * the network request is skipped via `enabled`. */
/** A save is an event, so it reports as one. The banner this replaces sat in
 *  the layout until dismissed and pushed the cards down on every save. The
 *  fields it named are kept — they are the part that says what actually
 *  changed — while the orchestrator-rebuild prose that filled the rest of it
 *  was the same sentence on every save and is gone. */
function announceSave(purpose: string, fields: string[]) {
  toast.success(`Saved — ${purpose} purpose updated`, {
    description: fields.join(", "),
  })
}

function announceFailure(purpose: string, error: Error) {
  toast.error(`Couldn’t save the ${purpose} purpose`, {
    description: error.message,
  })
}

export function useLLMTabBinding(): LLMTabBinding {
  const demo = useDemoLLM()
  const saveDemoPurpose = useDemoStore((s) => s.saveLLMPurpose)
  const setDemoClassifierKind = useDemoStore((s) => s.setClassifierKind)
  const saveDemoBucket = useDemoStore((s) => s.saveCodeBucket)

  const query = useLlmConfig(!DEMO)
  const update = useUpdateLlmConfig()
  const health = useHealth()

  if (DEMO) {
    return {
      purposes: demo.purposes,
      tierCPurposes: TIER_C_LLM_PURPOSES.map((p) => ({
        ...p,
        ...DEMO_TIER_C_CONNECTION[p.purpose],
      })),
      classifierKind: demo.classifier_kind,
      classifierUnavailable: false,
      pipelineState: null,
      buckets: demo.buckets,
      savePurpose: (purpose, patch) => {
        saveDemoPurpose(purpose, patch)
        announceSave(purpose, Object.keys(patch))
        return Promise.resolve()
      },
      setClassifierKind: (kind) => {
        setDemoClassifierKind(kind)
        announceSave("classification", ["classifier_kind"])
      },
      saveCodeBucket: saveDemoBucket,
      isLoading: false,
      error: null,
      retry: () => {},
    }
  }

  const config = query.data
  const purposes = config
    ? LIVE_PURPOSES.map((p) => toDemoPurpose(p, config[p]))
    : []
  const classifierKind =
    (query.data?.classification?.classifier_kind as "llm" | "local" | null) ??
    "llm"
  const tierCPurposes: TierCPurposeView[] = config
    ? TIER_C_LLM_PURPOSES.map((p) => {
        const cfg = config[p.purpose]
        return {
          ...p,
          model: cfg?.model ?? "",
          api_kind: cfg?.api_kind ?? "",
          provider_name: cfg?.provider_name ?? "",
        }
      })
    : []

  return {
    purposes,
    tierCPurposes,
    classifierKind,
    classifierUnavailable: health.data?.classifier_unavailable ?? false,
    pipelineState: health.data?.pipeline_state ?? null,
    buckets: null,
    savePurpose: (purpose, patch) =>
      update
        .mutateAsync({ [purpose]: toWirePatch(patch) })
        .then(() => announceSave(purpose, Object.keys(patch))),
    setClassifierKind: (kind) => {
      update.mutate(
        { classification: { classifier_kind: kind } },
        {
          onSuccess: () => announceSave("classification", ["classifier_kind"]),
          onError: (error) => announceFailure("classification", error),
        },
      )
    },
    saveCodeBucket: null,
    isLoading: query.isPending,
    // A failed refetch keeps the last good config on screen.
    error: config ? null : query.error,
    retry: () => void query.refetch(),
  }
}
