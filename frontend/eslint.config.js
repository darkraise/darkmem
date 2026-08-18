import js from "@eslint/js"
import globals from "globals"
import tseslint from "typescript-eslint"
import reactHooks from "eslint-plugin-react-hooks"
import reactRefresh from "eslint-plugin-react-refresh"
import prettier from "eslint-config-prettier"
import { builtinRules } from "eslint/use-at-your-own-risk"

export default tseslint.config(
  { ignores: ["dist", "src/routeTree.gen.ts"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
  prettier,
  {
    // Downgraded error -> warn by T1.58 (retire demo mode as the default).
    // T1.64 corrected the count this comment carries and retargeted the
    // achievable `error` flip to a narrower rule below, rather than flipping
    // this whole block: measured 2026-07-28, by demo submodule (files
    // overlap, since one file may import more than one) —
    // `@/demo/types` 65, `@/demo/hooks` 30, `@/demo/store` 22, `@/demo/data`
    // 0 (fixed in-lane by T1.64, see the `data/**`-scoped rule below),
    // `@/demo/flag` 0 (relocated to `@/lib/demo-flag`, T1.64).
    //
    // T1.67 re-verified the `@/demo/types` premise T1.64 recorded above —
    // "the dominant debt: real API types re-exported through a demo path" —
    // against the actual import statements, not the file's top two lines,
    // and it does not hold: zero of the 65 importers name `Memory`,
    // `MemoryStatus`, `Repo`, or `Job`; every one imports a `Demo`-prefixed
    // or locally-defined type (`DemoMemory`, `MemoryTrace`, `FactSource`,
    // `DemoCodeGraph`, ...) that happens to live in the same file. Moving
    // those 65 importers' actual dependencies out of `src/demo` is a much
    // larger, judgment-heavy type-relocation (some, like `DemoCodeGraph` /
    // `DemoCodeNode`, are shared by genuinely-real components
    // (`real-code-inspector.tsx`, `real-code-graph-view.tsx`) and would need
    // a real home decided per type, not a mechanical repoint) and stays
    // out of this task's scope — a named, not silently absorbed, residual.
    // T1.67's own fix is below: the literal re-export of the four real API
    // types is gone from `src/demo/types.ts`, and the `importNames`-scoped
    // block further down makes reintroducing it (from any file, not just
    // the ones measured today) an `error`, not just a `warn`. This block's
    // own measured violation count is asserted by
    // `src/__tests__/no-restricted-imports-count.test.ts` (not under
    // `tests/`, which vitest.config.ts excludes), literal, not parsed from
    // this comment.
    files: [
      "src/routes/**/*.tsx",
      "src/features/**/*.{ts,tsx}",
      "src/hooks/**/*.ts",
      "src/lib/**/*.ts",
      "src/components/**/*.{ts,tsx}",
    ],
    rules: {
      "no-restricted-imports": [
        "warn",
        {
          patterns: [
            { group: ["@/demo/*", "../demo/*", "../../demo/*"], message: "Production code may not import from src/demo/ — that path is for Storybook and demo-mode Playwright specs only." },
          ],
        },
      ],
    },
  },
  {
    // T1.64: the one sub-target of src/demo/* that is genuinely achievable
    // as a real `error` today — raw fixture literals, the narrowest,
    // most mechanical bucket (measured 0 importers after this task's
    // in-lane fixes, down from 5: three production files and two demo-mode
    // test files now reach the same constants through
    // `src/demo/data-exports.ts`, a plain re-export outside `src/demo/data/`,
    // instead of the fixture files directly). A new violator here fails the
    // build, not just a test — see the flip's own falsification test.
    //
    // Registered under an aliased rule name, not `no-restricted-imports`
    // directly: ESLint flat config does not merge two config objects' entries
    // for the same rule name on overlapping `files` globs, it replaces the
    // earlier one outright — a second `no-restricted-imports` block here
    // would silently kill the warn-level rule above for every file both
    // blocks match, not narrow it. Aliasing the same builtin rule under a
    // second name lets both severities coexist on the same file set.
    files: [
      "src/routes/**/*.tsx",
      "src/features/**/*.{ts,tsx}",
      "src/hooks/**/*.ts",
      "src/lib/**/*.ts",
      "src/components/**/*.{ts,tsx}",
    ],
    plugins: {
      "demo-data-import": {
        rules: { "no-restricted-imports": builtinRules.get("no-restricted-imports") },
      },
    },
    rules: {
      "demo-data-import/no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: ["@/demo/data/*", "../demo/data/*", "../../demo/data/*"], message: "Production and test code may not import fixture literals from src/demo/data/ directly — re-export the specific value through src/demo/data-exports.ts (or another indirection outside src/demo/data/) instead." },
          ],
        },
      ],
    },
  },
  {
    // T1.67: the real API types (`Memory`, `MemoryStatus`, `Repo`, `Job`)
    // no longer have any re-export in `src/demo/types.ts` to import — this
    // is the falsifiable guard against reintroducing one. Scoped by
    // `importNames`, not the whole `@/demo/types` path: the broader warn
    // rule above already covers every other name that path exports, and a
    // second plain `no-restricted-imports` path-level block here would
    // replace it outright rather than narrow it (same flat-config gotcha
    // T1.64 hit — see the `demo-data-import` alias above), so this reuses
    // that pattern under its own alias.
    files: [
      "src/routes/**/*.tsx",
      "src/features/**/*.{ts,tsx}",
      "src/hooks/**/*.ts",
      "src/lib/**/*.ts",
      "src/components/**/*.{ts,tsx}",
    ],
    plugins: {
      "demo-realtype-import": {
        rules: { "no-restricted-imports": builtinRules.get("no-restricted-imports") },
      },
    },
    rules: {
      "demo-realtype-import/no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/demo/types", "../demo/types", "../../demo/types", "../../../demo/types"],
              importNames: ["Memory", "MemoryStatus", "Repo", "Job"],
              message: "Import the real API types from @/hooks/api, not through src/demo/types — that re-export was removed in T1.67.",
            },
          ],
        },
      ],
    },
  },
  {
    // T1.68: the 33 names below no longer live in src/demo/types.ts at
    // all — they moved to features/{dashboard,code,memories,activity,
    // settings}/types.ts because real (non-demo-exclusive) code is
    // genuinely load-bearing on them (graph-derive.ts's DemoCodeGraph
    // derivation, use-job-board.ts's fromJob, memory-editor-dialog.tsx's
    // DemoMemory union, ...). This is the falsifiable guard against
    // reintroducing any of them on a demo path, same shape as the
    // `demo-realtype-import` alias above (a plain path-level
    // `no-restricted-imports` block here would replace the broader warn
    // rule instead of narrowing it — the flat-config gotcha T1.64 hit).
    files: [
      "src/routes/**/*.tsx",
      "src/features/**/*.{ts,tsx}",
      "src/hooks/**/*.ts",
      "src/lib/**/*.ts",
      "src/components/**/*.{ts,tsx}",
    ],
    plugins: {
      "demo-relocated-types-import": {
        rules: { "no-restricted-imports": builtinRules.get("no-restricted-imports") },
      },
    },
    rules: {
      "demo-relocated-types-import/no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/demo/types", "../demo/types", "../../demo/types", "../../../demo/types"],
              importNames: [
                "DashboardStats",
                "ActivityEventKind",
                "ActivityEvent",
                "ContributionTypeCount",
                "ContributionDay",
                "CodeNodeKind",
                "DemoCodeNode",
                "DemoCodeEdge",
                "DemoCodeCommunity",
                "DemoCodeProcess",
                "DemoCodeGraph",
                "MemoryRelationType",
                "MemoryRelation",
                "MemoryTimelineEventKind",
                "MemoryTimelineEvent",
                "DemoMemory",
                "DemoJobField",
                "DemoJob",
                "JobTriggerResult",
                "FeedCategory",
                "PipelineStepState",
                "PipelineWriteSubsteps",
                "PipelineTerminal",
                "DemoPipelineRun",
                "DemoPipelineFailure",
                "FlagSource",
                "DemoRankArm",
                "DemoBehavioralFlag",
                "DemoGraphFlag",
                "DemoCorroborationGate",
                "ApiKind",
                "LLMPurposeName",
                "DemoLLMPurpose",
                "DemoCodeBucket",
                "DemoLLMSaveTrace",
                "MaintenanceOpKey",
              ],
              message: "This type moved out of src/demo/types.ts in T1.68 — import it from its real feature module (features/{dashboard,code,memories,activity,settings}/types.ts) instead.",
            },
          ],
        },
      ],
    },
  },
)
