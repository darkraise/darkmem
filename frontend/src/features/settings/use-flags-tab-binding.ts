import { useCallback, useState } from "react"
import { DEMO } from "@/lib/demo-flag"
import { MEMORY_TYPES } from "@/lib/taxonomy"
import { useDemoFlags } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type {
  DemoBehavioralFlag,
  DemoCorroborationGate,
  DemoGraphFlag,
  DemoLadderParam,
  DemoRankArm,
  DemoTunable,
} from "@/features/settings/types"
import {
  useClassificationAreas,
  useFeatureFlags,
  useRepoAllowlist,
  useUpdateFeatureFlags,
  useUpdateRepoAllowlist,
  useUpdateVerificationLadder,
  useVerificationLadder,
  type ClassificationAreaInfo,
  type ClassificationLabel,
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
  w_ppr: 0,
  w_dual: 0,
}

const BEHAVIORAL_DEFAULTS: Record<string, boolean> = {
  hybrid_search_enabled: true,
  reranker_enabled: false,
  relation_rescue: true,
}

const GRAPH_DEFAULTS: Record<string, boolean> = {
  ppr_enabled: false,
  dual_level_enabled: false,
  community_injection_enabled: false,
}

const FUSION_ARM_META: Record<
  string,
  { alias?: string; desc: string; step: number }
> = {
  confidence_rank_gamma: {
    alias: "w_conf",
    desc: "1 + w·(confidence − 0.75) — scales a row's fused score by how far its content-quality estimate sits from the 0.75 default. Above 0 it multiplies rrf_score after fusion; after a rerank it rescales without reordering",
    step: 0.05,
  },
  w_importance: {
    desc: "1 + w·(importance − 0.5) — column populated, unread before this arm ships",
    step: 0.05,
  },
  w_heat: {
    desc: "1 + w·heat_norm, heat computed in SQL from memory_access_stats — a row read often ranks higher",
    step: 0.05,
  },
  w_recency: {
    desc: "1 + w·recency_norm, from last_accessed / created_at — a recently touched row ranks higher",
    step: 0.05,
  },
  // Absent until 2026-08-21, which made this arm's help tip render the literal
  // string "w_context_boost": `armFrom` falls back to the flag name when the
  // meta table has no entry, so a missing row here reads as a description.
  w_context_boost: {
    desc: "post-fusion multiplier on a MATCH outcome only — a NEUTRAL row carries a label with no boost, and a CONFLICT row is excluded and counted rather than down-weighted",
    step: 0.05,
  },
}

const BEHAVIORAL_META: Record<string, string> = {
  hybrid_search_enabled:
    "RRF fusion of semantic + keyword search, k=60 — the retrieval baseline the G-A gate already measured. Off, retrieval falls back to the semantic arm alone",
  reranker_enabled:
    "LLM-scores the top-40 RRF rows before serving — flips only on a measured win including its p95 cost (gate-ledger.md standing conditional gate)",
  relation_rescue:
    "pattern-based rescue layer for relations the extractor misses (adjacency, subject-tracking, REPLACES). The only surviving ingestion-side behavioral flag",
}

/** Doc 07 §4. Descriptions live here rather than on the wire for the reason
 *  `BEHAVIORAL_META` does — prose is a display concern. The *pairing* and the
 *  activation id do come from the backend's `GRAPH_CHANNELS`, because getting
 *  either wrong writes the wrong row with nothing looking wrong. */
const GRAPH_META: Record<string, string> = {
  ppr_enabled:
    "personalized PageRank list, seeded from the query's resolved entities and read from a cached in-process snapshot the ppr_snapshot job refreshes. Retrieval never computes it inline",
  dual_level_enabled:
    "global relation arm over relation_embeddings, scoped through the memories that assert each relation — a second ranked list, not a rescore of the first",
  community_injection_enabled:
    "injects a resolved community's report_string as local context. Context augmentation, so it adds no ranked list and takes no RRF weight",
}

const GRAPH_WEIGHT_META: Record<string, string> = {
  w_ppr: "RRF list weight — how heavily the PPR-ranked list counts in the fusion. A list weight, never a per-row multiplier",
  w_dual:
    "RRF list weight — how heavily the dual-level relation channel counts in the fusion. A list weight, never a per-row multiplier",
}

const TUNABLE_KEYS = [
  "pipeline_concurrency",
  "embedding_batch_size",
  "embedding_concurrency",
  "entity_cache_ttl_minutes",
] as const

/** The four numeric knobs the API has always served and no surface rendered.
 *  `min`/`max` mirror `FeatureFlagsUpdate`'s `Field(ge=, le=)` so the field
 *  refuses locally exactly what the API would 422 on. */
const TUNABLE_META: Record<
  (typeof TUNABLE_KEYS)[number],
  { desc: string; min: number; max: number; codedDefault: number; unit?: string }
> = {
  pipeline_concurrency: {
    desc: "how many memories Phase 2 extracts and classifies at once, and how wide Phase 4's dedup probes fan out. Raising it trades provider rate-limit headroom for batch latency",
    min: 1,
    max: 20,
    codedDefault: 5,
  },
  embedding_batch_size: {
    desc: "contents per chunk in Phase 1's single embedder call — larger batches cut round-trips, and overrun a model's context window",
    min: 1,
    max: 200,
    codedDefault: 20,
  },
  embedding_concurrency: {
    desc: "how many embed chunks are in flight at once against the embedding provider",
    min: 1,
    max: 10,
    codedDefault: 1,
  },
  entity_cache_ttl_minutes: {
    desc: "how long Phase 3 keeps an entity vector in the in-memory (name_lower, fingerprint) cache before falling back to the DB cache",
    min: 1,
    max: 1440,
    codedDefault: 60,
    unit: "minutes",
  },
}

/** `isSaving` keys for the writes that are not named after a single flag. */
export const SAVING_CLASSIFICATION_MODE = "classification_mode"
export const SAVING_CLASSIFICATION_AREAS = "classification_areas"
export const SAVING_ALLOWLIST = "repo_allowlist"

export interface FlagsTabBinding {
  fusionArms: DemoRankArm[]
  contextBoost: DemoRankArm
  behavioralFlags: DemoBehavioralFlag[]
  /** Live in both modes since 2026-08-21. The five doc 07 §4 flags have been in
   *  `FEATURE_FLAGS_DEFAULTS` since T2.32; what was missing was the response
   *  field, and this binding read that as "no config row exists". */
  graphAugmentationAvailable: boolean
  graphFlags: DemoGraphFlag[]
  /** Live in both modes since 2026-08-21, against `/config/verification-ladder`. */
  corroborationAvailable: boolean
  /** In flight, which is neither available nor unavailable — without this the
   *  unavailable box flashes on every first paint and reads as a failure. */
  corroborationLoading: boolean
  corroboration: DemoCorroborationGate
  tunables: DemoTunable[]
  classificationMode: "simple" | "expanded"
  classificationAreas: string[]
  availableAreas: ClassificationAreaInfo[]
  /** The label space the classifier actually works in, resolved by the
   *  backend rather than re-derived here. */
  classificationLabels: ClassificationLabel[]
  /** False in simple mode, where the area toggles change nothing. */
  classificationAreasApply: boolean
  /** Which writes are in flight, keyed by the thing being written — the
   *  flag name, the tunable name, the ladder parameter, or one of the
   *  sentinels below. One shared mutation object serves every control on the
   *  tab, so its own `isPending` would light up all of them at once. */
  isSaving: (key: string) => boolean
  allowlistPatterns: string[]
  overridesWritten: number
  isLoading: boolean
  saveArm: (key: string, value: number) => void
  setBehavioralFlag: (key: string, enabled: boolean) => void
  setGraphFlag: (key: string, enabled: boolean) => void
  /** Commit one ladder threshold; `null` clears it back to its floor. The
   *  response is the resolver's report, so a clamped save reports the clamp
   *  rather than echoing the number back. */
  saveCorroboration: (name: string, committed: number | null) => void
  saveTunable: (key: string, value: number) => void
  setClassificationMode: (mode: "simple" | "expanded") => void
  setClassificationAreas: (areas: string[]) => void
  saveAllowlist: (patterns: string[]) => void
}

function armFrom(
  flag: string,
  value: number,
  activation: string | null | undefined,
  measurable: string[],
  measured: string[],
  descOverride?: string,
): DemoRankArm {
  const meta = FUSION_ARM_META[flag]
  return {
    key: flag,
    alias: meta?.alias,
    desc: descOverride ?? meta?.desc ?? flag,
    value,
    coded_default: CODED_DEFAULTS[flag] ?? 0,
    source: value === (CODED_DEFAULTS[flag] ?? 0) ? "default" : "override",
    step: meta?.step ?? 0.05,
    activatesWith: activation ?? undefined,
    unmeasured: measurable.includes(flag) && !measured.includes(flag),
  }
}

/** Binds the Flags tab to `/config/feature-flags`, `/config/verification-ladder`,
 * `/config/classification-areas` and `/config/repo-allowlist` outside demo
 * mode; in demo mode it keeps the store fixture — the same gate
 * `useContributionCalendar` established for the dashboard calendar and
 * `useLLMTabBinding` established for the LLM tab. Every query hook runs
 * unconditionally (rules of hooks); only the network request is skipped via
 * `enabled`. */
export function useFlagsTabBinding(): FlagsTabBinding {
  const demoFlags = useDemoFlags()
  const saveDemoArm = useDemoStore((s) => s.saveArm)
  const setDemoGraphFlag = useDemoStore((s) => s.setGraphFlag)
  const saveDemoCorroboration = useDemoStore((s) => s.saveCorroboration)
  const setDemoBehavioralFlag = useDemoStore((s) => s.setBehavioralFlag)
  const saveDemoTunable = useDemoStore((s) => s.saveTunable)
  const setDemoClassificationMode = useDemoStore((s) => s.setClassificationMode)
  const setDemoClassificationAreas = useDemoStore(
    (s) => s.setClassificationAreas,
  )
  const saveDemoAllowlist = useDemoStore((s) => s.saveRepoAllowlist)

  // A list rather than a Set so two writes to the same key overlap correctly:
  // the second release removes one entry, not the key.
  const [inFlight, setInFlight] = useState<readonly string[]>([])
  const isSaving = useCallback(
    (key: string) => inFlight.includes(key),
    [inFlight],
  )
  const track = useCallback(
    (key: string, run: () => Promise<unknown>) => {
      setInFlight((keys) => [...keys, key])
      // The catch is required, not defensive: `mutateAsync` rejects on a failed
      // write and an unhandled rejection would take the page down over a
      // settings save. The error surface is the mutation's own; this only has
      // to stop the spinner.
      void run()
        .catch(() => {})
        .finally(() =>
          setInFlight((keys) => {
            const at = keys.indexOf(key)
            return at < 0 ? keys : [...keys.slice(0, at), ...keys.slice(at + 1)]
          }),
        )
    },
    [],
  )

  const flagsQuery = useFeatureFlags(!DEMO)
  const updateFlags = useUpdateFeatureFlags()
  const allowlistQuery = useRepoAllowlist(!DEMO)
  const updateAllowlist = useUpdateRepoAllowlist()
  const ladderQuery = useVerificationLadder(!DEMO)
  const updateLadder = useUpdateVerificationLadder()
  const areasQuery = useClassificationAreas()

  if (DEMO) {
    return {
      fusionArms: demoFlags.fusion_arms,
      contextBoost: demoFlags.context_boost,
      behavioralFlags: demoFlags.behavioral_flags,
      graphAugmentationAvailable: true,
      graphFlags: demoFlags.graph_flags,
      corroborationAvailable: true,
      corroborationLoading: false,
      corroboration: demoFlags.corroboration,
      tunables: demoFlags.tunables,
      classificationMode: demoFlags.classification_mode,
      classificationAreas: demoFlags.classification_areas,
      availableAreas: DEMO_AREAS,
      classificationLabels: DEMO_LABELS,
      classificationAreasApply: demoFlags.classification_mode !== "simple",
      // Demo writes are synchronous store updates; nothing is ever in flight,
      // and pretending otherwise would show a spinner that never resolves.
      isSaving: () => false,
      allowlistPatterns: demoFlags.repo_allowlist.patterns,
      overridesWritten: demoFlags.overrides_written,
      isLoading: false,
      saveArm: saveDemoArm,
      setBehavioralFlag: setDemoBehavioralFlag,
      setGraphFlag: setDemoGraphFlag,
      saveCorroboration: saveDemoCorroboration,
      saveTunable: saveDemoTunable,
      setClassificationMode: setDemoClassificationMode,
      setClassificationAreas: setDemoClassificationAreas,
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
    ? (
        [
          "confidence_rank_gamma",
          "w_importance",
          "w_heat",
          "w_recency",
        ] as const
      ).map((key) =>
        armFrom(key, flags[key], rankArmByFlag.get(key), measurable, measured),
      )
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

  // The channel list, its flag→weight pairing and its activation id all come
  // off `graph_channels`. Pairing `ppr_enabled` with `w_dual` here would write
  // the wrong row with nothing about the result looking wrong, which is why
  // this is read rather than re-typed.
  const graphFlags: DemoGraphFlag[] = (flags?.graph_channels ?? []).map(
    (channel) => ({
      key: channel.flag,
      desc: GRAPH_META[channel.flag] ?? channel.flag,
      enabled: channel.enabled,
      source:
        channel.enabled === (GRAPH_DEFAULTS[channel.flag] ?? false)
          ? "default"
          : "override",
      activatesWith: channel.activation ?? undefined,
      unmeasured:
        measurable.includes(channel.flag) && !measured.includes(channel.flag),
      paired_arm:
        channel.weight_flag === null
          ? null
          : armFrom(
              channel.weight_flag,
              channel.weight ?? 0,
              // A list weight is not a `RankArm`, so it carries no activation
              // of its own — the channel's is the one that governs both.
              undefined,
              measurable,
              measured,
              GRAPH_WEIGHT_META[channel.weight_flag],
            ),
      no_weight_note:
        channel.weight_flag === null
          ? "context augmentation, not a ranking signal — no paired RRF weight"
          : undefined,
    }),
  )

  const tunables: DemoTunable[] = flags
    ? TUNABLE_KEYS.map((key) => {
        const meta = TUNABLE_META[key]
        return {
          key,
          desc: meta.desc,
          value: flags[key],
          coded_default: meta.codedDefault,
          source: flags[key] === meta.codedDefault ? "default" : "override",
          min: meta.min,
          max: meta.max,
          unit: meta.unit,
        }
      })
    : []

  const corroboration: DemoCorroborationGate = {
    params: (ladderQuery.data?.params ?? []).map(
      (p): DemoLadderParam => ({
        name: p.name,
        committed: p.committed,
        effective: p.effective,
        floor: p.floor,
        measured: p.measured,
        state: p.state,
        note: p.note ?? undefined,
      }),
    ),
    measured: ladderQuery.data?.measured ?? [],
    rowPresent: ladderQuery.data?.row_present ?? false,
    measurementTask: ladderQuery.data?.measurement_task ?? "T2.40",
    gate_note: LADDER_GATE_NOTE,
  }

  const overridesWritten =
    fusionArms.filter((a) => a.source === "override").length +
    (contextBoost.source === "override" ? 1 : 0) +
    behavioralFlags.filter((f) => f.source === "override").length +
    graphFlags.filter((f) => f.source === "override").length +
    graphFlags.filter((f) => f.paired_arm?.source === "override").length +
    tunables.filter((t) => t.source === "override").length +
    corroboration.params.filter((p) => p.committed !== null).length

  return {
    fusionArms,
    contextBoost,
    behavioralFlags,
    graphAugmentationAvailable: Boolean(flags),
    graphFlags,
    corroborationAvailable: Boolean(ladderQuery.data),
    corroborationLoading: ladderQuery.isLoading,
    corroboration,
    tunables,
    classificationMode: flags?.classification_mode ?? "simple",
    classificationAreas: flags?.classification_areas ?? [],
    availableAreas: areasQuery.data ?? [],
    classificationLabels: flags?.classification_labels ?? [],
    classificationAreasApply: flags?.classification_areas_apply ?? false,
    isSaving,
    allowlistPatterns: allowlistQuery.data?.patterns ?? [],
    overridesWritten,
    isLoading: flagsQuery.isLoading,
    saveArm: (key, value) => {
      track(key, () => updateFlags.mutateAsync({ [key]: value }))
    },
    setBehavioralFlag: (key, enabled) => {
      track(key, () => updateFlags.mutateAsync({ [key]: enabled }))
    },
    setGraphFlag: (key, enabled) => {
      track(key, () => updateFlags.mutateAsync({ [key]: enabled }))
    },
    saveCorroboration: (name, committed) => {
      track(name, () => updateLadder.mutateAsync({ [name]: committed }))
    },
    saveTunable: (key, value) => {
      track(key, () => updateFlags.mutateAsync({ [key]: value }))
    },
    setClassificationMode: (mode) => {
      track(SAVING_CLASSIFICATION_MODE, () =>
        updateFlags.mutateAsync({ classification_mode: mode }),
      )
    },
    setClassificationAreas: (areas) => {
      track(SAVING_CLASSIFICATION_AREAS, () =>
        updateFlags.mutateAsync({ classification_areas: areas }),
      )
    },
    saveAllowlist: (patterns) => {
      track(SAVING_ALLOWLIST, () => updateAllowlist.mutateAsync(patterns))
    },
  }
}

/** Doc 08 §4.1's rule, spelled out once for the gate's section help. */
export const LADDER_GATE_NOTE =
  "N drops from 3 to 2 when two attributable origins differ in source-kind " +
  "(memory + code beats three memories) or lie at least 7 days apart. " +
  "Corroboration counts DISTINCT origin_key over fact_sources, never rows; " +
  "anonymous origins fold into one reserved bucket that counts once and fires " +
  "no gate, and a citation the re-verifier marked stale corroborates nothing."

/** The demo instance's simple-mode label space.
 *
 *  Names come from the one shared vocabulary source rather than being spelled
 *  out here: a per-component copy is exactly what
 *  `test_no_frontend_component_keeps_its_own_memory_type_list` fails the build
 *  on, and it goes stale the first time a type is added. Real mode serves each
 *  description from the backend's own `SIMPLE_TYPES`; demo mode has no backend
 *  to ask, so it says that rather than inventing prose that would then be a
 *  second place the descriptions live. */
const DEMO_LABELS: ClassificationLabel[] = MEMORY_TYPES.map((name) => ({
  name,
  description:
    "A simple-mode label. On a live instance its description is served from " +
    "the backend's own vocabulary — demo mode has no backend to read it from.",
}))

/** The demo instance's classification areas. Real mode reads the live set from
 *  `/config/classification-areas`, which is the authority — this fixture only
 *  has to render, not to be complete. */
const DEMO_AREAS: ClassificationAreaInfo[] = [
  {
    key: "general",
    display_name: "General",
    // The simple-7 vocabulary, read from the one shared source. Spelling the
    // list out here re-declares it, which `test_no_frontend_component_keeps_
    // its_own_memory_type_list` fails the build on — a per-component copy
    // silently hides rows of a type added later.
    types: [...MEMORY_TYPES],
    type_descriptions: {},
  },
  {
    key: "technical",
    display_name: "Technical",
    types: ["reference", "architecture"],
    type_descriptions: {},
  },
  {
    key: "debugging",
    display_name: "Debugging",
    types: ["root_cause", "workaround", "gotcha"],
    type_descriptions: {},
  },
  {
    key: "infrastructure",
    display_name: "Infrastructure",
    types: ["deployment", "configuration", "networking"],
    type_descriptions: {},
  },
]
