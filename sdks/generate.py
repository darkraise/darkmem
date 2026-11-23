#!/usr/bin/env python
"""The SDK generator (doc 15 §6) — T3.25's scaffold, T3.14's bodies.

**Generated, not hand-written, and that is the invariant rather than a
convenience.** Doc 15 §6: keeping the SDK generated from doc 12's contract "is
what guarantees the SDK never drifts from the two front doors … it enforces
invariant 17 (the SDK cannot expose a behaviour the contract does not)". So the
generator reads the *live* OpenAPI document off the running app object — the
same schema the app serves — rather than a checked-in copy that could age.

**Two verbs, deliberately** — `capture` and `search`. darkmem is not building
a client platform; doc 00 §8's success criterion is that a minimal SDK exists.
Each verb is bound to the contract surface it wraps and generation **fails** if
that surface is absent.

**The guard has been widened twice, each time by a defect it could not see.**

1. *Route-deep* (T3.25). It asked only whether a path and method exist. Both
   emitted clients passed while posting an ``applies_when`` key that no request
   schema in the contract has — pydantic ignores an unknown key, so the field
   was dropped by the door with nothing said.
2. *Field-deep* (T3.14). Each verb names the request-body fields it sends and
   generation refuses when the contract's request schema lacks one. A review
   drill then showed the tuple was checked while the *emitted body* was not: an
   extra key added to a template, with the tuple untouched, generated cleanly.
   So the body literals are no longer written by hand at all — ``_body``
   renders them from the same tuple the guard checks, which makes the two
   impossible to separate.

There was a third verb, ``declareContext``, sending doc 12 §5's declared
context as a header. The owner removed declared context from both doors
(2026-11-23), so the verb, its header and the ``context`` search argument are
gone, and the generator's refusal of a field the contract does not serve is
what keeps them gone.

**Contract bindings, and why each is where it is:**

- ``capture`` → ``POST /api/v1/memories``. Doc 15 §6's
  ``capture(content, project?, context?, source?)`` names a ``context``
  argument ``MemoryCreate`` does not have, and doc 15 §6 itself says "doc 12
  owns the wire shape", so the contract wins and the argument is absent.
- ``search`` → ``POST /api/v1/memories/search/paginated``. Doc 01 F3 is the
  memory retrieval flow returning "ranked results with a 'why retrieved'
  trace", and doc 15 §6's own mermaid names the memories twin
  (``POST .../search · memory_search``); this door returns the trace envelope
  with ``with_trace``. Doc 15 §6's ``fused?`` argument is served only by the
  composed read (``POST /api/v1/knowledge/search``), so it is **not**
  expressible here — recorded rather than faked.

**What the SDK deliberately cannot express.** Ratification, review and vault
administration are absent. Doc 15 §6's reason is that they are
human-authenticated single-door acts; note that this client speaks only REST
and every door it can reach is behind ``require_auth``, so what keeps ratify
out of *this* client is the surface it is given, not the absence of auth.
Absence is asserted, not reviewed — ``sdks/python/tests/test_surface.py`` reads
both generated files and checks the public surface *is* the two verbs.

**Output is deterministic.** No timestamps, no versions read from the
environment, sorted everywhere — because ``make generate && git diff
--exit-code`` is the task's own verification, and a generator whose output
moves on every run cannot be checked that way. The contract hash *is* recorded,
since a regeneration that changes nothing but the hash is exactly the signal a
reader wants when the contract moved.

Run from ``sdks/``::

    make generate
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SDKS = Path(__file__).resolve().parent
sys.path.insert(0, str(SDKS.parent / "backend"))

# The two verbs, each pinned to the contract surface it wraps, down to the
# request-body fields it sends. `fields` is the single source for both the
# guard and the emitted body literal — see `_body`.
VERBS = {
    "capture": {
        "method": "post",
        "path": "/api/v1/memories",
        "fields": ("content", "project", "source"),
    },
    "search": {
        "method": "post",
        "path": "/api/v1/memories/search/paginated",
        "fields": ("query", "project", "limit", "with_trace"),
    },
}


def contract() -> dict:
    from app.main import app  # imported late: it pulls the whole application in

    return app.openapi()


def _request_properties(schema: dict, verb: dict) -> dict:
    """The request-body properties the contract declares for a bound route.

    Returns ``{}`` when the operation has no JSON request body, which
    ``_require_contract`` reports as every named field missing — a verb that
    sends fields to a door taking none is drift, not an empty success.
    """
    operation = schema["paths"][verb["path"]][verb["method"]]
    body = (
        operation.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    ref = body.get("$ref")
    if ref:
        body = schema.get("components", {}).get("schemas", {}).get(
            ref.rsplit("/", 1)[-1], {}
        )
    return body.get("properties", {})


def _require_contract(schema: dict) -> None:
    """Refuse to generate unless every verb's whole binding is served.

    Two failures, one message, because they are one defect: the SDK claims a
    surface the contract does not have.
    """
    missing: list[str] = []
    for name, verb in sorted(VERBS.items()):
        if verb["method"] not in schema["paths"].get(verb["path"], {}):
            missing.append(f"{name} → {verb['method'].upper()} {verb['path']}")
            continue
        properties = _request_properties(schema, verb)
        for field in verb["fields"]:
            if field not in properties:
                missing.append(f"{name} → {verb['path']} has no field {field!r}")

    if missing:
        raise SystemExit(
            "refusing to generate: the contract does not serve "
            + ", ".join(missing)
            + ". An SDK that names a surface the contract lacks is the drift "
            "doc 15 §6 generates the SDK to prevent."
        )


def _hash(schema: dict) -> str:
    """A stable digest of the contract surface the SDK actually binds to.

    Not of the whole document: the SDK is two verbs, and hashing all 116
    paths would report a change every time an unrelated route moved, training
    a reader to ignore it.
    """
    bound: dict[str, object] = {}
    for verb in VERBS.values():
        properties = _request_properties(schema, verb)
        bound[f"{verb['method']} {verb['path']}"] = {
            "operation": schema["paths"][verb["path"]][verb["method"]],
            "fields": {field: properties.get(field) for field in verb["fields"]},
        }
    return hashlib.sha256(
        json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


# Per-language expressions for each wire field, keyed by the *contract's* field
# name so the guard and the emitted literal cannot drift: `_body` renders one
# line per declared field and refuses a field it has no expression for, which
# is what makes "the tuple says one thing, the body posts another" unwritable.
TS_EXPRESSIONS = {
    "content": "content",
    "project": "options.project ?? this.#project",
    "source": "options.source",
    "query": "query",
    "limit": "options.limit",
    "with_trace": "true",
}

PY_EXPRESSIONS = {
    "content": "content",
    "project": "project if project is not None else self.project",
    "source": "source",
    "query": "query",
    "limit": "limit",
    "with_trace": "True",
}


def _body(verb_name: str, expressions: dict[str, str], indent: str, quote: bool) -> str:
    """Render a verb's request body from its declared field tuple.

    The one place either client's post body is written. A key that is not a
    declared field cannot appear here, and a declared field the contract lacks
    never reaches here because ``_require_contract`` refuses first.
    """
    fields = VERBS[verb_name]["fields"]
    unknown = [field for field in fields if field not in expressions]
    if unknown:
        raise SystemExit(
            f"refusing to generate: {verb_name} declares {unknown} with no "
            "expression to emit for it"
        )
    lines = []
    for field in fields:
        key = f'"{field}"' if quote else field
        lines.append(f"{indent}{key}: {expressions[field]},")
    return "\n".join(lines)


HEADER = (
    "// Generated by sdks/generate.py from darkmem's OpenAPI contract (doc 12).\n"
    "// Do not edit: run `make generate` in sdks/ instead.\n"
    "// contract: {digest}\n"
)

PY_HEADER = (
    '"""Generated by sdks/generate.py from darkmem\'s OpenAPI contract (doc 12).\n\n'
    "Do not edit: run ``make generate`` in ``sdks/`` instead.\n"
    "contract: {digest}\n"
    '"""\n'
)

TYPESCRIPT = '''
export interface DarkmemOptions {
  baseUrl?: string;
  token?: string;
  project?: string;
}

/** Capture is a 202 accept carrying the pre-minted memory id (doc 05 §2.2). */
export interface CaptureAck {
  schema_version: number;
  id: string;
  status: "accepted";
}

export interface MemoryRow {
  id: string;
  content: string;
  summary: string | null;
  /** `active` | `superseded` | `deprecated` — carried so a caller never reads
   * a retired row as current (doc 01 F3's honesty guarantee). */
  status: string;
  project: string;
  /** Present only when the request asked for the trace. */
  trace?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface RetrievalEnvelope {
  query: string;
  channels: Record<string, unknown>;
  excluded: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SearchResult {
  items: MemoryRow[];
  total: number;
  limit: number;
  offset: number;
  /** Null unless the request asked for the trace. */
  envelope: RetrievalEnvelope | null;
}

/** A thin typed wrapper over the two front doors. Two verbs, no framework.
 *
 * Ratification, review and vault administration are absent by design: they are
 * human-authenticated single-door acts (doc 15 §6). Every door this client can
 * reach is authenticated, so what keeps ratify out is the surface it is given,
 * not the absence of auth.
 */
export class Darkmem {
  readonly #baseUrl: string;
  readonly #token: string | undefined;
  readonly #project: string | undefined;

  constructor(options: DarkmemOptions = {}) {
    this.#baseUrl = (options.baseUrl ?? "http://localhost:8000").replace(/\\/+$/, "");
    this.#token = options.token;
    this.#project = options.project;
  }

  /** File a memory. Answers 202 with a pre-minted id — every door buffers. */
  async capture(
    content: string,
    options: {
      project?: string;
      source?: string;
    } = {},
  ): Promise<CaptureAck> {
    return this.#post<CaptureAck>(
      "__CAPTURE_PATH__",
      {
__CAPTURE_BODY__
      },
    );
  }

  /** Run the memory read. The trace is always requested: doc 15 §6 defines the
   * verb as returning the labelled results *with their trace*.
   */
  async search(
    query: string,
    options: {
      project?: string;
      limit?: number;
    } = {},
  ): Promise<SearchResult> {
    return this.#post<SearchResult>(
      "__SEARCH_PATH__",
      {
__SEARCH_BODY__
      },
    );
  }

  async #post<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.#token) {
      headers["Authorization"] = `Bearer ${this.#token}`;
    }
    // An omitted argument is omitted from the wire, never sent as null: the
    // contract's defaults (`limit`, `with_trace`) are non-nullable, so a null
    // would be a 422 for an argument the caller never passed.
    const payload = Object.fromEntries(
      Object.entries(body).filter(([, value]) => value !== undefined && value !== null),
    );
    const response = await fetch(`${this.#baseUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      // The body is where a 422 names the field it rejected — the most likely
      // failure for a minimal client, and useless to a caller who cannot see it.
      const detail = await response.text().catch(() => "");
      throw new Error(
        `darkmem ${path} answered ${response.status}${detail ? `: ${detail}` : ""}`,
      );
    }
    return (await response.json()) as T;
  }
}
'''

PYTHON = '''
from __future__ import annotations

import httpx

CAPTURE_PATH = "__CAPTURE_PATH__"
SEARCH_PATH = "__SEARCH_PATH__"


class Darkmem:
    """A thin typed wrapper over the two front doors. Two verbs, no framework.

    Ratification, review and vault administration are absent by design: they are
    human-authenticated single-door acts (doc 15 section 6). Every door this
    client can reach is authenticated, so what keeps ratify out is the surface
    it is given, not the absence of auth.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: str | None = None,
        project: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.project = project

    async def capture(
        self,
        content: str,
        *,
        project: str | None = None,
        source: str | None = None,
    ) -> dict:
        """File a memory. Answers 202 with a pre-minted id -- every door buffers."""
        return await self._post(
            CAPTURE_PATH,
            {
__CAPTURE_BODY__
            },
        )

    async def search(
        self,
        query: str,
        *,
        project: str | None = None,
        limit: int | None = None,
    ) -> dict:
        """Run the memory read. The trace is always requested: doc 15 section 6
        defines the verb as returning the labelled results with their trace.
        """
        return await self._post(
            SEARCH_PATH,
            {
__SEARCH_BODY__
            },
        )

    async def _post(self, path: str, body: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        # An omitted argument is omitted from the wire, never sent as null: the
        # contract's defaults (``limit``, ``with_trace``) are non-nullable, so a
        # null would be a 422 for an argument the caller never passed.
        payload = {key: value for key, value in body.items() if value is not None}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{path}", json=payload, headers=headers,
            )
            response.raise_for_status()
            return response.json()
'''


def render_typescript(digest: str) -> str:
    return (
        HEADER.format(digest=digest)
        + TYPESCRIPT.replace("__CAPTURE_PATH__", VERBS["capture"]["path"])
        .replace("__SEARCH_PATH__", VERBS["search"]["path"])
        .replace("__CAPTURE_BODY__", _body("capture", TS_EXPRESSIONS, " " * 8, False))
        .replace("__SEARCH_BODY__", _body("search", TS_EXPRESSIONS, " " * 8, False))
    )


def render_python(digest: str) -> str:
    return (
        PY_HEADER.format(digest=digest)
        + PYTHON.replace("__CAPTURE_PATH__", VERBS["capture"]["path"])
        .replace("__SEARCH_PATH__", VERBS["search"]["path"])
        .replace("__CAPTURE_BODY__", _body("capture", PY_EXPRESSIONS, " " * 16, True))
        .replace("__SEARCH_BODY__", _body("search", PY_EXPRESSIONS, " " * 16, True))
    )


def main() -> int:
    schema = contract()
    _require_contract(schema)
    digest = _hash(schema)

    files = {
        SDKS / "ts/src/client.ts": render_typescript(digest),
        SDKS / "python/darkmem_sdk/client.py": render_python(digest),
    }
    for path, content in sorted(files.items()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"wrote {path.relative_to(SDKS)}")

    print(f"contract {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
