import hashlib
import json
import logging
import re
from collections.abc import Collection
from typing import NamedTuple

from app.services.extraction_pass_harness import (
    CleanState,
    OrderingConstraint,
    Pass,
    RunsBefore,
    StraddlesPivot,
    run_passes,
    validate_registry,
)
from app.taxonomy import (
    ENTITY_TYPES,
    MEMORY_TYPES,
    RELATIONSHIP_TYPES,
    normalize_entity_type,
    normalize_relation_type,
    refine_entity_type,
)
from app.services.relations import REPLACES_FAMILY, family_key as _family_key

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 6000


def _content_seed(content: str) -> int:
    """Derive a deterministic 32-bit seed from the content.

    Used to pin the LLM's RNG seed so the same input produces the same
    extraction output across calls. Truncating SHA-256 to 8 hex chars
    yields a value in [0, 2^32) which every vendor honouring the
    ``seed`` parameter (OpenAI, DeepSeek, z.ai, Google compat, Ollama)
    accepts. Anthropic ignores the param entirely; a stale seed there
    is harmless.
    """
    return int(hashlib.sha256(content.encode("utf-8")).hexdigest()[:8], 16)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _strip_json_fences(text: str) -> str:
    """Return the first fenced ```json ... ``` (or bare ```) block, if any.

    Reasoning-by-default vendors (and Anthropic's compat shim, which can't take
    ``response_format=json_object``) often wrap the JSON in a markdown fence —
    and frequently prepend chain-of-thought prose, so the fence is NOT at
    position 0. Search for the first fenced block anywhere rather than requiring
    it to wrap the whole response. No-op for responses that aren't fenced, so
    safe to apply unconditionally.
    """
    s = text.strip()
    m = _FENCE_RE.search(s)
    if m:
        return m.group(1).strip()
    return s


def _salvage_json_object(text: str) -> str | None:
    """Return the first balanced ``{...}`` object substring, or None.

    Recovers a JSON body buried in prose ("Sure, here you go: {...}") by scanning
    from the first ``{`` and tracking brace depth while respecting string and
    escape state, so braces inside string values don't unbalance the count.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _loads_extraction(response: str) -> dict:
    """Parse an extraction response, tolerating fenced or prose-wrapped JSON.

    Tries the fence-aware path first, then falls back to a brace-balanced
    salvage. Raises ``json.JSONDecodeError`` only when neither yields valid JSON.
    """
    try:
        return json.loads(_strip_json_fences(response))
    except json.JSONDecodeError:
        salvaged = _salvage_json_object(response)
        if salvaged is None:
            raise
        return json.loads(salvaged)


def _build_extraction_schema(with_classification: bool = False) -> str:
    entity_types = "|".join(ENTITY_TYPES)
    rel_types = "|".join(RELATIONSHIP_TYPES)
    memory_types = "|".join(MEMORY_TYPES)
    # When merged with classification, the same call also returns the
    # enrichment fields the standalone classifier would. ``memory_type`` already
    # carries the type label (the MEMORY_TYPES vocabulary), so no separate type
    # field is needed — only summary/emotions/flags ride along.
    classification_fields = (
        ',\n'
        '  "summary": "one-line summary of the key insight",\n'
        '  "emotions": [],\n'
        '  "flags": []'
    ) if with_classification else ""
    return (
        "{\n"
        f'  "entities": [{{"name": "string", "type": "{entity_types}", "properties": {{}}}}],\n'
        f'  "relationships": [{{"source": "entity_name", "target": "entity_name", "type": "{rel_types}", "properties": {{}}, "weight": 0.8}}],\n'
        f'  "memory_type": "{memory_types}",\n'
        f'  "importance": 0.7{classification_fields}\n'
        "}"
    )


# ── Composable cleanup steps (non-mutating) ─────────────────────────

_NOISE_NAMES: frozenset[str] = frozenset({
    "run", "main", "start", "stop", "get", "set", "put", "post", "delete",
    "token", "value", "key", "type", "name", "data", "result", "status",
    "format", "parameter", "resolution", "function", "method", "class",
    "module", "file", "path", "index", "list", "map", "string", "number",
    "true", "false", "none", "null", "error", "success", "failure",
    "symbol", "codebase", "framework",
    # Generic nouns that survive trailing-suffix stripping ("auth service" ->
    # "auth", "filesystem", "process_batch") and bare directory parts.
    "auth", "filesystem", "process_batch", "config",
    "request", "response", "session", "context", "scope",
    # 'kafka source connector' loses its descriptor suffix and leaves the bare
    # stem behind; the stem is a generic noun either way.
    "source",
    # Host stem left behind when the dotted-name collapse eats a bare
    # hostname ('www.example.com' -> 'www').
    "www",
})

_TRAILING_SUFFIXES = re.compile(
    r"\s+(function|method|table|column|operator|class|module|object|instance"
    r"|variable|field|property|endpoint|route|service|system|framework|library"
    r"|tool|api|sdk|server|broker|backend|frontend|interface|adapter|wrapper"
    r"|driver|plugin|extension|stack|cluster|proxy|store|engine|runtime)$",
    re.IGNORECASE,
)

# Trailing dotted method or attribute access (asyncio.create_task -> asyncio,
# os.path.join -> os). We only strip when the part before the first dot is a
# valid identifier; this avoids hurting legitimate names like ``v1.0`` (those
# are also caught by ``_VALUE_PATTERN``).
_DOTTED_METHOD = re.compile(r"^([A-Za-z_][\w-]*)\.[A-Za-z_][\w_.]*$")

# File path / filename: matches both ``foo.py`` and ``app/services/foo.py``.
_FILENAME_PATTERN = re.compile(
    r"^[\w./\\-]+\.(py|js|ts|tsx|jsx|go|rs|java|cpp|c|h|rb|php|yaml|yml|json"
    r"|toml|md|txt|sql|sh|env|cfg|ini)$",
    re.IGNORECASE,
)

# URL paths starting with a slash.
_URL_PATH_PATTERN = re.compile(r"^/[\w/\.\-_]*(?:\?[\w&=\.\-]*)?$")

# Absolute URLs. Matched on the scheme prefix rather than the whole string so a
# query string or fragment cannot smuggle one past. Without this the chain drops
# them only by accident, when ``_filter_hallucinated_names`` happens to find a
# dot-stripped token absent from the source; a dotless authority
# (``http://localhost:8000/api``) survives that check and reaches the graph.
_URL_ABSOLUTE_PATTERN = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)

# Environment variable names: all-caps with at least one underscore and 4+ chars.
_ENV_VAR_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*_[A-Z0-9_]+$")

# Bare values that should never be entities. Dates, versions, sizes, durations,
# counts, percentages — these belong inside an entity's properties, not as
# nodes in the graph.
_VALUE_PATTERN = re.compile(
    r"""^(?:
        \d{4}[-/]\d{1,2}[-/]\d{1,2}        # 2026-04-23, 2026/4/23
      | \d{4}[-/]\d{1,2}                   # 2026-04, 2026/4 (year-month)
      | \d{4}                              # bare 4-digit year (2026)
      | \d{1,2}[-/]\d{1,2}[-/]\d{2,4}      # 23/04/2026
      | v?\d+\.\d+(?:\.\d+)?(?:-[\w.-]+)?  # v2.0, 1.2.3, 2.0.0-beta
      | \d+\s*(?:ms|s|m|h|d)\b             # 30s, 5m, 24h
      | \d+\s*(?:KB|MB|GB|TB|PB)\b         # 512MB, 2GB
      | \d+%                               # 30%
      | \d+(?:,\d{3})*(?:\.\d+)?           # bare numbers including 1,000.5
    )$""",
    re.IGNORECASE | re.VERBOSE,
)

# Hardware tokens (and GPU runtimes) the LLM occasionally mislabels into
# the wrong bucket. When we recognise one, snap to ``tool`` regardless of
# the model's guess — none of these belong in ``entity``, ``artifact``,
# or ``service``.
_HARDWARE_TOKENS: frozenset[str] = frozenset({
    "cpu", "gpu", "tpu", "fpga", "asic", "ram", "vram",
    "ssd", "hdd", "nvme", "disk",
    "cuda", "rocm", "vulkan", "opencl", "metal", "mps",
})

# Known-short tools that are normally <3 chars and would fail the length
# guard in ``_normalize_names``. Allowlisted so we keep them as entities.
_SHORT_TOOL_ALLOWLIST: frozenset[str] = frozenset({
    "rg", "fd", "ls", "ps", "vi", "vim", "tar", "git", "ssh", "scp", "sed",
    "awk", "jq", "yq", "wc", "uv", "pip", "npm", "pnpm", "yarn", "bun", "go",
    "tox", "hg", "ko", "kn", "k8s", "kc", "cd",
    # short language names ('written in C', 'built in R')
    "c", "r", "d",
})

# Short allowlisted tokens that are also common English words/letters. Safe to
# KEEP when the LLM emits them with an entity type, but unsafe to AUTO-RESCUE
# from prose ('all writes now go through' -> 'go' as a tool). Excluded from the
# rescue scan only; the LLM's own typed mentions still survive.
_RESCUE_SKIP_SHORT: frozenset[str] = frozenset({
    "go", "c", "r", "d", "cd", "ls", "ps", "wc", "ko", "kn", "kc", "hg",
})

# Known type overrides: the LLM occasionally confuses tools/services/databases
# for these well-known names. We snap them to the canonical type used across
# the darkmem corpus. Keys are lower-cased.
#
# Underscore-private by name but exported in `__all__` and read by a second
# module: `app/services/code_deriver.py` runs names minted from code through
# this same table so a name from a repository and the same name from a memory
# land on one `(name, entity_type)` row. Changing a value here re-types both
# paths at once; changing the binding's name breaks the deriver's guard
# exemption in `tests/test_code_deriver.py`, which identifies this assignment
# structurally.
_TYPE_OVERRIDES: dict[str, str] = {
    # Self-projects
    "darkmem": "project",
    "darkraise": "project",
    # Services we run / call
    "mem0": "service", "memora": "service",
    "ollama": "service", "openai": "service", "anthropic": "service",
    "vllm": "service", "jenkins": "service", "github actions": "service",
    "github": "service", "gitlab": "service",
    "grafana": "service", "loki": "service", "promtail": "service",
    "searxng": "service", "kafka": "service",
    # Libraries / runtimes / extensions (tools)
    "pgvector": "tool", "asyncio": "tool",
    "bge": "tool", "tree-sitter": "tool", "sentence-transformers": "tool",
    # darkraise-ui is a first-party UI component library — a `tool` dependency,
    # not the `project`, so it flows into the technologies denorm.
    "darkraise-ui": "tool",
    "react": "tool", "fastapi": "tool", "sqlalchemy": "tool", "alembic": "tool",
    "docker": "tool", "docker-compose": "tool", "kubernetes": "tool",
    "kube-proxy": "tool", "kube-apiserver": "tool", "kube-scheduler": "tool",
    "traefik": "tool", "proxmox": "tool", "trpc": "tool",
    "lxc": "tool", "uvicorn": "tool", "celery": "tool",
    "grafana-agent": "tool", "prometheus": "tool", "node-exporter": "tool",
    "otel-collector": "tool", "fluent-bit": "tool", "fluentd": "tool",
    "nginx": "tool", "haproxy": "tool", "envoy": "tool",
    "next.js": "tool", "vite": "tool", "webpack": "tool", "rollup": "tool",
    "pnpm": "tool", "turborepo": "tool", "vitest": "tool",
    # Databases
    "postgres": "database", "postgresql": "database",
    "mysql": "database", "sqlite": "database",
    "redis": "database", "redis-stack": "database",
    "mongodb": "database", "cassandra": "database",
    "dynamodb": "database", "elasticsearch": "database", "opensearch": "database",
    "meilisearch": "database",
    # Vector stores are databases; pgvector stays a `tool` (a Postgres extension).
    "qdrant": "database", "milvus": "database", "weaviate": "database", "chroma": "database",
    # Algorithms / patterns
    "leiden": "algorithm", "louvain": "algorithm",
    "c3": "algorithm", "dijkstra": "algorithm", "rrf": "algorithm",
    # Protocols / standards
    "jwt": "protocol", "mcp": "protocol", "sse": "protocol",
    "http": "protocol", "https": "protocol", "ssh": "protocol",
    "tls": "protocol", "grpc": "protocol", "streamablehttp": "protocol",
}

# Markers that indicate an entity mention is negative. If the 30-char window
# preceding (and including) the mention contains one of these, that mention
# does not count as a positive reference. Used by ``_filter_negation_only``.
_NEGATION_WINDOW = re.compile(
    r"\b(?:"
    r"no"
    r"|not\s+(?:to\s+)?(?:using|use)"
    r"|do(?:es)?\s+not\s+(?:use|using)"
    r"|don't\s+use"
    r"|doesn't\s+use"
    r"|didn't\s+use"
    r"|did\s+not\s+use"
    r"|without"
    # 'instead of' is a comparative/selection cue ("chose X instead of Y"), not a
    # use-negation; the selection gate keeps both endpoints as X IMPROVES_ON Y, so
    # dropping Y here would orphan that edge.
    # 'never use X' needs its own alternative: the bare 'never' branch requires
    # the marker to sit immediately before the mention, so the intervening verb
    # hides it.
    r"|never\s+(?:to\s+)?us(?:e|ed|ing)"
    r"|never"
    r"|avoid(?:s|ing|ed)?"
    r"|skip(?:ped|ping)?"
    r")\s+$",
    re.IGNORECASE,
)


def _is_acronym_of(short: str, long: str) -> bool:
    if not short.isupper() or len(short) < 2:
        return False
    initials = [w[0].upper() for w in re.split(r"[\s-]+", long) if w]
    if len(initials) == len(short):
        return all(a == b for a, b in zip(initials, short))
    words = long.split()
    if len(words) == len(short):
        return all(w[0].upper() == c for w, c in zip(words, short))
    return False


# Strip a trailing infra role-noun so cross-memory names stay canonical:
# 'Postgres cluster' -> 'postgres', 'Proxmox host' -> 'proxmox'.
_DESCRIPTOR_SUFFIX_RE = re.compile(
    r"\s+(?:host|cluster|node|vm|instance|box|daemon|hypervisor"
    r"|source\s+connector|sink\s+connector|connector|exporter|broker)$",
    re.IGNORECASE,
)
# Strip a leading duration/quantifier: '30-minute outage' -> 'outage'.
_LEADING_DURATION_RE = re.compile(
    r"^\d+[-\s]?(?:minute|min|hour|hr|day|week|month|second|sec)s?[-\s]+", re.IGNORECASE
)


def _normalize_names(entities: list[dict]) -> list[dict]:
    out = []
    for e in entities:
        name = (e.get("name") or "").strip()
        if not name:
            continue
        # Strip trailing ``.method`` / ``.attribute`` chains so the entity
        # collapses to its module/library root (``asyncio.create_task`` ->
        # ``asyncio``). Only safe when the head looks like an identifier, and
        # never for a curated dotted name (``next.js``) whose tail is part of
        # the real entity — stripping it would corrupt the name and lose the
        # curated type before _apply_type_overrides runs.
        dotted = _DOTTED_METHOD.match(name)
        if dotted and name.lower() not in _TYPE_OVERRIDES:
            name = dotted.group(1)
        # Allow 2-char tools that are otherwise canonical (rg, fd, vi, …);
        # everything else under 3 chars is too noisy.
        if len(name) < 3 and name.lower() not in _SHORT_TOOL_ALLOWLIST:
            continue
        trimmed = _TRAILING_SUFFIXES.sub("", name).strip()
        # Don't let suffix-stripping collapse a real multi-word entity into a
        # generic noise word that _filter_noise then deletes ('auth module' ->
        # 'auth' -> dropped, which orphans every edge anchored to it). Keep the
        # fuller name when the trimmed head is noise or too short.
        if trimmed and len(trimmed) >= 3 and trimmed.lower() not in _NOISE_NAMES:
            name = trimmed
        stripped = _DESCRIPTOR_SUFFIX_RE.sub("", name).strip()
        if stripped:
            name = stripped
        led = _LEADING_DURATION_RE.sub("", name).strip()
        if led:
            name = led
        if not name:
            continue
        etype = refine_entity_type(name, normalize_entity_type(e.get("type") or "concept"))
        out.append({**e, "name": name, "type": etype})
    return out


def _filter_noise(entities: list[dict]) -> list[dict]:
    out = []
    for e in entities:
        name = e["name"]
        name_stripped = name.strip()
        if name.lower() in _NOISE_NAMES:
            continue
        if name.startswith("@") or name.startswith("$"):
            continue
        if _FILENAME_PATTERN.match(name):
            continue
        if _URL_PATH_PATTERN.match(name_stripped):
            continue
        if _URL_ABSOLUTE_PATTERN.match(name_stripped):
            continue
        if _ENV_VAR_PATTERN.match(name_stripped):
            continue
        if _VALUE_PATTERN.match(name_stripped):
            # Dates, versions, file sizes, durations — values, not entities.
            continue
        words = name.split()
        if len(words) >= 2 and words[0].lower() in ("a", "an", "the", "one", "this", "that"):
            continue
        out.append(e)
    return out


def _snap_hardware_types(entities: list[dict]) -> list[dict]:
    """If an entity name is a known hardware token, force its type to ``tool``.

    The taxonomy has no ``hardware`` class, so the LLM scatters hardware
    mentions across ``entity``, ``artifact``, and ``service`` depending on
    surrounding context. ``tool`` is the closest match in the existing set,
    and we apply it unconditionally when the name matches.
    """
    out = []
    for e in entities:
        name_lower = (e.get("name") or "").strip().lower()
        if name_lower in _HARDWARE_TOKENS:
            out.append({**e, "type": "tool"})
        else:
            out.append(e)
    return out


def _apply_type_overrides(entities: list[dict]) -> list[dict]:
    """Snap well-known names to their canonical type.

    The LLM tends to flip the same well-known names between ``tool``,
    ``service``, and ``concept`` from one run to the next.
    ``_TYPE_OVERRIDES`` is a small allowlist of names whose canonical type
    is unambiguous in the darkmem corpus; for those we override whatever
    the model guessed.
    """
    out = []
    for e in entities:
        name_lower = (e.get("name") or "").strip().lower()
        if name_lower in _TYPE_OVERRIDES:
            out.append({**e, "type": _TYPE_OVERRIDES[name_lower]})
        else:
            out.append(e)
    return out


# Path-with-extension: at least one slash AND a known file extension.
# Captures things like:
#   backend/app/services/llm_seed.py
#   frontend/src/routes/_authenticated/settings.tsx
#   migrations/versions/0001_initial.py
#   backend/app/main.py:health()      (path:symbol form, suffix optional)
# Specifically does NOT match:
#   classA.method1()    (no slash, just dots — method call, not a path)
#   obj.attr.subattr    (same — attribute access, not a module path)
# The slash requirement is what disambiguates path tokens from method
# calls. Dotted-module specs (``app.services.classifier``) are also
# excluded for the same reason — they look identical to chained method
# calls without a slash, and false-positives there poison the graph.
_FILE_PATH_RE = re.compile(
    r"\b"
    r"(?:[\w][\w.\-]*?/)+"            # one or more slash-terminated segments
    r"[\w][\w\-]*"                    # final basename
    r"\.(?:py|pyi|ts|tsx|js|jsx|mjs|cjs|go|rs|java|kt|kts|"
    r"cpp|cc|cxx|c|h|hpp|hh|cs|rb|php|swift|m|mm|"
    r"html|htm|css|scss|sass|less|"
    r"json|jsonc|yaml|yml|toml|ini|cfg|conf|env|"
    r"sql|prisma|sh|bash|zsh|fish|ps1|bat|cmd|"
    r"md|mdx|rst|tex|"
    r"proto|graphql|gql|"
    r"lua|jl|hs|ml|mli|scala|swift|zig|elm|ex|exs|erl|clj|cljs|"
    r"xml|svg|csv|tsv"
    r")"
    r"(?::[\w.\-]+(?:\(\))?)?"        # optional :symbol or :symbol() suffix
    r"\b"
)


def _rescue_file_path_entities(entities: list[dict], content: str) -> list[dict]:
    """Rescue file-path tokens the LLM dropped.

    deepseek-v4-pro / gpt-5.4-mini extract code symbols (function names,
    class names) reliably, but consistently drop file-path tokens like
    ``backend/app/services/llm_seed.py`` even when they are mentioned
    multiple times in a relocation memory's prose. Three rounds of
    prompt instruction (rounds 5, 6, 10) had no effect on this. With
    file paths missing, Pattern D in the relation rescue cannot find
    the new-home target of a REPLACES, so the relocation edge is lost.

    This rescue runs after the LLM extraction (and after
    ``_rescue_known_entities``) and adds any path-like token that
    matches ``_FILE_PATH_RE`` and isn't already covered by an existing
    entity span. The pattern requires a slash AND a known extension —
    plain dotted forms like ``classA.method1()`` and
    ``obj.attr.subattr`` are NOT matched, because without a slash they
    cannot be reliably distinguished from chained attribute / method
    calls.

    Added entities are typed ``artifact`` consistently (rule 7b).
    """
    if not content:
        return entities
    out = list(entities)
    seen_lower = {(e.get("name") or "").strip().lower() for e in out}

    # Build occupied spans the same way ``_rescue_known_entities`` does
    # so we don't duplicate when the LLM did extract the path. We use
    # case-insensitive matching against the raw content.
    text_lower = content.lower()
    occupied: list[tuple[int, int]] = []
    for e in entities:
        e_name = (e.get("name") or "").strip()
        if not e_name:
            continue
        e_low = e_name.lower()
        start = 0
        while True:
            idx = text_lower.find(e_low, start)
            if idx < 0:
                break
            occupied.append((idx, idx + len(e_low)))
            start = idx + 1

    def _overlaps_existing(s: int, e: int) -> bool:
        return any(not (e <= os or s >= oe) for os, oe in occupied)

    for m in _FILE_PATH_RE.finditer(content):
        s, e = m.span()
        if _overlaps_existing(s, e):
            continue
        path = m.group(0)
        key = path.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        out.append({"name": path, "type": "artifact", "properties": {}})
        occupied.append((s, e))
    return out


def _rescue_known_entities(entities: list[dict], content: str) -> list[dict]:
    """Add curated names that appear in the text but were missed by the LLM.

    The model occasionally drops well-known short or hardware names (CPU,
    GPU, rg, fd, OpenAI, LXC). For names we have canonical types for, we
    safely whole-word match against the text and insert the missing entity
    with the right type. Anything not on the curated list is left alone.

    Honours the same negation suppression that ``_filter_negation_only``
    applies — if every appearance of the name is preceded by a negation
    marker (``no CUDA``, ``without GPU``), the name is NOT rescued. This
    avoids re-introducing entities that the upstream filter just removed
    for being negation-only.
    """
    if not content:
        return entities
    have = {(e.get("name") or "").strip().lower() for e in entities}
    rescued = list(entities)
    # Map every existing entity's text span(s) so we can suppress rescue hits
    # that fall *inside* a longer mention. Without this, ``darkraise`` matches
    # inside ``darkraise-ui`` and ``github`` matches inside ``GitHub Actions``,
    # because the word-boundary regex below treats ``-`` and `` `` as breaks.
    occupied: list[tuple[int, int]] = []
    for e in entities:
        e_name = (e.get("name") or "").strip()
        if not e_name:
            continue
        e_pat = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(e_name)}(?![A-Za-z0-9_])", re.IGNORECASE)
        for m in e_pat.finditer(content):
            occupied.append((m.start(), m.end()))
    candidates: dict[str, str] = {}
    for name, etype in _TYPE_OVERRIDES.items():
        candidates[name] = etype
    for name in _HARDWARE_TOKENS:
        candidates.setdefault(name, "tool")
    for name in _SHORT_TOOL_ALLOWLIST:
        if name in _RESCUE_SKIP_SHORT:
            continue
        candidates.setdefault(name, "tool")
    for name, etype in candidates.items():
        if name in have:
            continue
        # Whole-word, case-insensitive match. Use a manual word boundary that
        # accepts adjacent ``.`` and ``-`` as separators so ``CPU.`` and
        # ``CPU-bound`` surface the bare token. ``_`` stays inside the class:
        # it binds an identifier rather than separating words, so ``CPU_count``
        # must not yield ``cpu``.
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", re.IGNORECASE)
        any_positive = False
        for m in pattern.finditer(content):
            span_len = m.end() - m.start()
            inside_longer = any(
                r_start <= m.start() and m.end() <= r_end and (r_end - r_start) > span_len
                for r_start, r_end in occupied
            )
            if inside_longer:
                continue
            preceding = content[max(0, m.start() - 30) : m.start()]
            if not _NEGATION_WINDOW.search(preceding):
                any_positive = True
                break
        if any_positive:
            rescued.append({"name": name, "type": etype, "properties": {}})
            have.add(name)
            # If the just-added compound contains an existing entity as a
            # sub-token (``docker-compose`` covering ``docker``,
            # ``grafana-agent`` covering ``grafana``), drop the bare prefix
            # the model emitted before rescue ran. Only fires for compound
            # names that the curated lists explicitly define, so the risk
            # of clobbering a legitimately-distinct short entity is bounded.
            tokens_in_compound = {
                t.lower() for t in re.split(r"[-_./\s]+", name) if t
            }
            tokens_in_compound.discard(name)
            if tokens_in_compound:
                rescued = [
                    e for e in rescued
                    if (e.get("name") or "").strip().lower() == name
                    or (e.get("name") or "").strip().lower() not in tokens_in_compound
                ]
                have = {(e.get("name") or "").strip().lower() for e in rescued}
    return rescued


def _mentioned_whole_word(name: str, content: str) -> bool:
    """True when ``name`` appears in ``content`` as a whole word."""
    if not name:
        return False
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"
    return re.search(pattern, content, re.IGNORECASE) is not None


# Head nouns the extraction system prompt already declares to be `artifact`:
# rule 7b's named app components and surfaces, and rule 9j's first-class
# documents. Transcribed from the prompt rather than invented here, because
# the model under-complies with both rules and doc 06 §4's standing remedy is
# the pass chain, never another prompt round. Any head noun outside these two
# sets keeps the taxonomy's default for an absent type — the prompt types
# 'savepoint' `concept` for exactly that reason.
_ARTIFACT_HEAD_NOUNS: frozenset[str] = frozenset({
    # rule 7b — named app components and surfaces
    "app", "frontend", "backend", "cli", "api", "gateway", "worker",
    "daemon", "scheduler", "dashboard", "console", "panel", "portal",
    "modal", "tab", "widget",
    # rule 9j — first-class documents
    "postmortem", "rfc", "doc", "report", "spec",
})


def _endpoint_entity_type(name: str) -> str:
    head = re.split(r"[\s\-_/]+", name.strip().lower())[-1] if name.strip() else ""
    head = head.rstrip("s") if head.rstrip("s") in _ARTIFACT_HEAD_NOUNS else head
    return "artifact" if head in _ARTIFACT_HEAD_NOUNS else normalize_entity_type("")


def _rescue_relation_endpoints(
    entities: list[dict], relationships: list[dict], content: str,
) -> list[dict]:
    """Reinstate a name the model asserted in one of its own edges but left
    out of its own entity list.

    The extraction model's ``entities`` array is biased towards proper nouns.
    It reliably lists ``Auth0``, ``RFC 7519`` and ``Datadog`` while dropping
    the common-noun component the sentence is actually about — ``the design
    doc``, ``the web app``, ``the CLI`` — even when its ``relationships``
    array names that component as an endpoint of the same response.
    ``_remap_to_valid_entities`` then deletes every edge anchored to the
    missing name, so one omission costs the entity *and* all of its
    relations. An edge is an assertion that both of its endpoints exist, so
    the model's own output already carries the evidence and no curated list
    of names is needed to act on it.

    A candidate is admitted only if it clears the same bar a model-listed
    entity clears: it must be grounded in the source text as a whole word,
    and it is run through the entity-shaping stage itself, so the noise,
    literal, fidelity and negation filters apply to it exactly as they
    applied to the model's own list and cannot drift apart from it.
    """
    if not content or not relationships:
        return entities
    have = {(e.get("name") or "").strip().lower() for e in entities}
    candidates: list[dict] = []
    seen: set[str] = set()
    for r in relationships:
        for side in ("source", "target"):
            name = (r.get(side) or "").strip()
            key = name.lower()
            if not name or key in have or key in seen:
                continue
            if not _mentioned_whole_word(name, content):
                continue
            seen.add(key)
            candidates.append({
                "name": name,
                "type": _endpoint_entity_type(name),
                "properties": {},
            })
    if not candidates:
        return entities

    shaping = tuple(p for p in PASS_REGISTRY if p.stage == STAGE_ENTITY_SHAPING)
    shaped = run_passes(shaping, CleanState(content=content, entities=candidates))

    out = list(entities)
    for e in shaped.entities:
        key = (e.get("name") or "").strip().lower()
        if not key or key in have:
            continue
        have.add(key)
        out.append(e)
    return out


# Connector phrases that imply a relation when sandwiched between two
# entities in close text proximity. Order matters: multi-word phrases come
# first so ``deployed on`` wins over ``on``. The 4th tuple element is a
# vestigial ``hardware_only`` flag — always False and no longer read (unpacked
# as ``_legacy_hardware_only`` below); the hardware-gating behavior was removed.
_RESCUE_CONNECTORS: list[tuple[str, str, float, bool]] = [
    # Multi-word / unambiguous connectors. Fire via the adjacency pass
    # (src immediately before connector). Single-word "implicit subject"
    # connectors (``via``, ``with``, ``using``, ``to``) moved to the
    # subject-tracking pass below because they routinely carry an implicit
    # grammatical subject the nearest-entity heuristic gets wrong.
    ("deployed on", "DEPLOYED_ON", 0.85, False),
    ("running on", "DEPLOYED_ON", 0.85, False),
    ("runs on", "DEPLOYED_ON", 0.85, False),
    ("hosted on", "DEPLOYED_ON", 0.85, False),
    ("lives on", "DEPLOYED_ON", 0.8, False),
    ("stored on", "DEPLOYED_ON", 0.8, False),
    ("improves on", "REPLACES", 0.8, False),
    ("improves upon", "REPLACES", 0.8, False),
    ("builds on", "REPLACES", 0.7, False),
    ("ships with", "DEPENDS_ON", 0.7, False),
    ("depends on", "DEPENDS_ON", 0.85, False),
    ("instead of", "REPLACES", 0.75, False),
    ("uses", "USES", 0.85, False),
    ("on", "DEPLOYED_ON", 0.6, False),
]


# Single-word connectors that commonly carry an IMPLICIT grammatical subject
# — the real src is the sentence's subject, not the closest preceding entity.
# Example: ``Promtail ships logs to Loki via gRPC`` — ``via gRPC`` belongs to
# Promtail, not Loki even though Loki is closer. Handled by the subject-
# tracking pass (``_rescue_relations_subject_tracking``).
_SUBJECT_TRACKED_CONNECTORS: list[tuple[str, str, float]] = [
    ("via", "USES", 0.65),
    ("with", "USES", 0.6),
    ("using", "USES", 0.7),
    ("to", "USES", 0.55),  # very weak; only fires when target is an entity
]


# Generic REPLACES extraction. Two transition-verb patterns cover the
# overwhelming majority of "we moved off X for Y" surface forms in dev notes
# without enumerating every phrasing case-by-case.
#
# Pattern A — verb of motion/change scoped to a clause, then "from X to Y":
#   "Switched ... from postgres-15 to postgres-17" -> postgres-17 REPLACES postgres-15
#   "Migrated darkraise-ui from Webpack to Vite"   -> vite REPLACES webpack
#   Verb may be far from the from/to anchors as long as it's earlier in the
#   same clause.
#
# Pattern B — explicit replacement verb directly governing two entities:
#   "Replaced X with Y" / "Replaced X by Y"  -> Y REPLACES X
#   "Swapped X for Y" / "Dropped X for Y"   -> Y REPLACES X
#   "Phased out X in favor of Y"            -> Y REPLACES X
#
# Pattern C — explicit "Y replaces/supersedes/deprecates X" verb:
#   These are cheap to catch when the LLM misses them.
_TRANSITION_VERBS_RE = re.compile(
    r"\b(?:"
    r"switch(?:ed|es|ing)?|"
    r"migrat(?:e|ed|ing|es)|"
    r"mov(?:e|ed|ing|es)|"
    r"upgrad(?:e|ed|ing|es)|"
    r"downgrad(?:e|ed|ing|es)|"
    r"cut(?:\s+over)?|"
    r"transition(?:ed|ing|s)?|"
    r"port(?:ed|ing|s)?|"
    r"adopt(?:ed|ing|s)?|"
    r"swap(?:ped|ping|s)?|"
    r"drop(?:ped|ping|s)?|"
    r"replac(?:ed|es|ing)?|"
    r"phas(?:e|ed|es|ing)\s+out|"
    r"jump(?:ed|ing|s)?|"
    r"extract(?:ed|ing|s)?|"
    r"lift(?:ed|ing|s)?|"
    r"reloc(?:ate|ated|ating|ates)"
    r")\b",
    re.IGNORECASE,
)
_REPLACE_VERB_RE = re.compile(
    r"\b(?:replac(?:ed|es|ing)?|swap(?:ped|ping|s)?|drop(?:ped|ping|s)?|"
    r"phas(?:ed|es|ing)\s+out)\b",
    re.IGNORECASE,
)
_SUPERSEDES_RE = re.compile(
    r"\b(?:replaces|supersedes|deprecates|obsoletes)\b",
    re.IGNORECASE,
)


def _split_clauses(text_lower: str) -> list[tuple[int, int]]:
    """Return [(start, end), ...] character ranges for each clause.

    Splits on strong sentence/clause boundaries: ``. ! ? ;`` followed by
    whitespace. Each clause is a half-open range ``[start, end)``.
    """
    clauses: list[tuple[int, int]] = []
    last = 0
    for m in re.finditer(r"[.!?;]\s+", text_lower):
        clauses.append((last, m.start()))
        last = m.end()
    if last < len(text_lower):
        clauses.append((last, len(text_lower)))
    return clauses


# Prepositions that govern an entity-as-object pattern. An entity preceded
# by one of these is NOT a candidate clause subject — it is the object of
# the preposition (``Adding via MCP`` -> mcp is the object of via, not the
# clause subject).
_PREPOSITIONS_BEFORE_OBJECT: frozenset[str] = frozenset({
    "via", "with", "by", "for", "to", "from", "of", "on", "in", "at",
    "into", "onto", "through", "over", "under", "during", "without",
    "against", "between", "before", "after",
})

# Articles and demonstratives that can appear between a preposition and
# its object: ``in the eu-west-1 region`` -> ``eu-west-1`` is still the
# object of ``in`` even with ``the`` intervening. Skipped during the
# walk-back in ``_is_object_of_preposition``.
_ARTICLES_AND_DEMONSTRATIVES: frozenset[str] = frozenset({
    "the", "a", "an", "this", "that", "these", "those",
})


def _is_object_of_preposition(text_lower: str, entity_start: int) -> bool:
    """True if the entity at ``entity_start`` is preceded by a preposition,
    optionally with one or two articles/demonstratives between (``in the
    eu-west-1`` and ``by Riya Patel`` both qualify). Used to disqualify
    the entity as a clause subject in the rescue passes.
    """
    # Window allows for ``preposition + article + entity`` plus whitespace.
    window_start = max(0, entity_start - 25)
    preceding = text_lower[window_start:entity_start].rstrip()
    if not preceding:
        return False
    tokens = [
        re.sub(r"[^a-z]", "", t)
        for t in re.split(r"\s+", preceding)
    ]
    tokens = [t for t in tokens if t]
    # Walk backwards skipping articles/demonstratives, then check the next
    # token. ``in the eu-west-1`` -> skip ``the``, hit ``in`` -> True.
    for tok in reversed(tokens):
        if tok in _ARTICLES_AND_DEMONSTRATIVES:
            continue
        return tok in _PREPOSITIONS_BEFORE_OBJECT
    return False


def _clause_for_position(
    clauses: list[tuple[int, int]], position: int,
) -> tuple[int, int] | None:
    """Return the [start, end) clause range containing ``position``."""
    for start, end in clauses:
        if start <= position < end:
            return (start, end)
    return None


def _clause_subject(
    text_lower: str,
    occurrences: list[tuple[str, int, int]],
    clause_range: tuple[int, int],
    *,
    before: int | None = None,
) -> tuple[str, int, int] | None:
    """Find the syntactic subject of the clause: earliest entity in the
    clause that is not an object of a preposition.

    ``before`` optionally caps the search to entities starting before
    that absolute position, so we don't pick a clause subject that
    appears *after* the verb we're trying to anchor.

    Used by the rescue passes to fall back to the real subject when the
    closest preceding entity is a prepositional object (``Phoenix is
    written in Rust and depends on Tokio`` -> rust is object of ``in``,
    real subject is phoenix).
    """
    clause_start, clause_end = clause_range
    candidates = [
        occ for occ in occurrences
        if clause_start <= occ[1] < clause_end
        and (before is None or occ[1] < before)
    ]
    candidates.sort(key=lambda o: o[1])
    for cand in candidates:
        if not _is_object_of_preposition(text_lower, cand[1]):
            return cand
    return None


# Dedup key for the rescue layer: source, target, and the relation's
# REPLACES-family bucket rather than its raw type, so an LLM-emitted
# IMPROVES_ON suppresses a rescue-emitted REPLACES for the same pair.
def _rescue_key(r: dict) -> tuple[str, str, str]:
    return (
        (r.get("source") or "").strip().lower(),
        (r.get("target") or "").strip().lower(),
        _family_key(r.get("type") or ""),
    )


class _RescueContext(NamedTuple):
    text_lower: str
    name_to_entity: dict[str, dict]
    occurrences: list[tuple[str, int, int]]
    existing: set[tuple[str, str, str]]
    clauses: list[tuple[int, int]]


def _rescue_context(
    entities: list[dict], relations: list[dict], content: str,
) -> _RescueContext | None:
    """The span index the three Stage-3 synthesis passes share.

    Rebuilt per pass rather than threaded between them: each pass reads
    only ``(entities, relationships, content)`` from the registry state,
    and ``existing`` recomputed from the incoming relations equals the
    set the previous pass left behind, since every emitted triple is
    appended under exactly the key that was added.
    """
    if not entities or not content:
        return None

    text_lower = content.lower()
    name_to_entity: dict[str, dict] = {}
    for e in entities:
        n = (e.get("name") or "").strip().lower()
        if n:
            name_to_entity[n] = e

    occurrences: list[tuple[str, int, int]] = []
    for name in name_to_entity:
        for m in re.finditer(
            rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text_lower,
        ):
            occurrences.append((name, m.start(), m.end()))
    occurrences.sort(key=lambda x: x[1])

    return _RescueContext(
        text_lower=text_lower,
        name_to_entity=name_to_entity,
        occurrences=occurrences,
        existing={_rescue_key(r) for r in relations},
        clauses=_split_clauses(text_lower),
    )


def _rescue_relations(
    entities: list[dict], relations: list[dict], content: str,
) -> list[dict]:
    """Pattern-based relation synthesis from text — the adjacency pass.

    For each pair of entities in close text proximity, emit an inferred
    triple if a connector phrase (``on``, ``with``, ``uses``, ``runs on``,
    ``deployed on``, ``instead of`` …) appears between them under tight
    distance constraints:

    - ``head_gap`` (src end → connector start) <= 15 chars: the source
      must be the immediate subject of the connector, not an earlier
      sentence's noun.
    - ``tail_gap`` (connector end → tgt start) <= MAX_TAIL_GAP (15) chars: the
      target must be close to the connector.

    These constraints rule out the most common false-positive pattern —
    pairing the *closest preceding entity* with a connector that
    grammatically belongs to a later subject (e.g. ``MCP to confirm
    extraction with pgvector`` should NOT yield ``MCP USES pgvector``).

    Both endpoints must already be in the entity list (no hallucination).
    Triples carry ``properties.rescue = True`` and a moderate weight
    (0.5-0.85) reflecting the indirect inference.

    Skips any pair whose between-text contains a negation marker so we
    don't infer ``X USES Y`` from ``X with no Y``.
    """
    ctx = _rescue_context(entities, relations, content)
    if ctx is None:
        return relations
    text_lower, name_to_entity, occurrences, existing, clauses = ctx
    out = list(relations)

    MAX_HEAD_GAP = 15  # src_end -> connector_start
    MAX_TAIL_GAP = 15  # connector_end -> tgt_start

    for i, (src_name, src_start, src_end) in enumerate(occurrences):
        for j in range(i + 1, len(occurrences)):
            tgt_name, tgt_start, _tgt_end = occurrences[j]
            if tgt_start - src_end > 60:
                break
            if src_name == tgt_name:
                continue

            # Skip if there is any other entity between src and tgt.
            # ``grep instead of find`` should not produce ``rg REPLACES find``
            # just because ``rg`` was the most recent prior entity — the
            # closer ``grep`` is the right subject.
            has_intermediate = any(
                src_end < o[1] < tgt_start and o[0] not in (src_name, tgt_name)
                for o in occurrences
            )
            if has_intermediate:
                continue

            between = text_lower[src_end:tgt_start]
            # Sentence boundary between src and tgt is a hard stop — relations
            # don't usually span sentences in developer notes, and ``X. Y on Z``
            # accidentally fires ``X DEPLOYED_ON Z`` via the ``Y on Z`` clause.
            if re.search(r"[.!?]\s", between):
                continue
            # Negation between src and tgt suppresses the rescue. We do NOT
            # include "instead of" here because that phrase IS one of our
            # legitimate connectors (REPLACES) — handled below.
            if re.search(r"\b(?:no|not|without|never)\b", between):
                continue

            matched: tuple[str, float, int] | None = None
            for conn, rel, weight, _legacy_hardware_only in _RESCUE_CONNECTORS:
                m = re.search(rf"\b{re.escape(conn)}\b", between)
                if not m:
                    continue
                head_gap = m.start()
                tail_gap = len(between) - m.end()
                if head_gap > MAX_HEAD_GAP or tail_gap > MAX_TAIL_GAP:
                    continue
                matched = (rel, weight, src_end + m.start())
                break
            if not matched:
                continue

            rel_type, weight, conn_abs_start = matched

            # All connectors in ``_RESCUE_CONNECTORS`` carry an explicit
            # subject (``X uses Y``, ``X depends on Y``, ``X deployed on
            # Y``, ``X replaces Y``). When the closest preceding entity is
            # a prepositional object, the *real* subject of the verb sits
            # earlier in the clause. Without this fallback, "Phoenix is
            # written in Rust and depends on Tokio" emits ``rust
            # DEPENDS_ON tokio`` because rust is the closest preceding
            # entity to ``depends on`` — but rust is the object of ``in``.
            # Promote the clause's syntactic subject when the closest src
            # is disqualified.
            effective_src_name = src_name
            effective_src_canon: str | None = None
            if _is_object_of_preposition(text_lower, src_start):
                clause_range = _clause_for_position(clauses, conn_abs_start)
                clause_subject = (
                    _clause_subject(
                        text_lower, occurrences, clause_range,
                        before=conn_abs_start,
                    )
                    if clause_range
                    else None
                )
                if clause_subject is None or clause_subject[0] == tgt_name:
                    continue
                effective_src_name = clause_subject[0]
                effective_src_canon = (
                    name_to_entity[effective_src_name].get("name")
                    or effective_src_name
                )

            if effective_src_name == tgt_name:
                continue

            src_canon = (
                effective_src_canon
                or name_to_entity[effective_src_name].get("name")
                or effective_src_name
            )
            tgt_canon = name_to_entity[tgt_name].get("name") or tgt_name
            key = (src_canon.strip().lower(), tgt_canon.strip().lower(), _family_key(rel_type))
            if key in existing:
                continue
            existing.add(key)
            out.append({
                "source": src_canon,
                "target": tgt_canon,
                "type": rel_type,
                "properties": {"rescue": True},
                "weight": weight,
            })

    return out


def _rescue_relations_replaces(
    entities: list[dict], relations: list[dict], content: str,
) -> list[dict]:
    """Generic REPLACES extractor for transition-verb patterns.

    Three pattern families:
      A. ``<transition_verb> ... from X to Y``  -> Y REPLACES X
      B. ``<replace_verb> X (with|by|for|in favor of) Y``  -> Y REPLACES X
      C. ``Y (replaces|supersedes|deprecates|obsoletes) X``  -> Y REPLACES X

    Both endpoints must already be in the entity list. Pattern matching is
    scoped to a single clause (split on ``. ! ? ;``) so a transition verb
    in one sentence cannot pull "from/to" anchors from the next.

    Negation between the verb and the entities suppresses the rescue.
    """
    ctx = _rescue_context(entities, relations, content)
    if ctx is None:
        return relations
    text_lower, name_to_entity, occurrences, existing, clauses = ctx
    out = list(relations)

    def _emit(src_name: str, tgt_name: str, weight: float, label: str) -> None:
        if src_name == tgt_name:
            return
        src_canon = name_to_entity[src_name].get("name") or src_name
        tgt_canon = name_to_entity[tgt_name].get("name") or tgt_name
        key = (src_canon.strip().lower(), tgt_canon.strip().lower(), _family_key("REPLACES"))
        if key in existing:
            return
        existing.add(key)
        out.append({
            "source": src_canon,
            "target": tgt_canon,
            "type": "REPLACES",
            "properties": {"rescue": True, "pattern": label},
            "weight": weight,
        })

    def _first_entity_in(start: int, end: int) -> tuple[str, int, int] | None:
        """First entity occurrence whose start lies in [start, end)."""
        for occ in occurrences:
            if start <= occ[1] < end:
                return occ
        return None

    for clause_start, clause_end in clauses:
        clause = text_lower[clause_start:clause_end]
        if re.search(r"\b(?:no|not|without|never)\b", clause):
            # Skip outright; cheap negation guard at clause level.
            continue

        # Pattern A: verb earlier in clause, then "from X to Y".
        for verb_m in _TRANSITION_VERBS_RE.finditer(clause):
            tail = clause[verb_m.end():]
            from_m = re.search(r"\bfrom\b", tail)
            if not from_m:
                continue
            from_abs_end = clause_start + verb_m.end() + from_m.end()
            after_from = text_lower[from_abs_end:clause_end]
            to_m = re.search(r"\bto\b", after_from)
            if not to_m:
                continue
            x_zone_start = from_abs_end
            x_zone_end = from_abs_end + to_m.start()
            y_zone_start = from_abs_end + to_m.end()
            y_zone_end = clause_end
            x_occ = _first_entity_in(x_zone_start, x_zone_end)
            y_occ = _first_entity_in(y_zone_start, y_zone_end)
            if x_occ and y_occ:
                _emit(y_occ[0], x_occ[0], 0.85, "from-to")
            break  # one from-to per clause is enough

        # Pattern B: replace-verb directly governs "X (with|by|for|in favor of) Y".
        for verb_m in _REPLACE_VERB_RE.finditer(clause):
            tail = clause[verb_m.end():]
            prep_m = re.search(r"\b(?:with|by|for|in\s+favor\s+of)\b", tail)
            if not prep_m:
                continue
            verb_end_abs = clause_start + verb_m.end()
            prep_start_abs = verb_end_abs + prep_m.start()
            prep_end_abs = verb_end_abs + prep_m.end()
            x_occ = _first_entity_in(verb_end_abs, prep_start_abs)
            y_occ = _first_entity_in(prep_end_abs, clause_end)
            if x_occ and y_occ:
                _emit(y_occ[0], x_occ[0], 0.8, "verb-x-prep-y")

        # Pattern C: "Y replaces/supersedes/deprecates X".
        for verb_m in _SUPERSEDES_RE.finditer(clause):
            verb_start_abs = clause_start + verb_m.start()
            verb_end_abs = clause_start + verb_m.end()
            # Y is the entity ending immediately before the verb (within ~25 chars).
            y_occ = None
            for occ in reversed(occurrences):
                if occ[2] <= verb_start_abs and verb_start_abs - occ[2] <= 25:
                    y_occ = occ
                    break
                if occ[2] <= verb_start_abs - 25:
                    break
            # If the closest preceding entity is a prepositional object
            # (e.g., "authored by Riya Patel that replaces Triton" -> Riya
            # Patel is object of ``by``), promote the clause's syntactic
            # subject. Without this fix every Pattern-C run produces the
            # closest-noun-as-Y bug observed in 11 model evaluations.
            if y_occ is not None and _is_object_of_preposition(text_lower, y_occ[1]):
                clause_subject = _clause_subject(
                    text_lower, occurrences,
                    (clause_start, clause_end),
                    before=verb_start_abs,
                )
                y_occ = clause_subject
            x_occ = _first_entity_in(verb_end_abs, clause_end)
            if x_occ and y_occ:
                _emit(y_occ[0], x_occ[0], 0.85, "supersedes")

        # Pattern D: file-level relocation "<verb> ... out of A into B"
        # -> B REPLACES A. The existing Pattern A handles "from X to Y";
        # decision memories about code refactors use "out of A into B"
        # ("seed data was moved out of migration 0001 into llm_seed.py")
        # which never matches Pattern A's "from"/"to" anchors. Six rounds
        # of prompt patches across 2026-05-02 failed to elicit REPLACES
        # on this surface form from deepseek-v4-pro, so the rescue layer
        # captures it deterministically. Both endpoints must already be
        # in the entity list — this never invents new entities, only the
        # edge between two the LLM already extracted.
        #
        # Two refinements compared to Patterns A-C, both observed live
        # on memory 89b069f7:
        #
        # 1. A-zone matching prefers the LONGEST entity span, not the
        #    first by start position. The text "Alembic migration 0001"
        #    contains both ``alembic`` (tool) and ``alembic migration
        #    0001`` (artifact) as entities; first-by-start picks the
        #    shorter one and the rescue produces the wrong target. The
        #    longest-span tiebreak resolves to the more specific entity.
        #
        # 2. B-zone matching uses FIRST-by-start (the entity adjacent to
        #    ``into``) and requires its start to fall within 50 chars of
        #    the marker. Two reasons:
        #    - "first" matches the relocation phrasing: the new home is
        #      the noun immediately after ``into``, not the longest noun
        #      anywhere downstream.
        #    - The 50-char window is tight enough to skip distant
        #      entities when the obvious file-path target wasn't
        #      extracted (the round-9 failure mode), so the rescue
        #      declines to fire instead of producing a wrong edge.
        _B_ZONE_WINDOW = 50
        for verb_m in _TRANSITION_VERBS_RE.finditer(clause):
            tail = clause[verb_m.end():]
            out_of_m = re.search(r"\bout\s+of\b", tail)
            if not out_of_m:
                continue
            out_of_abs_end = clause_start + verb_m.end() + out_of_m.end()
            after_out_of = text_lower[out_of_abs_end:clause_end]
            into_m = re.search(r"\binto\b", after_out_of)
            if not into_m:
                continue
            a_zone_start = out_of_abs_end
            a_zone_end = out_of_abs_end + into_m.start()
            b_zone_start = out_of_abs_end + into_m.end()
            b_zone_end = min(clause_end, b_zone_start + _B_ZONE_WINDOW)

            # A-zone: pick the longest entity whose span is fully inside
            # the zone (start AND end). Prefers ``alembic migration 0001``
            # over ``alembic`` when both overlap.
            a_occ = None
            a_span = -1
            for occ in occurrences:
                name_a, s_a, e_a = occ
                if s_a < a_zone_start or e_a > a_zone_end:
                    continue
                length = e_a - s_a
                if length > a_span:
                    a_span = length
                    a_occ = occ

            # B-zone: pick the FIRST entity by start position whose
            # start lies within the 50-char window after ``into``. The
            # relocation noun the writer intended is the one adjacent
            # to ``into``, not the longest noun further downstream.
            b_occ = None
            b_best_start = b_zone_end
            for occ in occurrences:
                name_b, s_b, e_b = occ
                if s_b < b_zone_start or s_b >= b_zone_end:
                    continue
                if s_b < b_best_start:
                    b_best_start = s_b
                    b_occ = occ

            if a_occ and b_occ:
                _emit(b_occ[0], a_occ[0], 0.85, "out-of-into")
            break  # one out-of-into per clause is enough

    return out


def _rescue_relations_subject_tracking(
    entities: list[dict], relations: list[dict], content: str,
) -> list[dict]:
    """Emit triples keyed on the clause's grammatical subject, not nearest entity.

    For each clause:
    - Identify the subject = first entity occurrence in the clause.
    - For each ``via / with / using / to`` connector in the clause after the
      subject, find the nearest entity after the connector. Emit
      ``(subject, that-entity, USES)`` if the tail gap is tight and the
      triple is not already present.

    Negation between the subject and the connector still suppresses.

    Catches ``Promtail ships logs to Loki via gRPC`` as ``promtail USES
    grpc`` + ``promtail USES loki`` instead of the adjacency pass's
    nearest-entity misread (``loki USES grpc``).
    """
    ctx = _rescue_context(entities, relations, content)
    if ctx is None:
        return relations
    text_lower, name_to_entity, occurrences, existing, clauses = ctx
    out = list(relations)
    MAX_TAIL_GAP = 15

    # Group occurrences by clause index for fast lookup.
    clause_occurrences: dict[int, list[tuple[str, int, int]]] = {}
    for occ in occurrences:
        for idx, (start, end) in enumerate(clauses):
            if start <= occ[1] < end:
                clause_occurrences.setdefault(idx, []).append(occ)
                break

    for idx, (clause_start, clause_end) in enumerate(clauses):
        occs = clause_occurrences.get(idx, [])
        if not occs:
            continue
        # Subject = earliest entity in this clause that is NOT the object
        # of a preposition. Skip prepositional objects so we don't pick
        # ``mcp`` as the subject of ``Adding via MCP to confirm extraction
        # with pgvector`` — mcp is the object of ``via``.
        occs.sort(key=lambda o: o[1])
        subject_name = subject_end = None
        for cand_name, cand_start, cand_end in occs:
            if _is_object_of_preposition(text_lower, cand_start):
                continue
            subject_name, _subject_start, subject_end = cand_name, cand_start, cand_end
            break
        if subject_name is None:
            continue
        subject_canon = name_to_entity[subject_name].get("name") or subject_name

        clause_text = text_lower[clause_start:clause_end]

        for conn, rel, weight in _SUBJECT_TRACKED_CONNECTORS:
            for conn_match in re.finditer(rf"\b{re.escape(conn)}\b", clause_text):
                conn_abs_end = clause_start + conn_match.end()
                if conn_abs_end <= subject_end:
                    # Connector appeared BEFORE the subject — wrong direction.
                    continue
                between_subject_and_conn = text_lower[subject_end:clause_start + conn_match.start()]
                if re.search(r"\b(?:no|not|without|never)\b", between_subject_and_conn):
                    continue

                # Find the nearest entity after the connector (same clause).
                nearest_tgt: tuple[str, int] | None = None
                for o_name, o_start, _o_end in occs:
                    if o_start < conn_abs_end:
                        continue
                    if o_name == subject_name:
                        continue
                    if nearest_tgt is None or o_start < nearest_tgt[1]:
                        nearest_tgt = (o_name, o_start)

                if not nearest_tgt:
                    continue
                tgt_name, tgt_start = nearest_tgt
                tail_gap = tgt_start - conn_abs_end
                if tail_gap > MAX_TAIL_GAP:
                    continue
                # Negation BETWEEN the connector and the target ("with no
                # GPU", "using zero CUDA") flips the meaning of the triple.
                between_conn_and_tgt = text_lower[conn_abs_end:tgt_start]
                if re.search(r"\b(?:no|not|without|never|zero)\b", between_conn_and_tgt):
                    continue

                tgt_canon = name_to_entity[tgt_name].get("name") or tgt_name
                key = (
                    subject_canon.strip().lower(),
                    tgt_canon.strip().lower(),
                    _family_key(rel),
                )
                if key in existing:
                    continue
                existing.add(key)
                out.append({
                    "source": subject_canon,
                    "target": tgt_canon,
                    "type": rel,
                    "properties": {"rescue": True, "subject_tracked": True},
                    "weight": weight,
                })

    return out


def _filter_negation_only(
    entities: list[dict], content: str,
) -> tuple[list[dict], set[str]]:
    """Drop entities whose every mention is governed by negation.

    Returns ``(kept_entities, dropped_names)``. The dropped set is used by
    relation cleanup to also strip any triple that references one of these
    ghosts — most often a hallucinated ``REPLACES`` against a thing the
    text only said we *don't* use.
    """
    if not content:
        return entities, set()
    text = content
    out: list[dict] = []
    dropped: set[str] = set()
    for e in entities:
        name = e.get("name") or ""
        if not name:
            continue
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"
        positive_mention = False
        any_mention = False
        for m in re.finditer(pattern, text, re.IGNORECASE):
            any_mention = True
            # Look at the 30 chars immediately preceding this mention. If
            # they end with a negation marker (e.g. "no ", "without ") then
            # this mention is negative.
            preceding = text[max(0, m.start() - 30) : m.start()]
            if not _NEGATION_WINDOW.search(preceding):
                positive_mention = True
                break
        if any_mention and not positive_mention:
            dropped.add(name)
            continue
        out.append(e)
    return out, dropped


# Hosting direction. Both sides may match either order in the text; the
# canonical SOURCE is the software/service and the canonical TARGET is the
# hardware/platform. ``RUNS_ON`` is normalized to ``DEPLOYED_ON`` upstream
# in ``normalize_relation_type``, so only the canonical label appears here.
_HOSTING_REL_TYPES: frozenset[str] = frozenset({"DEPLOYED_ON"})


def _validate_hosting_direction(relationships: list[dict]) -> list[dict]:
    """For DEPLOYED_ON: software is source, hardware is target.

    If we see the hardware token on the source side, swap. We rely on the
    same hardware-token list as ``_snap_hardware_types`` so the rules stay
    coupled.
    """
    out = []
    for r in relationships:
        rtype = (r.get("type") or "").upper()
        if rtype not in _HOSTING_REL_TYPES:
            out.append(r)
            continue
        src_lower = (r.get("source") or "").strip().lower()
        tgt_lower = (r.get("target") or "").strip().lower()
        if src_lower in _HARDWARE_TOKENS and tgt_lower not in _HARDWARE_TOKENS:
            out.append({**r, "source": r["target"], "target": r["source"]})
        else:
            out.append(r)
    return out


def _dedup_entities(entities: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    names_added: set[str] = set()
    for e in sorted(entities, key=lambda x: -len(x.get("name", ""))):
        name = e["name"]
        if name in names_added:
            continue
        is_dup = False
        name_key = name.upper().replace(" ", "")
        for other in names_added:
            if name_key == other.upper().replace(" ", ""):
                is_dup = True
                break
            if _is_acronym_of(name, other) or _is_acronym_of(other, name):
                is_dup = True
                break
        if is_dup:
            continue
        names_added.add(name)
        deduped.append(e)
    return deduped


def _build_name_remap(original_entities: list[dict], valid_names: set[str]) -> dict[str, str]:
    remap: dict[str, str] = {}
    for e in original_entities:
        orig = (e.get("name") or "").strip()
        stripped = _TRAILING_SUFFIXES.sub("", orig)
        if stripped in valid_names:
            remap[orig] = stripped
        for vn in valid_names:
            if _is_acronym_of(orig, vn) or _is_acronym_of(stripped, vn):
                remap[orig] = vn
                break
    return remap


def _remap_relationships(
    relationships: list[dict],
    name_remap: dict[str, str],
    valid_names: set[str],
) -> list[dict]:
    out = []
    for r in relationships:
        src = name_remap.get(r.get("source", ""), r.get("source", ""))
        tgt = name_remap.get(r.get("target", ""), r.get("target", ""))
        if src in valid_names and tgt in valid_names and src != tgt:
            out.append({
                **r,
                "source": src,
                "target": tgt,
                "type": normalize_relation_type(r.get("type", "")),
            })
    return out


# ── Direction validation (Item 5) ───────────────────────────────────

_REPLACES_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"switched\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "target", "source"),
    (re.compile(r"migrated?\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "target", "source"),
    (re.compile(r"replaced?\s+(.+?)\s+with\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "target", "source"),
    (re.compile(r"replacing\s+(.+?)\s+with\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "target", "source"),
    (re.compile(r"chose\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "source", "target"),
    (re.compile(r"picked\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "source", "target"),
    (re.compile(r"went\s+with\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "source", "target"),
    (re.compile(r"decided\s+to\s+use\s+(.+?)\s+(?:instead\s+of|over)\s+(.+?)(?:\s+because\b|\s+since\b|\s+as\b|\s+for\b|[,;.]|$)", re.I), "source", "target"),
]

_IMPROVES_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"(.+?)\s+improves?\s+(?:on|upon|over)\s+(.+?)(?:\s+by\b|\s+because\b|[,;.]|$)", re.I), "source", "target"),
    (re.compile(r"(.+?)\s+is\s+better\s+than\s+(.+?)(?:\s+because\b|\s+since\b|[,;.]|$)", re.I), "source", "target"),
    (re.compile(r"(.+?)\s+builds?\s+on\s+(.+?)(?:\s+by\b|\s+because\b|[,;.]|$)", re.I), "source", "target"),
]


def _entity_matches(entity_name: str, text_fragment: str) -> bool:
    # Word-boundary match, not bare substring: 'postgres' must not match inside
    # 'postgres 17' when validating relation directions, which would make both
    # the expected and wrong-direction tests pass and trigger a spurious swap.
    if not entity_name:
        return False
    return re.search(rf"\b{re.escape(entity_name.lower())}\b", text_fragment.lower()) is not None


def _dedup_by_target_predicate(relationships: list[dict]) -> list[dict]:
    """Drop duplicate ``(target, predicate)`` relations that came from
    different sources, keeping the most reliable one.

    Two failure modes this fix catches:

    1. **Subject anchoring** — the LLM emits both the correct
       ``darkmem USES rrf`` (subject = project) and a spurious
       ``qwen3-embedding USES rrf`` (subject = neighbouring tool the
       model anchored to). Neither claims a pattern-grounded
       direction, so the tie-break falls through to weight and picks
       whichever the model was more confident in. This is the
       original motivation for the dedup.
    2. **Wrong-direction REPLACES** — the LLM emits
       ``darkmem REPLACES qdrant`` while the rescue layer's pattern
       extractor (``_rescue_relations_replaces``) emits
       ``pgvector REPLACES qdrant`` from the literal "from X to Y"
       phrasing, at a lower weight. ``_prefer_relation`` picks the
       pattern-grounded triple regardless of weight.

    The same logic applies generically to any direction-sensitive
    predicate where a rescue pass matches a *directional* pattern and
    the LLM emits a conflicting subject (IMPLEMENTS, EXTENDS,
    DEPLOYED_ON, etc.). It deliberately does not extend to the
    adjacency and subject-tracking rescues, whose subject is inferred
    from position and is the same guess failure mode 1 exists to
    correct.

    Self-loops are ignored (already dropped earlier). Entries missing
    source/target/type pass through unchanged.
    """
    by_key: dict[tuple[str, str], dict] = {}
    untouchable: list[dict] = []
    for r in relationships:
        target = (r.get("target") or "").strip().lower()
        rtype = (r.get("type") or "").strip().upper()
        if not target or not rtype or not r.get("source"):
            untouchable.append(r)
            continue
        key = (target, rtype)
        prev = by_key.get(key)
        if prev is None or _prefer_relation(r, prev):
            by_key[key] = r
    return list(by_key.values()) + untouchable


def _is_direction_grounded(relation: dict) -> bool:
    """True for a rescue triple whose DIRECTION came from a pattern.

    The three rescue emitters are not equally trustworthy about which
    endpoint is the source. ``_rescue_relations`` (adjacency) and
    ``_rescue_relations_subject_tracking`` ground *adjacency* and then
    infer the subject from position, so their direction is a guess.
    Only ``_rescue_relations_replaces`` matches a directional pattern
    ("from X to Y", "Y supersedes X") and stamps its label, and it is
    that pattern — not the rescue tag — that makes the triple's
    direction more reliable than the model's.
    """
    props = relation.get("properties") or {}
    return bool(props.get("rescue")) and bool(props.get("pattern"))


def _prefer_relation(candidate: dict, current: dict) -> bool:
    """Tie-break ordering for ``_dedup_by_target_predicate``.

    Order:

    1. A direction-grounded rescue triple beats one that is not. This is
       the wrong-direction-REPLACES fix: the LLM reads the sentence
       subject as the replacer and emits ``darkmem REPLACES qdrant``
       from "we migrated from qdrant to pgvector", while the pattern
       extractor reads the phrasing itself and emits
       ``pgvector REPLACES qdrant`` at a *lower* weight — so weight
       alone keeps the backwards edge, and a backwards ``REPLACES`` is
       what ``detect_supersessions`` acts on.
    2. Otherwise the higher-weight triple wins. Preserves the original
       subject-anchoring fix where two emissions disagree on the
       subject, including the case where one of them is an adjacency
       rescue whose subject is itself a guess.
    """
    cand_grounded = _is_direction_grounded(candidate)
    curr_grounded = _is_direction_grounded(current)
    if cand_grounded != curr_grounded:
        return cand_grounded and not curr_grounded
    return float(candidate.get("weight") or 0) > float(current.get("weight") or 0)


def _drop_uses_when_deployed_on_exists(relationships: list[dict]) -> list[dict]:
    """Drop ``A USES B`` when ``A DEPLOYED_ON B`` exists for the same pair.

    The phrasing "qwen3-embedding:0.6b on Ollama" produces ``qwen3 USES
    ollama`` from the LLM and ``qwen3 DEPLOYED_ON ollama`` from the rescue
    layer's adjacency pass. Both are valid readings, but DEPLOYED_ON is
    the more specific predicate — it strictly implies USES — so the USES
    edge is redundant. Keeping both clutters the graph and inflates
    relationship counts without adding signal.

    Pair match is direction-sensitive: only collapse when source and
    target match exactly. ``A USES B`` + ``B DEPLOYED_ON A`` (reversed
    pair) is left alone because that describes a host using its own
    deployed service, which is a legitimate distinct relationship.
    """
    deployed_pairs: set[tuple[str, str]] = set()
    for r in relationships:
        if (r.get("type") or "").strip().upper() != "DEPLOYED_ON":
            continue
        src = (r.get("source") or "").strip().lower()
        tgt = (r.get("target") or "").strip().lower()
        if src and tgt:
            deployed_pairs.add((src, tgt))

    if not deployed_pairs:
        return relationships

    out: list[dict] = []
    for r in relationships:
        if (r.get("type") or "").strip().upper() == "USES":
            src = (r.get("source") or "").strip().lower()
            tgt = (r.get("target") or "").strip().lower()
            if (src, tgt) in deployed_pairs:
                continue
        out.append(r)
    return out


def _drop_uses_when_replaces_exists(relationships: list[dict]) -> list[dict]:
    """Drop USES between a pair that already has a REPLACES (any direction).

    The text "X was deprecated and we replaced it with Y" reliably produces
    the correct ``Y --REPLACES--> X`` plus a noisy ``X --USES--> Y`` from
    the rescue layer's ``with`` connector treating X as the implicit
    subject. Sometimes the LLM emits the same noisy edge directly.
    REPLACES (which collapses with IMPROVES_ON in the 5-type schema)
    already conveys the relationship, so an additional USES is semantic
    duplication and is often inverted. We compare on the unordered pair
    to catch both directions without making assumptions about which
    edge is in the right direction.
    """
    replaces_pairs: set[frozenset[str]] = set()
    for r in relationships:
        rtype = (r.get("type") or "").upper()
        if rtype not in REPLACES_FAMILY:
            continue
        src = (r.get("source") or "").strip().lower()
        tgt = (r.get("target") or "").strip().lower()
        if src and tgt and src != tgt:
            replaces_pairs.add(frozenset({src, tgt}))

    if not replaces_pairs:
        return relationships

    out: list[dict] = []
    for r in relationships:
        rtype = (r.get("type") or "").upper()
        if rtype == "USES":
            src = (r.get("source") or "").strip().lower()
            tgt = (r.get("target") or "").strip().lower()
            # Intentional pair-based (direction-agnostic) dedup: a REPLACES on the
            # same unordered pair already conveys the relationship, so the USES is
            # dropped in either direction. See
            # test_drop_uses_when_replaces_present_reverse_direction — the rare
            # "both edges genuinely distinct" case is a deliberately accepted
            # trade-off, not a bug.
            if src and tgt and frozenset({src, tgt}) in replaces_pairs:
                continue
        out.append(r)
    return out


def _validate_directions(relationships: list[dict], content: str) -> list[dict]:
    out = []
    for rel in relationships:
        r = dict(rel)
        rel_type = r.get("type", "")
        src = r.get("source", "")
        tgt = r.get("target", "")

        if rel_type == "REPLACES":
            patterns = _REPLACES_PATTERNS
        elif rel_type == "IMPROVES_ON":
            patterns = _IMPROVES_PATTERNS
        else:
            out.append(r)
            continue

        for pattern, first_role, second_role in patterns:
            match = pattern.search(content)
            if not match:
                continue
            first_text = match.group(1).strip()
            second_text = match.group(2).strip()

            if first_role == "source":
                expected_src, expected_tgt = first_text, second_text
            else:
                expected_src, expected_tgt = second_text, first_text

            src_matches_expected = _entity_matches(src, expected_src)
            tgt_matches_expected = _entity_matches(tgt, expected_tgt)
            src_matches_wrong = _entity_matches(src, expected_tgt)
            tgt_matches_wrong = _entity_matches(tgt, expected_src)

            if src_matches_expected and tgt_matches_expected:
                break
            # Only swap on an UNAMBIGUOUS wrong-direction match: both endpoints
            # match their swapped roles and neither matches its expected role.
            if (
                src_matches_wrong
                and tgt_matches_wrong
                and not src_matches_expected
                and not tgt_matches_expected
            ):
                r["source"], r["target"] = tgt, src
                break

        out.append(r)
    return out


# ── Main cleanup orchestrator ────────────────────────────────────────


_IP_LITERAL_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?$")
# Generic config-path stems the LLM splits out of dotted/snake keys
# (``client.backoff`` -> ``client``). Dropped only when they appear in dotted
# form in the content, so a real entity named the same word still survives.
_CONFIG_STEMS = frozenset({
    "client", "limits", "server", "config", "settings", "options", "params",
    "hooks", "env", "logs", "log", "cache", "queue", "pool", "app", "auth",
})


def _filter_literals(entities: list[dict], content: str) -> list[dict]:
    """Drop IP/port literals and dotted config-key stems that are not entities."""
    low = content.lower()
    out = []
    for e in entities:
        n = (e.get("name") or "").strip()
        nl = n.lower()
        if _IP_LITERAL_RE.match(n):
            continue
        if nl in _CONFIG_STEMS and (nl + ".") in low:
            continue
        # Generalized dotted config-key stem: drop a single-token entity that is
        # the leading segment of a 2+-dot config path in the text
        # ('producer.linger.ms' -> 'producer'). Single-dot forms (module.attr,
        # github.com, redis.conf) are left alone so 'asyncio.create_task' still
        # collapses to the legitimate 'asyncio' root.
        if nl and " " not in nl:
            has_dotted = re.search(r"(?<![\w.])" + re.escape(nl) + r"\.\w+\.\w", low) is not None
            # A bare standalone mention (word-boundary, not a dotted continuation)
            # means it's a real entity, not just a config-key stem — only drop
            # when EVERY mention is the leading segment of a dotted path.
            has_bare = re.search(r"\b" + re.escape(nl) + r"\b(?!\.\w)", low) is not None
            if has_dotted and not has_bare:
                continue
        out.append(e)
    return out


_FIDELITY_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "of", "for", "with", "from", "into", "over",
    "to", "in", "on", "at", "by", "our", "your", "its", "this", "that", "new", "old",
})


def _filter_hallucinated_names(entities: list[dict], content: str) -> list[dict]:
    """Value-fidelity guard: drop entities whose text is not grounded in the
    source. Only police MULTI-word phrases (a single token may be a canonical
    short form, e.g. 'postgres' from 'PostgreSQL') and standalone dates (a date
    value absent from the text is a fabrication, e.g. a stored '2026-05-12' when
    the source says '2026-05-20'). Catches non-deterministic LLM value
    hallucinations ('February outage' emitted as 'March outage'). Edges to
    dropped entities are removed downstream by ``_remap_relationships``."""
    if not content:
        return entities
    low = content.lower()

    def _present(tok: str) -> bool:
        return tok in low or (tok.endswith("s") and tok[:-1] in low) or (tok + "s") in low

    out = []
    for e in entities:
        nl = (e.get("name") or "").strip().lower()
        if not nl:
            continue
        if _DATE_ONLY_RE.fullmatch(nl) and nl not in low:
            continue
        toks = [re.sub(r"[^\w]", "", t) for t in re.split(r"[\s/]+", nl)]
        sig = [t for t in toks if len(t) >= 3 and t not in _FIDELITY_STOPWORDS]
        if len(sig) >= 2 and not all(_present(t) for t in sig):
            continue
        out.append(e)
    return out


_DATE_ISO_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _rescue_happened_on(
    entities: list[dict], relationships: list[dict], content: str
) -> tuple[list[dict], list[dict]]:
    """Keep ISO dates alive for HAPPENED_ON. ``_filter_noise`` strips dates as
    values, which orphans a correct LLM ``X HAPPENED_ON <date>`` edge, and the
    LLM also frequently drops the relation entirely (most-missed relation)."""
    dates_in_content = set(_DATE_ISO_RE.findall(content))
    if not dates_in_content:
        return entities, relationships
    out_e, out_r = list(entities), list(relationships)
    names = {(e.get("name") or "") for e in out_e}
    # 1) Re-add a date entity the value-filter stripped but an existing
    #    HAPPENED_ON edge still points at.
    for r in relationships:
        t = r.get("target") or ""
        if r.get("type") == "HAPPENED_ON" and t in dates_in_content and t not in names:
            out_e.append({"name": t, "type": "concept", "properties": {}})
            names.add(t)
    # 2) Anchor dates the LLM left unlinked to the nearest preceding
    #    event/release/service entity.
    low = content.lower()
    anchorable = {"event", "service", "artifact", "project", "milestone"}
    spots = [(low.find((e.get("name") or "").lower()), e.get("name"))
             for e in entities if e.get("type") in anchorable]
    spots = [(p, n) for p, n in spots if p >= 0]
    linked = {r.get("target") for r in out_r if r.get("type") == "HAPPENED_ON"}
    for m in _DATE_ISO_RE.finditer(content):
        d, dpos = m.group(1), m.start()
        if d in linked or not spots:
            continue
        cands = sorted((dpos - p, n) for p, n in spots if 0 <= dpos - p <= 90)
        if not cands:
            continue
        subj = cands[0][1]
        if d not in names:
            out_e.append({"name": d, "type": "concept", "properties": {}})
            names.add(d)
        out_r.append({"source": subj, "target": d, "type": "HAPPENED_ON", "weight": 0.7, "properties": {}})
        linked.add(d)
    return out_e, out_r


_SELECTION_RE = re.compile(
    r"\b(chose|choose|chosen|pick(?:ed)?|select(?:ed)?|went with|going with|opt(?:ed)?\s+for|prefer(?:red)?)\b.*?\b(over|instead of|rather than|versus|vs\.?)\b",
    re.IGNORECASE | re.DOTALL,
)
_MIGRATION_RE = re.compile(
    r"\b(replac\w+|switch\w*|migrat\w+|moved\s+(?:from|off|out)|superseded?|swapped|ported\s+(?:from|to))\b",
    re.IGNORECASE,
)


def _gate_replaces_selection(relationships: list[dict], content: str) -> list[dict]:
    """A pure selection ('chose X over Y') is IMPROVES_ON, not REPLACES — the
    latter triggers supersession and must be reserved for real migrations."""
    if not _SELECTION_RE.search(content) or _MIGRATION_RE.search(content):
        return relationships
    return [
        {**r, "type": "IMPROVES_ON"} if r.get("type") == "REPLACES" else r
        for r in relationships
    ]


# Any verb/phrase that legitimately backs a REPLACES (migration, supersession,
# or improvement-family). REPLACES with NONE of these in the text is unsupported.
_REPLACE_EVIDENCE_RE = re.compile(
    r"\b(?:replac\w+|switch\w*|migrat\w+|moved\s+(?:from|off|out)|supersed\w+"
    r"|deprecat\w+|obsolete\w*|swapped|ported|improves?\s+(?:on|upon|over)"
    r"|builds?\s+on|instead\s+of|in\s+favou?r\s+of|phas\w+\s+out)\b",
    re.IGNORECASE,
)


def _gate_replaces_requires_verb(relationships: list[dict], content: str) -> list[dict]:
    """A REPLACES edge must be backed by a replacement/migration verb in the
    text. The LLM sometimes emits REPLACES from a bare rewrite/negation sentence
    ('all writes now go through the event bus' -> 'event bus REPLACES legacy
    ledger') with no such verb, which carries false-supersession risk. Downgrade
    those unsupported edges to RELATED_TO."""
    if _REPLACE_EVIDENCE_RE.search(content):
        return relationships
    return [
        {**r, "type": "RELATED_TO"} if r.get("type") == "REPLACES" else r
        for r in relationships
    ]


_TEMPORAL_BETWEEN_RE = re.compile(r"\b(after|before|since|following|prior to|then|once|later)\b", re.IGNORECASE)
_CAUSAL_BETWEEN_RE = re.compile(r"\b(caus\w*|led to|result\w*|trigger\w*|because|due to|produc\w*)\b", re.IGNORECASE)


def _suppress_temporal_edges(relationships: list[dict], content: str) -> list[dict]:
    """Drop RELATED_TO / CAUSES edges whose two endpoints are joined in the text
    only by a temporal connector ('after the outage') with no causal verb."""
    low = content.lower()
    out = []
    for r in relationships:
        if r.get("type") in ("RELATED_TO", "CAUSES"):
            s, t = (r.get("source") or "").lower(), (r.get("target") or "").lower()
            if s and t:
                # Evaluate the guard on the CLOSEST s/t mention pair, not the
                # first occurrence of each: a name that recurs (common for the
                # project/service subject) would otherwise span an unrelated
                # mention window and suppress a legitimate edge.
                s_spans = [m.span() for m in re.finditer(re.escape(s), low)]
                t_spans = [m.span() for m in re.finditer(re.escape(t), low)]
                best: tuple[int, int, int] | None = None
                for ss in s_spans:
                    for ts in t_spans:
                        a, b = (ss[1], ts[0]) if ss[0] < ts[0] else (ts[1], ss[0])
                        if a <= b and (best is None or (b - a) < best[0]):
                            best = (b - a, a, b)
                if best is not None:
                    between = low[best[1]:best[2]]
                    if _TEMPORAL_BETWEEN_RE.search(between) and not _CAUSAL_BETWEEN_RE.search(between):
                        continue
        out.append(r)
    return out


_FUTURE_RE = re.compile(
    r"\b(plan(?:s|ned|ning)?\s+to|will\s+(?:add|support|build|introduce|ship)|going\s+to|intend(?:s|ed)?\s+to|upcoming|on\s+the\s+roadmap|considering|may\s+add|to\s+be\s+added)\b",
    re.IGNORECASE,
)


def _downgrade_future_to_mentions(relationships: list[dict], content: str) -> list[dict]:
    """Future/planned things are MENTIONS, not USES/IMPLEMENTS/etc."""
    m = _FUTURE_RE.search(content)
    if not m:
        return relationships
    future_zone = content.lower()[m.start():]
    out = []
    for r in relationships:
        if r.get("type") in ("USES", "IMPLEMENTS", "EXTENDS", "DEPENDS_ON") and (r.get("target") or "").lower() in future_zone:
            out.append({**r, "type": "MENTIONS", "weight": min(r.get("weight", 0.5), 0.5)})
        else:
            out.append(r)
    return out


# Connector between two coordinated entity mentions: comma / "and" / semicolon,
# optionally followed by an article ("dashboard, the admin console, and the ...").
_DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _drop_date_misuse(relationships: list[dict]) -> list[dict]:
    """A date can only be a HAPPENED_ON target. Drop any other edge that has an
    ISO date as an endpoint ('X DEPLOYED_ON <date>', '<date> AUTHORED_BY Y')."""
    out = []
    for r in relationships:
        if r.get("type") != "HAPPENED_ON":
            s, t = r.get("source") or "", r.get("target") or ""
            if _DATE_ONLY_RE.fullmatch(s.strip()) or _DATE_ONLY_RE.fullmatch(t.strip()):
                continue
        out.append(r)
    return out


# comma or "and" (+ optional article). ';' separates clauses, not subjects.
_COORD_CONN_RE = re.compile(r"^\s*(?:,\s*(?:and\s+)?|and\s+)(?:the\s+|a\s+|an\s+)?$")


def _fan_out_coordinated(
    relationships: list[dict], entities: list[dict], content: str
) -> list[dict]:
    """When a relation's subject is one of a coordinated set ('A, B, and C all
    use X'), replicate the predicate-object edge across every conjunct subject.
    Runs LAST so _dedup_by_target_predicate doesn't collapse the multi-source set."""
    name_by_lower = {(e.get("name") or "").lower(): e.get("name") for e in entities}
    if len(name_by_lower) < 2:
        return relationships
    low = content.lower()
    ordered = sorted((n for n in name_by_lower if n), key=len, reverse=True)
    name_re = re.compile("(?:" + "|".join(re.escape(n) for n in ordered) + r")")
    matches = list(name_re.finditer(low))
    groups: list[set[str]] = []
    i = 0
    while i < len(matches):
        group = [matches[i].group()]
        end = matches[i].end()
        j = i + 1
        while j < len(matches) and _COORD_CONN_RE.match(low[end:matches[j].start()]):
            group.append(matches[j].group())
            end = matches[j].end()
            j += 1
        if len(group) >= 2:
            groups.append(set(group))
        i = j if j > i + 1 else i + 1
    if not groups:
        return relationships
    existing = {((r.get("source") or "").lower(), r.get("type"), (r.get("target") or "").lower()) for r in relationships}
    out = list(relationships)
    for r in list(relationships):
        s, t = (r.get("source") or "").lower(), (r.get("target") or "").lower()
        for g in groups:
            if s in g and t not in g:
                # sorted, not the set's own iteration order: string hash
                # randomisation would otherwise make the emission ORDER of a
                # coordinated group differ between processes, which breaks
                # the reproducibility contract from the opposite end to the
                # one the LLM seed protects.
                for member in sorted(g):
                    if member == s or _DATE_ONLY_RE.fullmatch(member):
                        continue
                    key = (member, r.get("type"), t)
                    if key not in existing:
                        out.append({**r, "source": name_by_lower.get(member, member)})
                        existing.add(key)
    return out


# An `event` entity (outage, incident, release, migration) is a passive temporal
# node, not a software agent or dependency. These are the ONLY relation types an
# event may be an endpoint of. Enforces prompt rule 16a, which this extraction
# model does not reliably follow on its own (it emits 'incident USES disk',
# 'incident DEPLOYED_ON node'). Keyed on the entity TYPE, not on any name — holds
# for every future event.
_EVENT_ALLOWED_RELS: frozenset[str] = frozenset({
    "HAPPENED_ON", "CAUSES", "AUTHORED_BY", "MENTIONS",
})


def _drop_unlinked_dates(entities: list[dict], relationships: list[dict]) -> list[dict]:
    """A date entity exists ONLY to be a HAPPENED_ON target (taxonomy: a date is
    never a standalone node). If no HAPPENED_ON edge points at it — e.g. the event
    subject was never extracted, so _rescue_happened_on had nothing to anchor to —
    it is a dangling value node; drop it. General, keyed on the date shape."""
    happened_targets = {
        (r.get("target") or "").strip().lower()
        for r in relationships if (r.get("type") or "").upper() == "HAPPENED_ON"
    }
    return [
        e for e in entities
        if not (
            _DATE_ONLY_RE.fullmatch((e.get("name") or "").strip().lower())
            and (e.get("name") or "").strip().lower() not in happened_targets
        )
    ]


def _filter_event_edges(relationships: list[dict], entities: list[dict]) -> list[dict]:
    """Drop any edge with an `event`-typed endpoint whose relation type is not in
    the event-legal set. General structural guard, not an ad-hoc carve-out."""
    events = {
        (e.get("name") or "").strip().lower()
        for e in entities if e.get("type") == "event"
    }
    if not events:
        return relationships
    out = []
    for r in relationships:
        s = (r.get("source") or "").strip().lower()
        t = (r.get("target") or "").strip().lower()
        if (s in events or t in events) and (r.get("type") or "").upper() not in _EVENT_ALLOWED_RELS:
            continue
        out.append(r)
    return out


def _remap_to_valid_entities(
    relationships: list[dict], entities: list[dict], raw_entities: list[dict],
) -> list[dict]:
    """Rewrite every edge endpoint onto a surviving entity, dropping the rest."""
    valid_names = {e["name"] for e in entities}
    name_remap = _build_name_remap(raw_entities, valid_names)
    return _remap_relationships(relationships, name_remap, valid_names)


def _drop_edges_to_negated(
    relationships: list[dict], negated_names: Collection[str],
) -> list[dict]:
    """Drop relations that reference an entity removed for being negation-only."""
    if not negated_names:
        return relationships
    return [
        r for r in relationships
        if r.get("source") not in negated_names and r.get("target") not in negated_names
    ]


STAGE_ENTITY_SHAPING = "entity_shaping"
STAGE_ENTITY_RESCUE = "entity_rescue"
STAGE_RELATION_SYNTHESIS = "relation_synthesis"
STAGE_RELATION_GATING = "relation_gating"
STAGE_COLLAPSE_AND_FANOUT = "collapse_and_fanout"


# The post-processor, as an explicit ordered sequence. One line per pass;
# reordering, dropping, or inserting a pass is a one-line edit whose effect
# the F1 bench measures. Every entry is a pure function with no hidden state.
PASS_REGISTRY: tuple[Pass, ...] = (
    Pass("normalize_names", STAGE_ENTITY_SHAPING, _normalize_names, ("entities",), ("entities",)),
    Pass("filter_noise", STAGE_ENTITY_SHAPING, _filter_noise, ("entities",), ("entities",)),
    Pass("filter_literals", STAGE_ENTITY_SHAPING, _filter_literals, ("entities", "content"), ("entities",)),
    Pass("snap_hardware_types", STAGE_ENTITY_SHAPING, _snap_hardware_types, ("entities",), ("entities",)),
    Pass("apply_type_overrides", STAGE_ENTITY_SHAPING, _apply_type_overrides, ("entities",), ("entities",)),
    Pass("filter_hallucinated_names", STAGE_ENTITY_SHAPING, _filter_hallucinated_names, ("entities", "content"), ("entities",)),
    Pass("filter_negation_only", STAGE_ENTITY_SHAPING, _filter_negation_only, ("entities", "content"), ("entities", "negated_names")),
    Pass("dedup_entities", STAGE_ENTITY_SHAPING, _dedup_entities, ("entities",), ("entities",)),
    # Rescue runs AFTER dedup so canonical short names (``cpu``, ``rg``) are
    # not dropped as substrings of longer model proposals (``cpu_fallback``).
    #
    # Endpoint rescue leads the stage: it reinstates names the model itself
    # asserted, so the passes after it see the model's complete claim set —
    # ``rescue_known_entities`` builds its span guard from the entity list and
    # ``rescue_happened_on`` picks its date anchor from it.
    Pass("rescue_relation_endpoints", STAGE_ENTITY_RESCUE, _rescue_relation_endpoints, ("entities", "relationships", "content"), ("entities",)),
    Pass("rescue_known_entities", STAGE_ENTITY_RESCUE, _rescue_known_entities, ("entities", "content"), ("entities",)),
    # File-path rescue: scans for ``a/b/c.py``-style tokens the LLM
    # dropped and adds them as ``artifact`` entities. Closes the
    # round-10 recall gap that broke Pattern D's B-zone selection on
    # relocation memories. Plain dotted forms (``classA.method1()``)
    # are intentionally NOT matched — see ``_FILE_PATH_RE`` docstring.
    Pass("rescue_file_path_entities", STAGE_ENTITY_RESCUE, _rescue_file_path_entities, ("entities", "content"), ("entities",)),
    # Attach ISO dates to their event/release entity (HAPPENED_ON) before
    # ``valid_names`` is computed, so the date node + edge survive remap.
    Pass("rescue_happened_on", STAGE_ENTITY_RESCUE, _rescue_happened_on, ("entities", "relationships", "content"), ("entities", "relationships")),
    # Pattern-based relation synthesis, doc 06 §4's Stage 3 — three passes
    # in the order the doc declares them. They add DEPLOYED_ON / USES /
    # REPLACES triples the LLM missed, and run before remap/direction/
    # collapse so the synthetic triples go through the same downstream
    # cleanup as LLM-emitted ones. Each is skipped when ``relation_rescue``
    # is False; the model's raw triples still go through the cleanup below.
    #
    # The adjacency pass leads: it and the subject-tracking pass can both
    # reach the same (source, target, USES) key, and the first emitter of a
    # key wins it — so the order decides which weight and which properties
    # the surviving triple carries into ``dedup_by_target_predicate``.
    Pass("rescue_relations", STAGE_RELATION_SYNTHESIS, _rescue_relations, ("entities", "relationships", "content"), ("relationships",), gate="relation_rescue"),
    Pass("rescue_relations_subject_tracking", STAGE_RELATION_SYNTHESIS, _rescue_relations_subject_tracking, ("entities", "relationships", "content"), ("relationships",), gate="relation_rescue"),
    Pass("rescue_relations_replaces", STAGE_RELATION_SYNTHESIS, _rescue_relations_replaces, ("entities", "relationships", "content"), ("relationships",), gate="relation_rescue"),
    Pass("remap_to_valid_entities", STAGE_RELATION_GATING, _remap_to_valid_entities, ("relationships", "entities", "raw_entities"), ("relationships",)),
    Pass("drop_edges_to_negated", STAGE_RELATION_GATING, _drop_edges_to_negated, ("relationships", "negated_names"), ("relationships",)),
    # Reserve REPLACES for real migrations; a selection ('chose X over Y') is
    # IMPROVES_ON. Drop edges joined only by a temporal connector. Future/planned
    # references are MENTIONS, not USES.
    Pass("gate_replaces_selection", STAGE_RELATION_GATING, _gate_replaces_selection, ("relationships", "content"), ("relationships",)),
    Pass("gate_replaces_requires_verb", STAGE_RELATION_GATING, _gate_replaces_requires_verb, ("relationships", "content"), ("relationships",)),
    Pass("suppress_temporal_edges", STAGE_RELATION_GATING, _suppress_temporal_edges, ("relationships", "content"), ("relationships",)),
    Pass("downgrade_future_to_mentions", STAGE_RELATION_GATING, _downgrade_future_to_mentions, ("relationships", "content"), ("relationships",)),
    Pass("drop_date_misuse", STAGE_RELATION_GATING, _drop_date_misuse, ("relationships",), ("relationships",)),
    Pass("validate_directions", STAGE_RELATION_GATING, _validate_directions, ("relationships", "content"), ("relationships",)),
    Pass("validate_hosting_direction", STAGE_RELATION_GATING, _validate_hosting_direction, ("relationships",), ("relationships",)),
    # Events are passive temporal nodes: strip any non-temporal/causal edge the
    # model hung off an incident/outage/release (rule 16a; model under-complies).
    Pass("filter_event_edges", STAGE_RELATION_GATING, _filter_event_edges, ("relationships", "entities"), ("relationships",)),
    # Suppress USES between a pair already covered by REPLACES (any
    # direction). Runs after the direction validators so the REPLACES
    # is in the right shape, and before the 10->5 collapse so we still
    # see IMPROVES_ON as part of the REPLACES family.
    Pass("drop_uses_when_replaces_exists", STAGE_COLLAPSE_AND_FANOUT, _drop_uses_when_replaces_exists, ("relationships",), ("relationships",)),
    # Same idea for hosting: when a pair already has DEPLOYED_ON, the
    # parallel USES edge is redundant (DEPLOYED_ON ⊂ USES semantically).
    Pass("drop_uses_when_deployed_on_exists", STAGE_COLLAPSE_AND_FANOUT, _drop_uses_when_deployed_on_exists, ("relationships",), ("relationships",)),
    # Cross-source dedup: when a (target, predicate) appears with two
    # different sources, keep the highest-weight one. Catches the
    # subject-tracking failure where the extractor anchors a relation
    # to the most-recent technology entity in addition to (or instead
    # of) the correct project subject.
    Pass("dedup_by_target_predicate", STAGE_COLLAPSE_AND_FANOUT, _dedup_by_target_predicate, ("relationships",), ("relationships",)),
    Pass("fan_out_coordinated", STAGE_COLLAPSE_AND_FANOUT, _fan_out_coordinated, ("relationships", "entities", "content"), ("relationships",)),
    Pass("filter_event_edges", STAGE_COLLAPSE_AND_FANOUT, _filter_event_edges, ("relationships", "entities"), ("relationships",)),
    # Drop any date entity left without a HAPPENED_ON edge (dangling value node).
    Pass("drop_unlinked_dates", STAGE_COLLAPSE_AND_FANOUT, _drop_unlinked_dates, ("entities", "relationships"), ("entities",)),
)


# The three orderings doc 06 §4 calls load-bearing. Declared as data and
# checked at import time so a reorder fails loudly instead of silently
# costing F1.
ORDERING_CONSTRAINTS: tuple[OrderingConstraint, ...] = (
    RunsBefore(
        "dedup_entities", "rescue_known_entities",
        why=(
            "rescue after dedup keeps canonical short names ('cpu', 'rg') that "
            "dedup would otherwise drop against a longer model proposal"
        ),
    ),
    RunsBefore(
        "dedup_entities", "rescue_relation_endpoints",
        why=(
            "the same whitespace-collapse equality that would drop a rescued "
            "short name would drop a rescued edge endpoint ('web app' against "
            "a model-listed 'webapp')"
        ),
    ),
    RunsBefore(
        "rescue_relation_endpoints", "remap_to_valid_entities",
        why=(
            "the remap deletes every edge whose endpoint is not a valid "
            "entity, which is the loss the endpoint rescue exists to prevent"
        ),
    ),
    RunsBefore(
        "dedup_by_target_predicate", "fan_out_coordinated",
        why=(
            "fan-out deliberately mints a multi-source set for one "
            "(target, predicate) that the dedup would collapse back to one edge"
        ),
    ),
    RunsBefore(
        "remap_to_valid_entities", "drop_edges_to_negated",
        why=(
            "``negated_names`` holds SHAPED names while an edge endpoint is "
            "still the model's raw string until the remap rewrites it, so a "
            "pre-remap negation check compares two vocabularies that only "
            "coincide by luck and lets an edge to a denied entity through"
        ),
    ),
    RunsBefore(
        "remap_to_valid_entities", "suppress_temporal_edges",
        why=(
            "every gate from here on keys on endpoint NAMES against the "
            "content; before the remap those names are the model's raw "
            "strings, so the span search finds no mention and the gate "
            "silently declines to fire"
        ),
    ),
    RunsBefore(
        "gate_replaces_selection", "gate_replaces_requires_verb",
        why=(
            "a selection ('chose X over Y') carries no replacement verb, so "
            "the verb gate would collapse it to RELATED_TO before the "
            "selection gate ever sees a REPLACES to reclassify as IMPROVES_ON"
        ),
    ),
    StraddlesPivot(
        "filter_event_edges", "fan_out_coordinated",
        why=(
            "fan-out can mint an edge with an event-typed endpoint that the "
            "first event-legality pass never saw"
        ),
    ),
)

validate_registry(PASS_REGISTRY, ORDERING_CONSTRAINTS)


def clean_extraction(
    result: dict,
    content: str = "",
    *,
    relation_rescue: bool = True,
) -> dict:
    """Normalize and post-process raw extraction output.

    Runs ``PASS_REGISTRY`` in order; every pass is deterministic and
    in-process, so the whole chain makes zero model calls.

    ``relation_rescue`` toggles the pattern-based relation synthesis pass
    (adjacency + subject-tracking + REPLACES). Defaults to ``True`` so
    existing call sites and tests behave unchanged. Pipeline call sites
    pass the live ``relation_rescue`` feature flag.
    """
    raw_entities = result.get("entities", [])
    state = run_passes(
        PASS_REGISTRY,
        CleanState(
            content=content,
            entities=raw_entities,
            relationships=result.get("relationships", []),
            raw_entities=raw_entities,
            relation_rescue=relation_rescue,
        ),
    )

    return {
        **result,
        "entities": state.entities,
        "relationships": state.relationships,
    }
