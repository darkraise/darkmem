import { useCallback, useState } from "react"
import { toast } from "darkraise-ui/components/sonner"
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
  type FeatureFlags,
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

const FUSION_ARM_META: Record<string, { desc: string; step: number }> = {
  confidence_rank_gamma: {
    desc: "Ranks results with a higher confidence estimate above the rest",
    step: 0.05,
  },
  w_importance: {
    desc: "Ranks more important memories higher",
    step: 0.05,
  },
  w_heat: {
    desc: "Ranks frequently read memories higher",
    step: 0.05,
  },
  w_recency: {
    desc: "Ranks recently used or created memories higher",
    step: 0.05,
  },
  // Absent until 2026-08-21, which made this arm's help tip render the literal
  // string "w_context_boost": `armFrom` falls back to the flag name when the
  // meta table has no entry, so a missing row here reads as a description.
  w_context_boost: {
    desc: "Boosts results whose context conditions match the query; results whose conditions conflict are left out",
    step: 0.05,
  },
}

const BEHAVIORAL_META: Record<string, string> = {
  hybrid_search_enabled:
    "Combines semantic and keyword search. Off, search uses semantic matching only",
  reranker_enabled:
    "Has an LLM re-score the top 40 results before they are returned. Adds latency and cost",
  relation_rescue:
    "Recovers relations the extractor missed, using text patterns",
}

/** Descriptions live here rather than on the wire for the reason
 *  `BEHAVIORAL_META` does — prose is a display concern. The *pairing* does
 *  come from the backend's `GRAPH_CHANNELS`, because getting it wrong writes
 *  the wrong row with nothing looking wrong. */
const GRAPH_META: Record<string, string> = {
  ppr_enabled:
    "Adds results ranked by how close they are in the entity graph to the entities in the query",
  dual_level_enabled:
    "Adds results found by searching the relations between entities",
  community_injection_enabled:
    "Adds a summary of the matching entity group as context. It adds no ranked list, so it has no weight",
}

const GRAPH_WEIGHT_META: Record<string, string> = {
  w_ppr: "How much the graph-proximity results count in the ranking",
  w_dual: "How much the relation-search results count in the ranking",
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
    desc: "How many memories are processed at once. Higher is faster but uses more of the provider's rate limit",
    min: 1,
    max: 20,
    codedDefault: 5,
  },
  embedding_batch_size: {
    desc: "How many texts are sent per embedding request. Larger batches mean fewer requests but can exceed the model's context window",
    min: 1,
    max: 200,
    codedDefault: 20,
  },
  embedding_concurrency: {
    desc: "How many embedding requests run at once",
    min: 1,
    max: 10,
    codedDefault: 1,
  },
  entity_cache_ttl_minutes: {
    desc: "How long entity embeddings stay in the in-memory cache",
    min: 1,
    max: 1440,
    codedDefault: 60,
    unit: "minutes",
  },
}

/** The tab's sections. A save is per section now, not per control: the whole
 *  card's edits go out as one request, so `isSaving` is keyed on the section
 *  and the "edited" list in a dialog footer names everything that one call
 *  will write. */
export const SECTIONS = {
  arms: "arms",
  flags: "flags",
  contextBoost: "context_boost",
  graph: "graph",
  tunables: "tunables",
  classification: "classification",
  allowlist: "repo_allowlist",
  ladder: "ladder",
} as const

export type SectionKey = (typeof SECTIONS)[keyof typeof SECTIONS]

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
  isLoading: boolean
  /** One `feature_flags` write for a whole section's edits. Every control on
   *  this tab that lives in that row goes through here, so a card with six
   *  changed fields costs one request rather than six. */
  saveFlags: (section: SectionKey, patch: Record<string, unknown>) => void
  /** One `verification_ladder` write. `null` clears a threshold back to its
   *  floor. The response is the resolver's report, so a clamped save reports
   *  the clamp rather than echoing the number back. */
  saveLadder: (patch: Record<string, number | null>) => void
  saveAllowlist: (patterns: string[]) => void
}

function armFrom(flag: string, value: number, descOverride?: string): DemoRankArm {
  const meta = FUSION_ARM_META[flag]
  return {
    key: flag,
    desc: descOverride ?? meta?.desc ?? flag,
    value,
    coded_default: CODED_DEFAULTS[flag] ?? 0,
    source: value === (CODED_DEFAULTS[flag] ?? 0) ? "default" : "override",
    step: meta?.step ?? 0.05,
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
      // settings save. It also has to say so: the section dialogs close on
      // Save, and nothing else rendered a refusal, so an out-of-range value
      // (the server's 422) vanished and the old value stayed without a word.
      void run()
        .catch((error: unknown) => {
          toast.error(
            `Not saved: ${error instanceof Error ? error.message : String(error)}`,
          )
        })
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
      isLoading: false,
      // Demo mode has no request to batch, so one section save fans back out
      // to the store actions the fixture already had. The *caller's* shape is
      // what matters — one save per section — and it is the same in both
      // modes.
      saveFlags: (_section, patch) => {
        for (const [key, value] of Object.entries(patch)) {
          if (key === "classification_mode") {
            setDemoClassificationMode(value as "simple" | "expanded")
          } else if (key === "classification_areas") {
            setDemoClassificationAreas(value as string[])
          } else if (typeof value === "boolean") {
            if (key in GRAPH_DEFAULTS) setDemoGraphFlag(key, value)
            else setDemoBehavioralFlag(key, value)
          } else if (typeof value === "number") {
            if (TUNABLE_KEYS.includes(key as (typeof TUNABLE_KEYS)[number])) {
              saveDemoTunable(key, value)
            } else {
              saveDemoArm(key, value)
            }
          }
        }
      },
      saveLadder: (patch) => {
        for (const [name, committed] of Object.entries(patch)) {
          saveDemoCorroboration(name, committed)
        }
      },
      saveAllowlist: saveDemoAllowlist,
    }
  }

  const flags = flagsQuery.data

  const fusionArms: DemoRankArm[] = flags
    ? (
        [
          "confidence_rank_gamma",
          "w_importance",
          "w_heat",
          "w_recency",
        ] as const
      ).map((key) => armFrom(key, flags[key]))
    : []

  const contextBoost: DemoRankArm = flags
    ? armFrom("w_context_boost", flags.w_context_boost)
    : armFrom("w_context_boost", 0)

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
      }))
    : []

  // The channel list and its flag→weight pairing come off `graph_channels`.
  // Pairing `ppr_enabled` with `w_dual` here would write the wrong row with
  // nothing about the result looking wrong, which is why this is read rather
  // than re-typed.
  const graphFlags: DemoGraphFlag[] = (flags?.graph_channels ?? []).map(
    (channel) => ({
      key: channel.flag,
      desc: GRAPH_META[channel.flag] ?? channel.flag,
      enabled: channel.enabled,
      source:
        channel.enabled === (GRAPH_DEFAULTS[channel.flag] ?? false)
          ? "default"
          : "override",
      paired_arm:
        channel.weight_flag === null
          ? null
          : armFrom(
              channel.weight_flag,
              channel.weight ?? 0,
              GRAPH_WEIGHT_META[channel.weight_flag],
            ),
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
  }

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
    isLoading: flagsQuery.isLoading,
    saveFlags: (section, patch) => {
      // `FeatureFlagsUpdate` is a partial schema, so a many-key body is one
      // valid request. Sending them one at a time was never required by the
      // API — it was the UI's own habit, and it cost a round-trip and a cache
      // reconcile per keystroke-commit.
      track(section, () =>
        updateFlags.mutateAsync(patch as Partial<FeatureFlags>),
      )
    },
    saveLadder: (patch) => {
      track(SECTIONS.ladder, () => updateLadder.mutateAsync(patch))
    },
    saveAllowlist: (patterns) => {
      track(SECTIONS.allowlist, () => updateAllowlist.mutateAsync(patterns))
    },
  }
}

/** The demo instance's simple-mode label space.
 *
 *  Names come from the one shared vocabulary source rather than being spelled
 *  out here: a per-component copy is exactly what
 *  `test_no_frontend_component_keeps_its_own_memory_type_list` fails the build
 *  on, and it goes stale the first time a type is added. Real mode serves each
 *  description from the backend's own `SIMPLE_TYPES`; demo mode has no backend
 *  to ask, so it serves none rather than inventing prose that would then be a
 *  second place the descriptions live. */
const DEMO_LABELS: ClassificationLabel[] = MEMORY_TYPES.map((name) => ({
  name,
  description: "",
  // Simple mode credits no area, because none is responsible for the fixed
  // vocabulary.
  area: null,
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
