import { DEMO } from "@/lib/demo-flag"
import { useDemoFlags } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type {
  DemoBehavioralFlag,
  DemoCorroborationGate,
  DemoGraphFlag,
  DemoRankArm,
} from "@/features/settings/types"
import {
  useFeatureFlags,
  useRepoAllowlist,
  useUpdateFeatureFlags,
  useUpdateRepoAllowlist,
} from "@/hooks/api"

/** Mirrors `FEATURE_FLAGS_DEFAULTS` in `backend/app/config.py` — display-only
 *  (whether a value is a written override), not a second validity check, so
 *  duplicating it here carries none of ruling 2's "two validators" risk. */
const CODED_DEFAULTS: Record<string, number> = {
  confidence_rank_gamma: 0,
  w_importance: 0,
  w_heat: 0,
  w_recency: 0,
  w_context_boost: 0,
}

const BEHAVIORAL_DEFAULTS: Record<string, boolean> = {
  hybrid_search_enabled: true,
  reranker_enabled: false,
  relation_rescue: true,
}

const FUSION_ARM_META: Record<
  string,
  { alias?: string; desc: string; step: number }
> = {
  confidence_rank_gamma: {
    alias: "w_conf",
    desc: "1 + w·(confidence − 0.75)",
    step: 0.05,
  },
  w_importance: {
    desc: "1 + w·(importance − 0.5) — column populated, unread before this arm ships",
    step: 0.05,
  },
  w_heat: {
    desc: "1 + w·heat_norm, heat computed in SQL from memory_access_stats",
    step: 0.05,
  },
  w_recency: {
    desc: "1 + w·recency_norm, from last_accessed / created_at",
    step: 0.05,
  },
}

const BEHAVIORAL_META: Record<string, string> = {
  hybrid_search_enabled:
    "RRF fusion of semantic + keyword search, k=60 — the retrieval baseline the G-A gate already measured",
  reranker_enabled:
    "LLM-scores the top-40 RRF rows before serving — flips only on a measured win including its p95 cost (gate-ledger.md standing conditional gate)",
  relation_rescue:
    "pattern-based rescue layer for relations the extractor misses (adjacency, subject-tracking, REPLACES)",
}

export interface FlagsTabBinding {
  fusionArms: DemoRankArm[]
  contextBoost: DemoRankArm
  behavioralFlags: DemoBehavioralFlag[]
  /** false in real mode: no backend flag exists yet for ppr/dual-level/
   *  community-injection (doc 07 §4/§11) — rendered honestly rather than
   *  fetched against a guessed contract (the T1.61 buffer-monitor precedent). */
  graphAugmentationAvailable: boolean
  graphFlags: DemoGraphFlag[]
  /** false in real mode: the verification ladder (candidate → corroborated)
   *  is E2/T2.03 scope and has no config row yet. */
  corroborationAvailable: boolean
  corroboration: DemoCorroborationGate
  allowlistPatterns: string[]
  overridesWritten: number
  isLoading: boolean
  saveArm: (key: string, value: number) => void
  setBehavioralFlag: (key: string, enabled: boolean) => void
  setGraphFlag: (key: string, enabled: boolean) => void
  saveCorroboration: (nBase: number, nDiverse: number) => void
  saveAllowlist: (patterns: string[]) => void
}

function armFrom(
  flag: string,
  value: number,
  activation: string | null | undefined,
  measurable: string[],
  measured: string[],
): DemoRankArm {
  const meta = FUSION_ARM_META[flag]
  return {
    key: flag,
    alias: meta?.alias,
    desc: meta?.desc ?? flag,
    value,
    coded_default: CODED_DEFAULTS[flag] ?? 0,
    source: value === (CODED_DEFAULTS[flag] ?? 0) ? "default" : "override",
    step: meta?.step ?? 0.05,
    activatesWith: activation ?? undefined,
    unmeasured: measurable.includes(flag) && !measured.includes(flag),
  }
}

/** Binds the Flags tab to `/config/feature-flags` + `/config/repo-allowlist`
 * outside demo mode; in demo mode it keeps the store fixture — the same
 * gate `useContributionCalendar` established for the dashboard calendar and
 * `useLLMTabBinding` established for the LLM tab. Both query hooks run
 * unconditionally (rules of hooks); only the network request is skipped via
 * `enabled`. */
export function useFlagsTabBinding(): FlagsTabBinding {
  const demoFlags = useDemoFlags()
  const saveDemoArm = useDemoStore((s) => s.saveArm)
  const setDemoGraphFlag = useDemoStore((s) => s.setGraphFlag)
  const saveDemoCorroboration = useDemoStore((s) => s.saveCorroboration)
  const setDemoBehavioralFlag = useDemoStore((s) => s.setBehavioralFlag)
  const saveDemoAllowlist = useDemoStore((s) => s.saveRepoAllowlist)

  const flagsQuery = useFeatureFlags(!DEMO)
  const updateFlags = useUpdateFeatureFlags()
  const allowlistQuery = useRepoAllowlist(!DEMO)
  const updateAllowlist = useUpdateRepoAllowlist()

  if (DEMO) {
    return {
      fusionArms: demoFlags.fusion_arms,
      contextBoost: demoFlags.context_boost,
      behavioralFlags: demoFlags.behavioral_flags,
      graphAugmentationAvailable: true,
      graphFlags: demoFlags.graph_flags,
      corroborationAvailable: true,
      corroboration: demoFlags.corroboration,
      allowlistPatterns: demoFlags.repo_allowlist.patterns,
      overridesWritten: demoFlags.overrides_written,
      isLoading: false,
      saveArm: saveDemoArm,
      setBehavioralFlag: setDemoBehavioralFlag,
      setGraphFlag: setDemoGraphFlag,
      saveCorroboration: saveDemoCorroboration,
      saveAllowlist: saveDemoAllowlist,
    }
  }

  const flags = flagsQuery.data
  const measurable = flags?.measurable_flags ?? []
  const measured = flags?.measured_flags ?? []
  const rankArmByFlag = new Map(
    (flags?.rank_arms ?? []).map((a) => [a.flag, a.activation]),
  )

  const fusionArms: DemoRankArm[] = flags
    ? [
        armFrom(
          "confidence_rank_gamma",
          flags.confidence_rank_gamma,
          rankArmByFlag.get("confidence_rank_gamma"),
          measurable,
          measured,
        ),
        armFrom(
          "w_importance",
          flags.w_importance,
          rankArmByFlag.get("w_importance"),
          measurable,
          measured,
        ),
        armFrom(
          "w_heat",
          flags.w_heat,
          rankArmByFlag.get("w_heat"),
          measurable,
          measured,
        ),
        armFrom(
          "w_recency",
          flags.w_recency,
          rankArmByFlag.get("w_recency"),
          measurable,
          measured,
        ),
      ]
    : []

  const contextBoost: DemoRankArm = flags
    ? armFrom(
        "w_context_boost",
        flags.w_context_boost,
        rankArmByFlag.get("w_context_boost"),
        measurable,
        measured,
      )
    : armFrom("w_context_boost", 0, undefined, [], [])

  const behavioralFlags: DemoBehavioralFlag[] = flags
    ? (
        [
          "hybrid_search_enabled",
          "reranker_enabled",
          "relation_rescue",
        ] as const
      ).map((key) => ({
        key,
        desc: BEHAVIORAL_META[key] ?? key,
        enabled: flags[key] as boolean,
        source:
          (flags[key] as boolean) === BEHAVIORAL_DEFAULTS[key]
            ? "default"
            : "override",
        unmeasured: measurable.includes(key) && !measured.includes(key),
      }))
    : []

  const overridesWritten =
    fusionArms.filter((a) => a.source === "override").length +
    (contextBoost.source === "override" ? 1 : 0) +
    behavioralFlags.filter((f) => f.source === "override").length

  return {
    fusionArms,
    contextBoost,
    behavioralFlags,
    graphAugmentationAvailable: false,
    graphFlags: [],
    corroborationAvailable: false,
    corroboration: {
      n_base: 0,
      n_diverse: 0,
      source: "default",
      gate_note: "",
    },
    allowlistPatterns: allowlistQuery.data?.patterns ?? [],
    overridesWritten,
    isLoading: flagsQuery.isLoading,
    saveArm: (key, value) => {
      updateFlags.mutate({ [key]: value })
    },
    setBehavioralFlag: (key, enabled) => {
      updateFlags.mutate({ [key]: enabled })
    },
    setGraphFlag: () => {
      // No backend row exists yet in either direction — see
      // graphAugmentationAvailable. Never wired to a guessed contract.
    },
    saveCorroboration: () => {
      // Owned by T2.03 (the verification ladder) — no config row yet.
    },
    saveAllowlist: (patterns) => {
      updateAllowlist.mutate(patterns)
    },
  }
}
