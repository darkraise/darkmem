"""The closed API-key scope vocabulary and its strict reader (doc 18 §5).

Scopes are a closed vocabulary in the sense invariant 5 fixes, and they live
here rather than in ``app.taxonomy`` for the same reason ``EVENT_TYPES`` does:
a scope is never LLM output. It is operator input at issue time, and it is read
back as an authorisation decision.

That read is why the fallthrough direction inverts. Every normaliser in
``app.taxonomy`` maps an unknown value onto a safe default, because the
alternative is losing an entity or a paragraph of prose. Here both directions of
a default are wrong: defaulting an unknown scope *into* the set grants a
privilege nobody asked for, and defaulting it *out* mints a credential that
silently does not work. So an unknown scope is rejected outright, with the
offending value named, at issue time where a human is reading the error.

``ratify`` is not in the set and never joins it. ``confirmed`` is the human-only
rung of the verification ladder, and a key is a credential a program holds, so a
keyed ratification is the forged imprimatur doc 18 §2 names in its threat table.
``FORBIDDEN_SCOPES`` states that as data rather than as a comment so a later
widening that contradicts it fails at import rather than in review.

The three scopes are independent: ``admin`` does not imply ``read`` or
``capture``. An implication ladder is a privilege-escalation design this module
declines to invent, so an operator grants exactly what a key needs.

The vocabulary is a ``tuple`` where ``ENTITY_TYPES`` and ``EVENT_TYPES`` are
``list``. The divergence is deliberate and narrow: those two are read to
normalise, so a mutated one misfiles a row, while a mutated authorisation
vocabulary grants. ``API_KEY_SCOPES.append("ratify")`` is a one-line runtime
privilege escalation that the import-time guard below could not catch, and a
tuple makes it a ``AttributeError`` instead.

``read_scopes`` is deliberately as strict as ``parse_scopes`` even though it
reads a row this module wrote. ``api_keys.scopes`` is jsonb, and anyone with a
psql prompt can edit it, so the stored value is untrusted input on the way back
in. The laxity that matters is not hypothetical: ``"admin" in "admin"`` is True
and so is ``"read" in "unread"``, so a column holding a bare string rather than
a list would grant on a substring match.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


API_KEY_SCOPES: tuple[str, ...] = (
    "capture",
    "read",
    "admin",
)

FORBIDDEN_SCOPES: frozenset[str] = frozenset({"ratify"})

_SCOPE_SET: frozenset[str] = frozenset(API_KEY_SCOPES)


class ScopeRejected(ValueError):
    """A scope value outside the closed set, refused rather than defaulted."""


def assert_no_forbidden_scope(scopes: tuple[str, ...]) -> None:
    """Refuse a vocabulary that has grown a scope the design forbids.

    Called at import against ``API_KEY_SCOPES`` so adding ``ratify`` to the
    closed set stops the process rather than quietly arming a keyed path to the
    human-only rung.
    """
    overlap = frozenset(scopes) & FORBIDDEN_SCOPES
    if overlap:
        raise RuntimeError(
            f"{sorted(overlap)} may never be an API-key scope (doc 18 §5): "
            "confirmed power is reachable only by a human session"
        )


assert_no_forbidden_scope(API_KEY_SCOPES)


def parse_scopes(raw: object) -> tuple[str, ...]:
    """Validate an operator-supplied scope collection into its stored form.

    Raises ``ScopeRejected`` on anything outside the closed set. Returns the
    scopes deduplicated and in ``API_KEY_SCOPES`` order, so two issues of the
    same grant store byte-identical jsonb.
    """
    if isinstance(raw, (str, bytes, bytearray)):
        raise ScopeRejected(
            "scopes must be a list of strings, never a bare string: a string is "
            "iterable and substring-testable, so accepting one would grant on a "
            "substring match"
        )
    if not isinstance(raw, (list, tuple)):
        raise ScopeRejected(
            f"scopes must be a list of strings, got {type(raw).__name__}"
        )

    granted: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            raise ScopeRejected(
                f"each scope must be a string, got {type(item).__name__}"
            )
        value = item.strip().lower()
        if value in FORBIDDEN_SCOPES:
            raise ScopeRejected(
                f"{value!r} is never an API-key scope (doc 18 §5): confirmed "
                "power belongs to a human session, not to a credential a "
                "program holds"
            )
        if value not in _SCOPE_SET:
            raise ScopeRejected(
                f"unknown scope {item!r}; the closed set is "
                f"{', '.join(API_KEY_SCOPES)}"
            )
        granted.add(value)

    if not granted:
        raise ScopeRejected("a key must carry at least one scope")

    return tuple(scope for scope in API_KEY_SCOPES if scope in granted)


def read_scopes(stored: object) -> frozenset[str]:
    """Read a stored ``api_keys.scopes`` value, denying anything malformed.

    Denies rather than raises: a hand-edited row must cost its holder access,
    not turn every request into a 500. Each refusal is logged so a key that has
    silently stopped working is diagnosable.
    """
    if isinstance(stored, (str, bytes, bytearray)) or not isinstance(
        stored, (list, tuple)
    ):
        logger.warning(
            "api_keys.scopes holds %s rather than a list; granting nothing",
            type(stored).__name__,
        )
        return frozenset()

    granted: set[str] = set()
    for item in stored:
        if not isinstance(item, str):
            logger.warning(
                "api_keys.scopes member is %s rather than a string; ignoring it",
                type(item).__name__,
            )
            continue
        value = item.strip().lower()
        if value in _SCOPE_SET and value not in FORBIDDEN_SCOPES:
            granted.add(value)
        else:
            logger.warning("api key carries unknown scope %r; ignoring it", item)
    return frozenset(granted)


def has_scope(stored: object, required: str) -> bool:
    """True when a stored scope set covers ``required``.

    ``required`` is itself checked against the closed set, so a caller asking
    for ``ratify`` — or for a scope that was renamed out from under it — is
    denied even when the stored set is well-formed and generous.
    """
    if required in FORBIDDEN_SCOPES or required not in _SCOPE_SET:
        return False
    return required in read_scopes(stored)
