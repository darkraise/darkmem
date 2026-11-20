"""The one response envelope, shared by every surface (doc 12 §4, T1.42a).

There is exactly one class defining ``schema_version``, ``partial``,
``excluded``, ``page`` and ``context``: :class:`ResponseEnvelope`. Every
surface-specific envelope **extends** it — T1.33's ``RetrievalEnvelope`` is
its retrieval specialisation — because a second, parallel envelope is the
failure this module exists to prevent. ``tests/test_envelope.py`` fails the
build if another model in ``app.schemas`` redeclares one of those fields.

Two deliberate shapes a reader will want explained:

``excluded`` is an **open** ``dict[str, int]`` keyed by reason name. Doc 12
§4 fixed a ``{by_project, by_status}`` pair and was **amended to match this
shape on 2026-07-28**, with those kept as *reserved names*: a reason that
becomes constructible must use the doc's name for it. The T1.29-series
pushdown scopes project and status in SQL, so a foreign row is never fetched
to be counted. An always-zero honesty counter is worse than an absent one:
it reads as evidence that a check ran.

``detail`` on :class:`ErrorEnvelope` is a **string mirror** of
``error.message``. ``frontend/src/lib/api.ts`` interpolates ``detail``
straight into an ``Error``, so dropping the mirror — or letting a 422 put a
list there, as FastAPI's default does — silently degrades every error
message in the UI. Retiring the mirror is T1.42b's, after T1.58 binds the
frontend to ``error.message``.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Iterator, Literal

from pydantic import BaseModel, Field, computed_field

ENVELOPE_SCHEMA_VERSION = 1

DeclaredByTier = Literal["arg", "header", "project_default"]


class PageInfo(BaseModel):
    """Pagination, stated once on the envelope.

    ``PaginatedMemoryResponse``'s top-level ``total``/``limit``/``offset``
    remain as a deprecated mirror of this object; retiring them is a breaking
    change to a shape the frontend reads and belongs to T1.42b, which is why
    a test pins the two agreeing rather than re-deriving pagination there.
    """

    limit: int
    offset: int
    total: int
    next_offset: int | None = None

    @classmethod
    def build(cls, *, limit: int, offset: int, total: int) -> "PageInfo":
        nxt = offset + limit
        return cls(limit=limit, offset=offset, total=total, next_offset=nxt if nxt < total else None)


class ContextEcho(BaseModel):
    """What the request declared as its context, and which tier declared it.

    Both fields are **required**, so a vacuous echo is not constructible —
    the same discipline ``DeclaredContext`` enforces by raising on an empty
    axis set. Undeclared is represented by ``ResponseEnvelope.context`` being
    ``None``, never by an echo carrying ``{}``, and never by the project
    name: an undeclared context that renders as a default is the exact
    confusion T1.65 exists to guard against.

    ``provenance`` is always ``human`` and is not settable from the request.
    """

    declared: dict[str, str]
    declared_by: DeclaredByTier
    provenance: Literal["human"] = "human"


class ResponseEnvelope(BaseModel):
    schema_version: int = ENVELOPE_SCHEMA_VERSION
    excluded: dict[str, int] = Field(default_factory=dict)
    page: PageInfo | None = None
    context: ContextEcho | None = None

    model_config = {"extra": "ignore"}

    @computed_field
    @property
    def partial(self) -> bool:
        """Derived, never assigned.

        A surface with no channels cannot be partial. A retrieval envelope
        overrides this to read its channels, so no constructor can hand back
        an envelope claiming completeness alongside a failed channel — the
        degraded-result-rendering-as-complete failure invariant 14 names.
        """
        return False


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list | None = None


class ErrorEnvelope(BaseModel):
    schema_version: int = ENVELOPE_SCHEMA_VERSION
    error: ErrorDetail
    detail: str


def iter_schema_models() -> Iterator[type[BaseModel]]:
    """Every Pydantic model declared under ``app.schemas``.

    Imports the whole package so the drift guard sees models no test has
    happened to import.
    """
    import app.schemas as schemas_pkg

    seen: set[type[BaseModel]] = set()
    for module_info in pkgutil.iter_modules(schemas_pkg.__path__):
        module = importlib.import_module(f"{schemas_pkg.__name__}.{module_info.name}")
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, BaseModel)
                and value is not BaseModel
                and value.__module__.startswith(schemas_pkg.__name__)
                and value not in seen
            ):
                seen.add(value)
                yield value
