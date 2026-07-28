import { useState } from "react"
import { DEMO } from "@/lib/demo-flag"
import { useDemoLLM } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type {
  DemoCodeBucket,
  DemoLLMPurpose,
  DemoLLMSaveTrace,
  LLMPurposeName,
} from "@/demo/types"
import {
  useLlmConfig,
  useUpdateLlmConfig,
  type LlmPurposeConfig,
} from "@/hooks/api"

/** Documentation copy for the six live purposes in real (non-demo) mode.
 *  Connection fields (model/api_kind/base_url/...) come from the API; this
 *  is only the descriptive text the demo fixture also carries, kept short
 *  here rather than imported from the demo module (real code should not
 *  depend on `@/demo/**` fixture data). */
const LIVE_PURPOSE_META: Record<LLMPurposeName, { tier: string; role: string }> = {
  embedding: {
    tier: "tier A / B / C",
    role: "every vector: content, entity, code chunk, query",
  },
  extraction: {
    tier: "tier B",
    role: "the merged ingest call — entities + relations + classification fields",
  },
  classification: {
    tier: "tier B",
    role: "classification, folded into extraction in simple mode",
  },
  reasoning: {
    tier: "tier A / C",
    role: "memory_reason, conversational chat, Tier-C dream-refine judgments",
  },
  summarization: {
    tier: "tier B / C",
    role: "code enrichment + wiki, fanning out to three code-summarization buckets",
  },
  reranker: {
    tier: "tier A",
    role: "retrieval rerank scoring, top-40 RRF rows, flag-gated",
  },
}

const LIVE_PURPOSES = Object.keys(LIVE_PURPOSE_META) as Array<
  keyof typeof LIVE_PURPOSE_META
>

function toDemoPurpose(
  purpose: keyof typeof LIVE_PURPOSE_META,
  cfg: LlmPurposeConfig | undefined,
): DemoLLMPurpose {
  const meta = LIVE_PURPOSE_META[purpose]
  return {
    purpose,
    tier: meta.tier,
    role: meta.role,
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
  classifierKind: "llm" | "local"
  /** null = not live-bound in this mode (real mode has no buckets endpoint
   *  yet — there is no backend table for these, demo or otherwise). */
  buckets: DemoCodeBucket[] | null
  lastSave: DemoLLMSaveTrace | null
  savePurpose: (
    purpose: LLMPurposeName,
    patch: Partial<Omit<DemoLLMPurpose, "purpose">>,
  ) => void
  setClassifierKind: (kind: "llm" | "local") => void
  saveCodeBucket: ((key: DemoCodeBucket["key"], model: string) => void) | null
  dismissSave: () => void
  isLoading: boolean
}

/** Binds the LLM tab to `/config/llm` outside demo mode; in demo mode it
 * keeps the store fixture so the showcase still needs no backend — the
 * same gate `useContributionCalendar` established for the dashboard
 * calendar. Both query hooks run unconditionally (rules of hooks); only
 * the network request is skipped via `enabled`. */
export function useLLMTabBinding(): LLMTabBinding {
  const demo = useDemoLLM()
  const saveDemoPurpose = useDemoStore((s) => s.saveLLMPurpose)
  const setDemoClassifierKind = useDemoStore((s) => s.setClassifierKind)
  const saveDemoBucket = useDemoStore((s) => s.saveCodeBucket)
  const dismissDemoSave = useDemoStore((s) => s.dismissLLMSave)

  const [realLastSave, setRealLastSave] = useState<DemoLLMSaveTrace | null>(
    null,
  )
  const query = useLlmConfig(!DEMO)
  const update = useUpdateLlmConfig()

  if (DEMO) {
    return {
      purposes: demo.purposes,
      classifierKind: demo.classifier_kind,
      buckets: demo.buckets,
      lastSave: demo.last_save,
      savePurpose: saveDemoPurpose,
      setClassifierKind: setDemoClassifierKind,
      saveCodeBucket: saveDemoBucket,
      dismissSave: dismissDemoSave,
      isLoading: false,
    }
  }

  const purposes = LIVE_PURPOSES.map((p) => toDemoPurpose(p, query.data?.[p]))
  const classifierKind =
    (query.data?.classification?.classifier_kind as "llm" | "local" | null) ??
    "llm"

  return {
    purposes,
    classifierKind,
    buckets: null,
    lastSave: realLastSave,
    savePurpose: (purpose, patch) => {
      update.mutate({ [purpose]: toWirePatch(patch) })
      setRealLastSave({ purpose, fields: Object.keys(patch) })
    },
    setClassifierKind: (kind) => {
      update.mutate({ classification: { classifier_kind: kind } })
      setRealLastSave({ purpose: "classification", fields: ["classifier_kind"] })
    },
    saveCodeBucket: null,
    dismissSave: () => setRealLastSave(null),
    isLoading: query.isLoading,
  }
}
