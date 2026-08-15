"""The F7 research loop: gather evidence outside the box, file it through the
ordinary capture front door (doc 09 §6, T3.07).

**This is orchestration, not a pipeline.** Every finding is filed through
``MemoryService.batch_create_memories`` — the same service call the four
capture doors funnel into — so extraction, classification, the buffer, and the
ladder treat a researched memory exactly as they treat any other. The loop
reaches nothing under ``app.services`` that capture does not already reach for
it; ``tests/test_auto_research.py`` pins the module's whole ``app.*`` import set
to a whitelist so a second ingestion path cannot appear here by accident.

**Evidence gathering lives outside the box** (invariant 1, doc 09 §6): web
search and fetch are the calling agent's capability, never a darkmem datastore.
So ``ResearchGatherer`` is a port with no in-tree implementation, and that
absence is a design position rather than an omission — a gatherer backed by a
model alone would *invent* sources, and inventing sources is the one failure
this loop's origin discipline exists to prevent. Whoever owns a real
web-capable agent injects it.

**The loop manufactures origins; it does not observe them, and the corpus must
be able to tell the difference** (v0.5 spec, Half B). Two markers make that
machine-checkable rather than remembered: every researched capture carries
``source = RESEARCH_SOURCE`` and an ``origin_key`` that ``is_researched_origin``
recognises, so a later measurement can slice manufactured origins out of a
count instead of pooling them silently. Forging the marker from outside can
only *widen* the manufactured slice, which is the safe direction for a
disclosure — a researched capture can never lose its marker, because this
module is the only thing that files one.

**A researched capture's origin is its SOURCE's identity — never the run's, and
never the finding's** (T3.08). ``research_origin_id`` canonicalises the
gatherer's ``source_id`` into a locator identity, so the same page fetched
twice, under either scheme, with or without ``www.``, a trailing slash, a
fragment or a campaign parameter, resolves to one origin and corroborates once.
A per-run key would be the counterfeit doc 09 §6 names — two runs over one page
are one source fetched twice — and a per-finding key would be worse still,
since paraphrasing one page into two notes would then buy a promotion. Identity
that cannot be established at all resolves to ``None``, which lands the capture
in ``resolve_origin_key``'s merge-to-one bucket: an undercount, which only
delays a promotion, rather than an overcount, which fabricates one.

**A failed run leaves nothing behind.** Gathering completes before anything is
written, and the whole run is filed in a single ``batch_create_memories``
call — one transaction, one commit — with any failure rolling that transaction
back before re-raising. The *run* commits twice, though: the filing, then the
run-level journal. A failure in that second window leaves the filing durable
and is degraded to ``journalled=False`` rather than raised, because raising
would report a filed run as failed and a driver retrying on it would file the
whole run twice. A budget the run cannot satisfy refuses the
whole run rather than filing a truncated one: filing part of a research run
would leave a corpus whose origin story is untrue in a way nothing downstream
could detect.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol, Sequence
from urllib.parse import parse_qsl, urlsplit, unquote
from uuid import UUID

import idna
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp.client_identity import resolve_origin_key
from app.models.config import Config
from app.schemas.memory import MemoryBatchCreate, MemoryCreate
from app.services.events import record_event
from app.services.memory import MemoryService
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# The reserved source-kind. Every capture this loop files carries it, so
# `memories.source` alone distinguishes a manufactured origin from an observed
# one without joining anything.
RESEARCH_SOURCE = "research"

AUTO_RESEARCH_CONFIG_KEY = "auto_research"

# Mirrors `client_identity._sanitize_origin`'s own bound. Emitting a longer id
# would hand that function the merge boundary; emitting exactly its bound, over
# an alphabet it leaves alone, makes the id this module computes the id that
# lands on the row — and truncation past it merges two long locators, which is
# the safe direction.
ORIGIN_ID_MAX_LEN = 128

# Query keys that identify a *referral* rather than a document. Dropping one can
# only merge two ids; keeping one splits a single page into as many origins as
# there are ways to link to it, and a split is the direction that manufactures
# corroboration. Doubt therefore resolves toward dropping.
_TRACKING_QUERY_KEYS = frozenset({
    "fbclid", "gclid", "gbraid", "wbraid", "msclkid", "yclid", "igshid",
    "mc_cid", "mc_eid", "spm", "_ga", "ref", "ref_src", "referrer",
})
_TRACKING_QUERY_PREFIXES = ("utm_",)

_WHITESPACE_RE = re.compile(r"\s+")
# Removed outright rather than replaced: the WHATWG URL parser strips these
# from a URL, so one href wrapped across lines is one locator.
_URL_STRIPPED_RE = re.compile(r"[\t\r\n]")
# Folds `scheme:` and `scheme:/` to `scheme://`. Deliberately not three or
# more: `file:///tmp/a.pdf` means an *empty* authority, and collapsing those
# slashes would make `tmp` its host.
_SCHEME_NO_SLASHES_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):/{0,1}(?!/)")
_REPEATED_SLASH_RE = re.compile(r"/{2,}")

# Fail closed. Building the loop is not running it (T3.07 brief): pointing it
# at a live instance is a separate, owner-owned decision, so an install that
# has never been configured refuses every run.
AUTO_RESEARCH_DEFAULTS: dict[str, object] = {
    "enabled": False,
    "max_findings_per_run": 20,
    "max_content_chars": 8000,
}

# The batch door's own cap, read off the schema rather than re-typed, so the
# budget cannot quietly authorise a batch the front door would reject.
MAX_FINDINGS_CEILING: int = next(
    meta.max_length
    for meta in MemoryBatchCreate.model_fields["entries"].metadata
    if getattr(meta, "max_length", None) is not None
)


class ResearchBudgetExceeded(Exception):
    """The gathered evidence does not fit the configured budget.

    Raised before anything is written. Refusing the run is deliberate: a
    truncated filing would record a research run that claims to have gathered
    what it did not file.
    """


class ResearchDisabled(Exception):
    """The `auto_research` config row does not permit runs on this install."""


@dataclass(frozen=True)
class ResearchFinding:
    """One piece of evidence the gatherer brought back.

    ``source_id`` is the gatherer's own identity for the source it came from —
    a canonical URL, a document id. It is carried through to the memory's
    metadata and is what ``research_origin_id`` resolves into this finding's
    origin, so it is the one field on which a corroboration count turns: two
    findings sharing it are one witness, and two findings that do not are two.
    Leaving it unset is the honest answer when the gatherer cannot say, and it
    merges rather than counting.
    """

    content: str
    source_id: str | None = None
    metadata: dict = field(default_factory=dict)


class ResearchGatherer(Protocol):
    """The evidence-gathering capability, which lives outside darkmem's box.

    Implementations do the searching and fetching and return at most ``limit``
    findings. Returning more is a contract violation the loop refuses rather
    than trims.
    """

    async def gather(self, subject: str, *, limit: int) -> Sequence[ResearchFinding]:
        ...


@dataclass(frozen=True)
class ResearchBudget:
    enabled: bool
    max_findings_per_run: int
    max_content_chars: int


@dataclass(frozen=True)
class ResearchRunResult:
    run_id: UUID
    subject: str
    project: str
    gathered: int
    filed: int
    memory_ids: tuple[UUID, ...]
    journalled: bool


def _positive_int(value: object, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


async def load_budget(session: AsyncSession) -> ResearchBudget:
    """The per-run budget, from the `auto_research` config row over defaults.

    A malformed row degrades to the defaults rather than raising: the budget
    bounds a run, and an unreadable bound must never read as "unbounded".
    """
    row = (await session.execute(
        select(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY)
    )).scalar_one_or_none()
    stored = row.value if row is not None and isinstance(row.value, dict) else {}

    max_findings = _positive_int(
        stored.get("max_findings_per_run"),
        int(AUTO_RESEARCH_DEFAULTS["max_findings_per_run"]),
    )
    if max_findings > MAX_FINDINGS_CEILING:
        logger.warning(
            "%s.max_findings_per_run=%d exceeds the capture batch cap %d; clamping",
            AUTO_RESEARCH_CONFIG_KEY, max_findings, MAX_FINDINGS_CEILING,
        )
        max_findings = MAX_FINDINGS_CEILING

    # `bool()` is the wrong coercion for the master switch: `{"enabled":
    # "false"}` — the most natural malformed shape an operator writes — is
    # truthy, so the one field where failing closed matters most would fail
    # open. The int fields already get this treatment from `_positive_int`.
    enabled = stored.get("enabled", AUTO_RESEARCH_DEFAULTS["enabled"])
    if not isinstance(enabled, bool):
        logger.warning(
            "%s.enabled=%r is not a boolean; falling back to the default",
            AUTO_RESEARCH_CONFIG_KEY, enabled,
        )
        enabled = AUTO_RESEARCH_DEFAULTS["enabled"]

    return ResearchBudget(
        enabled=bool(enabled),
        max_findings_per_run=max_findings,
        max_content_chars=_positive_int(
            stored.get("max_content_chars"),
            int(AUTO_RESEARCH_DEFAULTS["max_content_chars"]),
        ),
    )


def _canonical_query(query: str) -> str:
    kept = {
        (key.lower(), value.lower())
        for key, value in parse_qsl(query, keep_blank_values=True)
        if key.lower() not in _TRACKING_QUERY_KEYS
        and not key.lower().startswith(_TRACKING_QUERY_PREFIXES)
    }
    # A set, not a list: `?a=1` and `?a=1&a=1` are one page, and a fetcher that
    # appends a parameter it already carries would otherwise mint a second
    # origin. Deduplicating identical pairs cannot separate two spellings —
    # distinct values survive as distinct members.
    return "&".join(f"{key}={value}" for key, value in sorted(kept))


def _canonical_path(path: str) -> str:
    """Percent-decoded and dot-segment-resolved, both merge-only.

    RFC 3986 §6.2.2 makes ``/caf%C3%A9`` and ``/café`` one identifier, and
    §6.2.3 does the same for ``/x/../docs`` and ``/docs``. This repo's own
    client produces the split: ``httpx`` percent-encodes a non-ASCII path, so a
    gatherer storing ``str(response.url)`` and one storing the scraped href hand
    back two spellings of one page. Decoding is deliberately full — ``%2F``
    becomes ``/`` — because doubt resolves toward merging, which delays a
    promotion rather than fabricating one.
    """
    decoded = unquote(path)
    segments: list[str] = []
    for segment in decoded.split("/"):
        if segment == ".":
            continue
        if segment == "..":
            # **Never past the root.** `segments[0]` is the empty string an
            # absolute path splits to, and popping it glued the path onto the
            # host — `/%2e%2e/a` canonicalised to `example.testa` while `/a`
            # gave `example.test/a`, two origins for one page.
            if len(segments) > 1:
                segments.pop()
            continue
        segments.append(segment)
    return _REPEATED_SLASH_RE.sub("/", "/".join(segments))


def _split_port(host: str) -> tuple[str, str]:
    """``(host, port)``, with a default port dropped and any other kept verbatim.

    Verbatim because the digits after a colon are not always a port:
    ``urn:isbn:0451450523`` lands here too, and normalising through ``int()``
    would drop its leading zero and merge two distinct identifiers.
    """
    if host.endswith("]"):
        # A bracketed IPv6 literal with no port; every colon in it is address.
        return host, ""
    head, separator, tail = host.rpartition(":")
    if not separator or not head or "]" in tail:
        return host, ""
    try:
        if int(tail) in (80, 443):
            return head, ""
    except ValueError:
        pass
    return head, tail


def _canonical_host(netloc: str) -> str:
    # Credentials are not identity, and a fetcher that carries them on one
    # request and not the next would otherwise mint two origins for one page.
    host = netloc.rsplit("@", 1)[-1].lower()

    # **Port before dots.** `rstrip(".")` used to run first, so a trailing-dot
    # FQDN carrying an explicit default port kept its dot once the port came
    # off and split from the same host written plainly.
    # **The port comes off first and goes back on last.** The first repair of
    # this function reattached a non-default port before the passes below ran,
    # which did not fix the ordering bug so much as move it one step later:
    # every canonicalisation here stopped working the moment a port was
    # present, and strict `idna.encode` *raises* on the embedded colon where
    # the old IDNA2003 codec had tolerated it — so the fix for one page
    # becoming two origins created exactly that failure for IDN hosts carrying
    # a port. Splitting the port off is what removes the ordering hazard
    # instead of relocating it.
    host, port = _split_port(host)
    suffix = f":{port}" if port else ""

    host = host.rstrip(".")
    host = host[4:] if host.startswith("www.") else host

    # An IPv6 literal has many spellings of one address (zero-compression,
    # leading zeros, case). `ipaddress` gives the one canonical form; anything
    # it refuses is left as written rather than guessed at.
    if host.startswith("[") and host.endswith("]"):
        try:
            return f"[{ipaddress.IPv6Address(host[1:-1]).compressed}]{suffix}"
        except ValueError:
            return f"{host}{suffix}"

    # **IDNA2008 via the `idna` package, which is what `httpx` uses.** This ran
    # through Python's built-in codec, i.e. IDNA2003, and the two standards
    # disagree on the deviation characters: IDNA2003 maps `ß` to `ss` and final
    # sigma to sigma, IDNA2008 keeps them. So `https://straße.example` and the
    # `xn--strae-oqa.example` this repo's own client emits for it canonicalised
    # to two different origins — one page, two attributable witnesses, which at
    # seven days' spacing is a promotion off a single source. Matching the
    # client is also what stops the opposite error: IDNA2003 conflated
    # `strasse.example` with `straße.example`, two genuinely different hosts.
    if host:
        try:
            host = idna.encode(host, uts46=True, transitional=False).decode("ascii")
        except (idna.IDNAError, UnicodeError, ValueError):
            # An unencodable name is not two names; it is one this pass cannot
            # normalise, and leaving it merges no worse than before.
            pass
    return f"{host}{suffix}"


def _canonical_locator(value: str) -> str:
    # Parsed as a locator whether or not it carries a scheme, so a bare
    # `example.test/a` and `https://www.example.test/a/` reach the same form
    # rather than splitting on which spelling the gatherer happened to hand
    # back. A non-locator id simply lands in the host slot and survives the
    # pass unchanged.
    # NFC first: two Unicode spellings of one host or path are one locator, and
    # the encoding steps below have to run over a settled form.
    value = unicodedata.normalize("NFC", value)
    # `https:example.test/a` is a legal spelling of `https://example.test/a`
    # and appears in hand-written hrefs. Without this the scheme lands in the
    # host slot and the two split.
    value = _SCHEME_NO_SLASHES_RE.sub(r"\1://", value, count=1)
    prefixed = value if "://" in value or value.startswith("//") else f"//{value}"
    parts = urlsplit(prefixed)
    host = _canonical_host(parts.netloc)
    path = _canonical_path(parts.path.lower()).rstrip("/")
    query = _canonical_query(parts.query)
    return f"{host}{path}" + (f"?{query}" if query else "")


def _bounded_origin_id(value: str) -> str | None:
    """The canonical form over the alphabet the capture layer leaves intact.

    ``:`` is excluded because ``_sanitize_origin`` excludes it — that removal is
    what stops a *declared* id forging a second key segment, so an id carrying
    one would be rewritten under this module and the seam would no longer emit
    what lands. An id with nothing alphanumeric left is not an identity and
    merges instead.
    """
    cleaned = "".join(
        "-" if character == " " else character
        for character in value
        if character.isprintable() and character != ":"
    )[:ORIGIN_ID_MAX_LEN]
    return cleaned if any(character.isalnum() for character in cleaned) else None


def research_origin_id(finding: ResearchFinding) -> str | None:
    """The declared origin identity for one finding, or ``None`` to merge.

    One source is one origin, whatever spelling it arrives under. The
    canonicalisation collapses exactly the variation a fetcher produces
    mechanically — scheme, host case, ``www.``, a default port, credentials, a
    trailing slash, duplicated slashes, a fragment, campaign parameters,
    parameter order — because each of those is one page reachable two ways, and
    counting it twice is the manufactured corroboration doc 09 §6 forbids. Every
    step aims to be merge-only — no input should split one source into two ids —
    and the lowercasing in particular is not cosmetic, since the corroboration
    count
    normalises with ``lower(btrim(origin_key))`` and a case-preserved id would
    show the audit a distinction the count does not honour.

    **Merge-only is a tested property, not a structural guarantee, and the
    difference has cost twice.** Stated as holding "by construction", it was
    falsified by T3.08's review (six splitting inputs) and again by v0.5's
    version review (nine more, 2026-08-15) — most seriously an IDNA2003 host
    pass against the IDNA2008 punycode ``httpx`` emits, which made one page two
    attributable origins. Every one is pinned in
    ``tests/test_research_origins.py``. Assume more exist that nobody has
    looked for, and add a red-first pin before extending anything here.

    **Its bound, stated rather than left to be discovered.** Identity here is the
    *locator's*, not the content's: one wire story syndicated under two
    hostnames is two origins, and so is one page reachable under two unrelated
    URLs. Establishing that would take content identity the loop does not have,
    and the guard against it is upstream — the gatherer declares the source it
    actually fetched. What this function guarantees is narrower and checkable:
    given an honest ``source_id``, no re-fetch, re-run or paraphrase adds an
    origin.
    """
    raw = finding.source_id
    if not isinstance(raw, str):
        return None
    # Before the whitespace collapse, not after: tab/CR/LF are *removed* from a
    # URL by the WHATWG parser, and collapsing them to spaces first meant the
    # capture layer saw a `-` where the other spelling had nothing.
    value = _WHITESPACE_RE.sub(" ", _URL_STRIPPED_RE.sub("", raw)).strip()
    if not value:
        return None
    try:
        canonical = _canonical_locator(value)
    except ValueError:
        # urlsplit refuses some netlocs outright (NFKC-confusable characters,
        # unbalanced IPv6 brackets). The id is still an identity; it just gets
        # the opaque treatment rather than the locator one -- but it gets it
        # over the **normalised** form. Falling back to `value` threw away the
        # NFC pass this module does first, so the one path that could not be
        # parsed was also the one that split on Unicode spelling alone.
        canonical = unicodedata.normalize("NFC", value).lower()
    return _bounded_origin_id(canonical) if canonical else None


def research_origin_key(finding: ResearchFinding, *, project: str) -> str:
    """The `origin_key` a researched capture is stamped with.

    Routed through T1.11's ``resolve_origin_key`` rather than formatted here,
    so researched captures inherit the same declared-identity-then-merge chain
    every other door uses, with ``RESEARCH_SOURCE`` as the source.
    """
    return resolve_origin_key(
        research_origin_id(finding), None, source=RESEARCH_SOURCE, project=project,
    )


def is_researched_origin(origin_key: str | None) -> bool:
    """Whether an `origin_key` was manufactured by this loop.

    The disclosure the v0.5 spec asks to be machine-enforced: a measurement
    that pools manufactured origins with observed ones has to do so on
    purpose. Both shapes are recognised — the declared per-source form
    (``research:<id>``) and the merged bucket an unestablishable identity falls
    to (``unknown:research:<project>``) — so filling the seam did not have to
    widen the predicate, which is the one edit that would have left a gap
    exactly where the origins start counting.
    """
    if not origin_key:
        return False
    key = origin_key.strip().lower()
    return key.startswith(f"{RESEARCH_SOURCE}:") or key.startswith(
        f"unknown:{RESEARCH_SOURCE}:"
    )


def _build_entries(
    findings: Sequence[ResearchFinding],
    *,
    subject: str,
    project: str,
    run_id: UUID,
    budget: ResearchBudget,
) -> list[MemoryCreate]:
    if len(findings) > budget.max_findings_per_run:
        raise ResearchBudgetExceeded(
            f"gatherer returned {len(findings)} findings for subject {subject!r}, "
            f"over the {budget.max_findings_per_run} the budget allows"
        )
    for index, finding in enumerate(findings):
        if len(finding.content) > budget.max_content_chars:
            raise ResearchBudgetExceeded(
                f"finding {index} for subject {subject!r} is "
                f"{len(finding.content)} characters, over the "
                f"{budget.max_content_chars} the budget allows"
            )

    entries = [
        MemoryCreate(
            content=finding.content,
            project=project,
            source=RESEARCH_SOURCE,
            origin_key=research_origin_key(finding, project=project),
            metadata={
                **finding.metadata,
                "research": {
                    "run_id": str(run_id),
                    "subject": subject,
                    "source_id": finding.source_id,
                },
            },
        )
        for finding in findings
    ]
    # Validated through the batch door's own schema, so the run inherits its
    # 1-100 cap and its per-entry validation instead of carrying a second copy
    # of either.
    return list(MemoryBatchCreate(entries=entries).entries)


async def run_research(
    session: AsyncSession,
    *,
    subject: str,
    project: str,
    gatherer: ResearchGatherer,
    service: MemoryService | None = None,
    budget: ResearchBudget | None = None,
) -> ResearchRunResult:
    """Gather evidence for ``subject`` and file it into ``project``.

    Owns ``session``'s transaction for the duration: capture commits, and a
    failure rolls back, so a caller must not hand this a session carrying work
    of its own — and a ``service`` passed in must be bound to that same
    session, or the rollback below reaches a transaction the write did not use.

    The two stages are strictly ordered and never interleaved. Gathering
    finishes first, so a gatherer that fails partway through has written
    nothing; filing is then one call, so there is no window in which some
    findings are durable and others are not.
    """
    budget = budget or await load_budget(session)
    if not budget.enabled:
        raise ResearchDisabled(
            f"the {AUTO_RESEARCH_CONFIG_KEY} config row does not enable research runs"
        )

    run_id = new_id()
    findings = list(await gatherer.gather(subject, limit=budget.max_findings_per_run))
    if not findings:
        logger.info("research run %s for %r gathered nothing", run_id, subject)
        return ResearchRunResult(
            run_id=run_id, subject=subject, project=project,
            gathered=0, filed=0, memory_ids=(), journalled=False,
        )

    entries = _build_entries(
        findings, subject=subject, project=project, run_id=run_id, budget=budget,
    )
    service = service or MemoryService(session)
    try:
        results = await service.batch_create_memories(entries, api_key_id=None)
    except Exception:
        await session.rollback()
        raise

    memory_ids = tuple(result.ack.id for result in results)
    # Counts and identity only. The findings' text is already durable on the
    # memory rows, and the journal outlives their deletion (T2.59), so copying
    # content here would widen the residue for nothing this run needs.
    journalled = await record_event(
        session,
        event_type="research_run",
        object_type="system",
        project=project,
        source=RESEARCH_SOURCE,
        payload={
            "run_id": str(run_id),
            "subject": subject,
            "filed": len(memory_ids),
            "memory_ids": [str(memory_id) for memory_id in memory_ids],
            "origins_manufactured": True,
        },
    )
    if not journalled:
        # Not fatal, and deliberately so: the disclosure a later measurement
        # reads is the marker on the memory rows themselves, which is already
        # committed. The journal is the run-level audit on top of it.
        logger.warning("research run %s filed %d memories unjournalled", run_id, len(memory_ids))
    try:
        await session.commit()
    except Exception:
        # The filing committed inside the capture call and is durable. Raising
        # here would report a filed run as failed, and a driver that retried on
        # that exception would file the whole run a second time. Degrade to the
        # same unjournalled outcome the branch above already tolerates.
        await session.rollback()
        journalled = False
        logger.warning(
            "research run %s filed %d memories; the journal commit failed",
            run_id, len(memory_ids),
        )

    return ResearchRunResult(
        run_id=run_id, subject=subject, project=project,
        gathered=len(findings), filed=len(memory_ids),
        memory_ids=memory_ids, journalled=journalled,
    )
