"""The undeclared-field guard (T2.104).

FastAPI + pydantic v2 default to ``extra="ignore"``: a key present in the
dict a route hands to its ``response_model`` but absent from that model's
fields is dropped with no error, no warning, no log line. Four fields in
``schemas/facts.py`` were lost this way across three separate landings
(``demotion_pending_since``, ``label_suppressed``, ``unverified``, ``stale``)
before anyone noticed, because a shape/type comparison against a fixed field
list cannot catch a field that silently is not there — the response is
smaller, not wrong, and every existing assertion about the fields it does
carry still passes.

The only thing that catches it is a key-set diff between what the builder
actually computed and what the wire actually served, so this compares
``built`` (the raw dict or model a service-layer builder produced) against
``served`` (the same object after it round-tripped through a live
``response_model``) and reports every key present in the first and missing
from the second. It recurses into nested mappings and into sequences of
mappings, because the concrete case this module exists to catch —
``FactSourceGroup.stale`` — was dropped two levels down
(``FactDetailResponse.sources[].stale``), not at the top level a shallow
comparison would have checked.

**What this does not cover.** Only keys the builder actually wrote are
checked; a response field with no corresponding key in the builder's own
output is invisible to this guard, so a route that hands the model a dict
missing a field pydantic itself requires still fails at model construction,
just not through here. Values are never compared, only key presence — a
served field with the wrong type or the wrong value is a different bug this
guard makes no claim about. And this only sees what the caller feeds it:
a builder whose real service layer this test does not invoke stays unchecked
by construction, which is why each call site names, in its own test, which
builder and which route it is standing in for.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def undeclared_keys(built: Any, served: Any, *, path: str = "$") -> list[str]:
    missing: list[str] = []
    if isinstance(built, Mapping):
        if not isinstance(served, Mapping):
            return [f"{path}: builder produced a mapping, response did not"]
        for key, value in built.items():
            child_path = f"{path}.{key}"
            if key not in served:
                missing.append(child_path)
                continue
            missing.extend(undeclared_keys(value, served[key], path=child_path))
    elif isinstance(built, Sequence) and not isinstance(built, (str, bytes)):
        if not isinstance(served, Sequence) or isinstance(served, (str, bytes)):
            return [f"{path}: builder produced a list, response did not"]
        if len(served) < len(built):
            return [
                f"{path}: builder produced {len(built)} item(s), "
                f"response served only {len(served)}"
            ]
        for index, (built_item, served_item) in enumerate(zip(built, served)):
            missing.extend(
                undeclared_keys(built_item, served_item, path=f"{path}[{index}]")
            )
    return missing


def assert_builder_keys_served(built: Any, served: Any, *, label: str) -> None:
    missing = undeclared_keys(built, served)
    assert not missing, (
        f"{label}: response_model silently dropped key(s) the builder wrote "
        f"(pydantic extra=\"ignore\" gives no error for this): {missing}"
    )
