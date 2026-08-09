#!/usr/bin/env python
"""The SDK generator (doc 15 §6) — T3.25's scaffold, T3.14's bodies.

**Generated, not hand-written, and that is the invariant rather than a
convenience.** Doc 15 §6: keeping the SDK generated from doc 12's contract "is
what guarantees the SDK never drifts from the two front doors … it enforces
invariant 17 (the SDK cannot expose a behaviour the contract does not)". So the
generator reads the *live* OpenAPI document off the running app object — the
same schema the app serves — rather than a checked-in copy that could age.

**Three verbs, deliberately** — `capture`, `search`, `declareContext`. darkmem
is not building a client platform; doc 00 §8's success criterion is that a
minimal SDK exists. Each verb is bound to the contract surface it wraps and
generation **fails** if that surface is absent: an SDK method with no route
behind it is precisely the drift this design exists to prevent.

**The binding is per *field*, not per route (T3.14).** T3.25 pinned each verb
to a path and a method, which is a real guard but a shallow one: it passed
while both emitted bodies sent an ``applies_when`` key that no request schema
in the contract has — silently dropped by every door, so a declared context
reached nothing and nothing said so. A route-level guard cannot see that. So
each verb now also names the request-body fields it sends, and generation
refuses when the contract's request schema does not carry one.

**Contract bindings, and why these three and not the ones T3.25 guessed:**

- ``capture`` → ``POST /api/v1/memories``, unchanged.
- ``search`` → ``POST /api/v1/knowledge/search``, **moved off**
  ``/api/v1/memories/search``. Doc 15 §6 defines the verb as "the F3 read"
  returning "the labelled results with their trace" and gives it a ``fused?``
  argument; only the composed read serves any of that — the plain memories
  search returns a bare ``list[MemoryResponse]`` with no envelope, no layer or
  verification labels and no ``fuse`` axis. ``app/schemas/knowledge.py`` says
  as much from the other side, naming "an SDK generator reading it — doc 15's,
  eventually" as the reason ``rows``/``sections`` exclusivity is enforced in
  the model.
- ``declareContext`` → the ``X-Darkmem-Context`` **header**, not a route. It
  was pinned to ``POST /api/v1/memories/reason``, which it has nothing to do
  with; the route existed, so the guard was satisfied by a binding that meant
  nothing. Doc 12 §5 settles per-session context as a header precisely because
  a stateful ``context_declare`` "would be a lie on a ``stateless_http=True``
  server", so there is no route to bind and pretending otherwise is the drift
  in miniature. The header name is pinned here and checked against the app's
  own constant, so a rename refuses generation exactly as a missing route does.

**What the SDK deliberately cannot express.** Ratification, review and vault
administration are absent, and doc 15 §6 gives the reason: they are
human-authenticated actions, and "putting them in a LAN client SDK would hand
``confirmed``-power to an unauthenticated caller". Absence is asserted, not
reviewed — ``sdks/python/tests/test_surface.py`` reads both generated files and
checks the public surface *is* the three verbs, rather than checking that one
forbidden word is missing from it. The TypeScript transport is a ``#private``
method so the escape hatch is closed at run time and not merely in the types.

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

# Doc 12 §5's per-session declaration. Pinned as a literal *and* checked
# against the app's own constant below: importing it alone would let a rename
# silently re-point the SDK at a header nothing reads, which is the same
# failure as a missing route and deserves the same refusal.
CONTEXT_HEADER = "X-Darkmem-Context"

# The three verbs, each pinned to the contract surface it wraps, down to the
# request-body fields it sends. The pinning is the point: if a route is renamed
# or a field dropped, generation fails here rather than emitting an SDK that
# calls a 404 or posts a key the door ignores.
VERBS = {
    "capture": {
        "method": "post",
        "path": "/api/v1/memories",
        "fields": ("content", "project", "source"),
    },
    "search": {
        "method": "post",
        "path": "/api/v1/knowledge/search",
        "fields": ("query", "project", "limit", "fuse"),
    },
    # No route, by doc 12 §5's decision. The binding is the header.
    "declareContext": {"header": CONTEXT_HEADER},
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

    Three failures, one message, because they are one defect: the SDK claims a
    surface the contract does not have.
    """
    missing: list[str] = []
    for name, verb in sorted(VERBS.items()):
        if "header" in verb:
            from app.api.context_resolution import DECLARED_CONTEXT_HEADER

            if verb["header"].lower() != DECLARED_CONTEXT_HEADER.lower():
                missing.append(
                    f"{name} → header {verb['header']} "
                    f"(the contract resolves {DECLARED_CONTEXT_HEADER})"
                )
            continue
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

    Not of the whole document: the SDK is three verbs, and hashing all 116
    paths would report a change every time an unrelated route moved, training
    a reader to ignore it. The header is in the digest for the same reason the
    routes are — it is one of the three bindings.
    """
    bound: dict[str, object] = {}
    for name, verb in VERBS.items():
        if "header" in verb:
            bound[f"header {verb['header']}"] = name
            continue
        properties = _request_properties(schema, verb)
        bound[f"{verb['method']} {verb['path']}"] = {
            "operation": schema["paths"][verb["path"]][verb["method"]],
            "fields": {field: properties.get(field) for field in verb["fields"]},
        }
    return hashlib.sha256(
        json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


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

# The one honest limitation both clients state at the point a reader meets it.
CONTEXT_NOTE_LINES = (
    "A declared context rides the X-Darkmem-Context header on every request.",
    "Doc 12 section 5 ranks a per-call `context` body argument above that",
    "header, but neither bound door carries such a field -- MemoryCreate has",
    "none, and KnowledgeSearchRequest deliberately has none so both doors stay",
    "equal (invariant 17). So a per-call context is carried in the header too,",
    "at rank 2 rather than rank 1. Only one context is ever sent, so the",
    "distinction cannot change which declaration wins; it is recorded because",
    "the SDK carries the value and never decides what it means -- whether a",
    "context boosts, labels or excludes is doc 07's, and which doors resolve",
    "it at all is the server's.",
)


def _ts_comment(lines: tuple[str, ...], indent: str = "   ") -> str:
    return "\n".join(f"{indent}* {line}".rstrip() for line in lines)


def _py_comment(lines: tuple[str, ...], indent: str = "    ") -> str:
    return "\n".join(f"{indent}{line}".rstrip() for line in lines)


TYPESCRIPT = '''
/** The declared caller context: doc 06's closed `env`/`situation` axes plus a
 * free `version`. The SDK normalises nothing and matches nothing — doc 12 owns
 * the wire shape and doc 07 owns what it means. */
export type DeclaredContext = Record<string, unknown>;

export interface DarkmemOptions {
  baseUrl?: string;
  token?: string;
  project?: string;
  context?: DeclaredContext | null;
}

/** Capture is a 202 accept carrying the pre-minted memory id (doc 05 §2.2). */
export interface CaptureAck {
  schema_version: number;
  id: string;
}

export interface ComposedRow {
  id: string;
  layer: string;
  text: string;
  score: number;
  labels: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SearchEnvelope {
  fused: boolean;
  [key: string]: unknown;
}

/** `rows` and `sections` are exclusive — the shape the `fused` argument chose.
 * Expressed as a union rather than two nullable fields so a caller reading the
 * wrong one for the requested shape is a type error rather than a `null` that
 * looks like an empty vault. */
export type SearchResult =
  | { rows: ComposedRow[]; sections: null; envelope: SearchEnvelope }
  | { rows: null; sections: Record<string, ComposedRow[]>; envelope: SearchEnvelope };

/** A thin typed wrapper over the two front doors. Three verbs, no framework.
 *
 * Ratification, review and vault administration are absent by design: they are
 * human-authenticated single-door acts, and an unauthenticated LAN client that
 * could reach them would hold `confirmed`-power (doc 15 §6).
 */
export class Darkmem {
  readonly #baseUrl: string;
  readonly #token: string | undefined;
  readonly #project: string | undefined;
  #context: DeclaredContext | null;

  constructor(options: DarkmemOptions = {}) {
    this.#baseUrl = (options.baseUrl ?? "http://localhost:8000").replace(/\\/+$/, "");
    this.#token = options.token;
    this.#project = options.project;
    this.#context = options.context ?? null;
  }

  /** Declare the session's context once; every later call carries it.
   *
__CONTEXT_NOTE_TS__
   */
  declareContext(context: DeclaredContext | null): void {
    this.#context = context;
  }

  /** File a memory. Answers 202 with a pre-minted id — every door buffers. */
  async capture(
    content: string,
    options: {
      project?: string;
      source?: string;
      context?: DeclaredContext;
    } = {},
  ): Promise<CaptureAck> {
    return this.#post<CaptureAck>(
      "__CAPTURE_PATH__",
      {
        content,
        project: options.project ?? this.#project,
        source: options.source,
      },
      options.context,
    );
  }

  /** Run the composed four-layer read. `fused` selects doc 07 §5's single-list
   * shape for a token-budgeted consumer; the default is sectioned by layer. */
  async search(
    query: string,
    options: {
      project?: string;
      limit?: number;
      fused?: boolean;
      context?: DeclaredContext;
    } = {},
  ): Promise<SearchResult> {
    return this.#post<SearchResult>(
      "__SEARCH_PATH__",
      {
        query,
        project: options.project ?? this.#project,
        limit: options.limit,
        fuse: options.fused,
      },
      options.context,
    );
  }

  async #post<T>(
    path: string,
    body: Record<string, unknown>,
    context?: DeclaredContext,
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.#token) {
      headers["Authorization"] = `Bearer ${this.#token}`;
    }
    const declared = context ?? this.#context;
    if (declared) {
      headers["__CONTEXT_HEADER__"] = JSON.stringify(declared);
    }
    // An omitted argument is omitted from the wire, never sent as null: the
    // contract's defaults (`limit`, `fuse`) are non-nullable, so a null would
    // be a 422 for an argument the caller never passed.
    const payload = Object.fromEntries(
      Object.entries(body).filter(([, value]) => value !== undefined && value !== null),
    );
    const response = await fetch(`${this.#baseUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`darkmem ${path} answered ${response.status}`);
    }
    return (await response.json()) as T;
  }
}
'''

PYTHON = '''
from __future__ import annotations

import json
from typing import Any

import httpx

CAPTURE_PATH = "__CAPTURE_PATH__"
SEARCH_PATH = "__SEARCH_PATH__"
CONTEXT_HEADER = "__CONTEXT_HEADER__"


class Darkmem:
    """A thin typed wrapper over the two front doors. Three verbs, no framework.

    Ratification, review and vault administration are absent by design: they are
    human-authenticated single-door acts, and an unauthenticated LAN client that
    could reach them would hold ``confirmed``-power (doc 15 section 6).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: str | None = None,
        project: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.project = project
        self._context = context

    def declare_context(self, context: dict[str, Any] | None) -> None:
        """Declare the session's context once; every later call carries it.

__CONTEXT_NOTE_PY__
        """
        self._context = context

    async def capture(
        self,
        content: str,
        *,
        project: str | None = None,
        source: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict:
        """File a memory. Answers 202 with a pre-minted id -- every door buffers."""
        return await self._post(
            CAPTURE_PATH,
            {
                "content": content,
                "project": project or self.project,
                "source": source,
            },
            context=context,
        )

    async def search(
        self,
        query: str,
        *,
        project: str | None = None,
        limit: int | None = None,
        fused: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict:
        """Run the composed four-layer read.

        ``fused`` selects doc 07 section 5's single-list shape for a
        token-budgeted consumer; the default is sectioned by layer. Exactly one
        of ``rows`` / ``sections`` comes back populated, and ``envelope.fused``
        names which.
        """
        return await self._post(
            SEARCH_PATH,
            {
                "query": query,
                "project": project or self.project,
                "limit": limit,
                "fuse": fused,
            },
            context=context,
        )

    async def _post(
        self, path: str, body: dict, *, context: dict[str, Any] | None = None,
    ) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        declared = context if context is not None else self._context
        if declared:
            headers[CONTEXT_HEADER] = json.dumps(declared, separators=(",", ":"))
        # An omitted argument is omitted from the wire, never sent as null: the
        # contract's defaults (``limit``, ``fuse``) are non-nullable, so a null
        # would be a 422 for an argument the caller never passed.
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
        .replace("__CONTEXT_HEADER__", CONTEXT_HEADER)
        .replace("__CONTEXT_NOTE_TS__", _ts_comment(CONTEXT_NOTE_LINES))
    )


def render_python(digest: str) -> str:
    return (
        PY_HEADER.format(digest=digest)
        + PYTHON.replace("__CAPTURE_PATH__", VERBS["capture"]["path"])
        .replace("__SEARCH_PATH__", VERBS["search"]["path"])
        .replace("__CONTEXT_HEADER__", CONTEXT_HEADER)
        .replace("__CONTEXT_NOTE_PY__", _py_comment(CONTEXT_NOTE_LINES, "        "))
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
