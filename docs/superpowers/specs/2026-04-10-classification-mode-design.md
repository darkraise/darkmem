# Classification Mode: Simple vs Expanded

**Date:** 2026-04-10
**Status:** Draft

## Problem

With all 11 classification areas enabled, the LLM classifier presents 35 types to the model. Small models (qwen2.5:3b) struggle with this many options and invent plausible-but-invalid types like "solution", "fix", and "recommendation", which fall back to "fact" and lose semantic value.

## Solution

Add a `classification_mode` feature flag that toggles between two modes:

- **Simple** (default): 7 universal types with a normalization map that catches common LLM drift. Area selection is ignored.
- **Expanded**: Current behavior — types are merged from enabled classification areas.

## Simple Mode Types

| Type | Description |
|------|-------------|
| fact | Neutral factual information, how things work, definitions, specifications |
| decision | Explicit choices made, architecture rationale, trade-offs with reasoning |
| preference | Habits, rules, style preferences, always/never statements |
| problem | Bugs, errors, root causes, workarounds, gotchas, debugging insights |
| reference | Documentation pointers, specs, standards, protocol descriptions |
| architecture | System design, component responsibilities, patterns, data flow |
| milestone | Breakthroughs, achievements, releases, things that finally worked |

## Normalization Map (Simple Mode Only)

When the LLM returns a type not in the simple list, the normalization map remaps it before falling back to "fact":

| LLM Output | Mapped To |
|-------------|-----------|
| solution, fix, workaround, root_cause, gotcha, debug, incident, vulnerability | problem |
| recommendation, comparison, agreement, disagreement, feedback | decision |
| finding, configuration, networking, compliance, status_update, hypothesis | fact |
| tutorial, concept, requirement, feature_spec, user_story | reference |
| deployment, planning | architecture |
| lesson_learned, retrospective, journal, reflection, goal | milestone |
| emotional | preference |

## Backend Changes

### config.py

Add to `FEATURE_FLAGS_DEFAULTS`:

```python
"classification_mode": "simple"
```

### classification_areas.py

Add module-level constants:

```python
SIMPLE_TYPES: dict[str, str]          # 7-type map with descriptions
SIMPLE_NORMALIZATION: dict[str, str]  # remap table
```

Update `get_merged_llm_types(enabled_areas, mode="expanded")`:
- When `mode="simple"`, return `SIMPLE_TYPES` directly, ignoring `enabled_areas`.
- When `mode="expanded"`, behave as today.

Update `get_merged_markers(enabled_areas, mode="expanded")`:
- When `mode="simple"`, collect markers from all enabled areas, then remap type keys through `SIMPLE_NORMALIZATION`. When multiple source types map to the same simple type (e.g., `root_cause` and `problem` both map to `problem`), their marker lists are concatenated. Types that don't exist in either `SIMPLE_TYPES` or `SIMPLE_NORMALIZATION` are dropped.
- When `mode="expanded"`, behave as today.

### classification_llm.py

`ClassificationService.classify()` gains a `mode` parameter.

After extracting `classified_type` from LLM response:

```python
if mode == "simple" and classified_type not in valid_names:
    classified_type = SIMPLE_NORMALIZATION.get(classified_type, classified_type)
if classified_type not in valid_names:
    classified_type = "fact"
```

### memory_classifier.py

`classify()` and `extract_memories()` gain a `mode` parameter, passed to `get_merged_markers()`.

### pipeline.py

Read `classification_mode` from feature flags alongside `classification_areas`. Pass `mode` to:
- `self.classification.classify(content, areas, cls_prompt, mode=mode)`
- `regex_classify(content, enabled_areas=areas, mode=mode)`

### routes/config.py

Add `classification_mode: str` to `FeatureFlagsResponse` and `FeatureFlagsUpdate`.

Add validation in `update_feature_flags`:

```python
if "classification_mode" in updates:
    if updates["classification_mode"] not in ("simple", "expanded"):
        raise HTTPException(status_code=422, detail="classification_mode must be 'simple' or 'expanded'")
```

## Frontend Changes

### use-config-api.ts

Add `classification_mode: string` to the feature flags TypeScript type.

### settings.tsx

Rework `ClassificationAreasCard`:

**Top of card:** Two-segment toggle control (Simple | Expanded) that calls `updateFlags.mutate({ classification_mode: value })`.

**Simple mode body:** Read-only list of the 7 simple types with their descriptions. Not interactive, purely informational.

**Expanded mode body:** Table layout with clear row dividers. Each row contains:
- Area name (bold, left-aligned)
- Comma-separated type names (muted text, middle)
- Toggle switch (right-aligned)

General area row has its switch disabled (always on). Switching modes preserves the area selection in the backend.

## Files Changed

| File | Change |
|------|--------|
| `backend/app/config.py` | Add `classification_mode` to `FEATURE_FLAGS_DEFAULTS` |
| `backend/app/services/classification_areas.py` | Add `SIMPLE_TYPES`, `SIMPLE_NORMALIZATION`, update `get_merged_llm_types()` and `get_merged_markers()` |
| `backend/app/services/classification_llm.py` | Add `mode` param, apply normalization |
| `backend/app/services/memory_classifier.py` | Add `mode` param, pass to `get_merged_markers()` |
| `backend/app/services/pipeline.py` | Read and pass `classification_mode` |
| `backend/app/api/routes/config.py` | Update schemas and validation |
| `frontend/src/hooks/api/use-config-api.ts` | Update types |
| `frontend/src/routes/_authenticated/settings.tsx` | Mode toggle, conditional card body |
