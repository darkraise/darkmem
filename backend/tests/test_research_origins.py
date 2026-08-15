"""T3.08 — one source is one origin, and two sources are two.

The research loop manufactures its own origins, so it is the one capture path
that could counterfeit corroboration without anybody lying: a crawler visiting
one page twice is one witness, and a count that says otherwise promotes a fact
nothing corroborates. These tests pin the arithmetic from both ends.

* **The collapse.** ``TestOneSourceIsOneOrigin`` walks the variation a fetcher
  produces mechanically — scheme, host case, ``www.``, default port,
  credentials, trailing and duplicated slashes, fragment, campaign parameters,
  parameter order — and asserts every spelling reaches one id. Its kill vector
  is ``test_the_raw_source_ids_really_do_differ``: without it, an implementation
  that returned ``source_id`` verbatim would pass every collapse assertion the
  day the fixture happened to use one spelling.
* **The split.** Only genuine difference splits, and ``TestUnknownIdentity``
  covers the other side of doc 09 §6's rule — an identity that cannot be
  established resolves to the merge-to-one bucket rather than to an
  attributable key, because an attributable key is what lowers a threshold.
* **The consequence.** ``TestCorroborationOutcome`` runs the real ladder over
  real ``fact_sources`` rows. The pair that matters is two sources versus one
  page fetched twice under *identical* timing and kinds: the only difference is
  the origin identity this task computes, and the outcomes are opposite.
* **The disclosure.** ``TestManufacturedOriginsStayVisible`` re-asserts the
  T3.07 marker against the declared form, since the merged bucket that carried
  it is no longer the shape a researched capture normally files under.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import unicodedata

import pytest
from sqlalchemy import select, text

from app.api.mcp.client_identity import (
    UNKNOWN_ORIGIN_PREFIX,
    _sanitize_origin,
    resolve_origin_key,
)
from app.models.memory import MemoryBuffer
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.auto_research import (
    ORIGIN_ID_MAX_LEN,
    RESEARCH_SOURCE,
    ResearchBudget,
    ResearchFinding,
    is_researched_origin,
    research_origin_id,
    research_origin_key,
    run_research,
)
from app.services.triple_key import compute_triple_key
from app.services.verification_ladder import decide, get_ladder_config

PROJECT = "t308-research-origins"
NOW = datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc)
ENABLED = ResearchBudget(enabled=True, max_findings_per_run=20, max_content_chars=8000)

# One page, and every spelling of it a fetcher hands back on its own: the
# scheme it was redirected to, the host casing DNS does not care about, the
# `www.` alias, the default port, the credentials in the fetcher's config, the
# fragment the search result carried, the campaign parameters the link had, the
# parameter order a query builder chose.
ONE_PAGE = (
    "https://example.test/docs/pgvector",
    "http://example.test/docs/pgvector",
    "HTTPS://Example.TEST/docs/pgvector",
    "https://www.example.test/docs/pgvector/",
    "https://example.test:443/docs/pgvector",
    "https://example.test/docs//pgvector",
    "https://crawler:secret@example.test/docs/pgvector",
    "https://example.test/docs/pgvector#installation",
    "https://example.test/docs/pgvector?utm_source=newsletter&utm_medium=email",
    "https://example.test/docs/pgvector?fbclid=abc123",
    "//example.test/docs/pgvector",
    "example.test/docs/pgvector",
    "  https://example.test/docs/pgvector  ",
)

ANOTHER_PAGE = "https://other.test/blog/pgvector-notes"


def _finding(text: str = "evidence", source_id: str | None = None) -> ResearchFinding:
    return ResearchFinding(content=text, source_id=source_id)


async def _buffer_origin_keys(session) -> list[str]:
    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    return [row.metadata_["origin_key"] for row in rows]


async def _fact(session) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(PROJECT, "pgvector", "DEPENDS_ON", "postgres"),
        subject_name="pgvector",
        object_name="postgres",
        rel_type="DEPENDS_ON",
        fact="pgvector depends on postgres",
        reference_time=NOW,
        project=PROJECT,
    )
    return row["id"]


async def _cite(session, fact_id: str, *, ref: str, origin: str | None, at: datetime):
    """Record one researched memory as a source of ``fact_id`` at ``at``.

    ``fact_sources.created_at`` carries a server default, so the ladder's time
    gate can only be exercised by rewriting it after the row lands.
    """
    row = await FactSourceRepository(session).add_source(
        fact_id=fact_id, source_kind="memory", source_ref=ref, origin_key=origin,
    )
    await session.execute(
        text(
            "UPDATE fact_sources SET created_at = CAST(:when AS timestamptz) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"when": at, "id": row["id"]},
    )


class TestOneSourceIsOneOrigin:
    def test_every_spelling_of_one_page_is_one_origin(self):
        ids = {research_origin_id(_finding(source_id=spelling)) for spelling in ONE_PAGE}
        assert len(ids) == 1, f"one page split into {len(ids)} origins: {sorted(ids)}"
        assert ids == {"example.test/docs/pgvector"}

    def test_the_raw_source_ids_really_do_differ(self):
        """The kill vector for the assertion above.

        Every collapse test passes trivially against an implementation that
        returns ``source_id`` unchanged if the fixture only ever holds one
        spelling. This one fails in that world, so the collapse above is
        evidence of canonicalisation rather than of a thin fixture.
        """
        assert len(set(ONE_PAGE)) == len(ONE_PAGE)

    def test_query_parameters_that_identify_the_document_are_kept(self):
        """Dropping every parameter would merge a site into one origin.

        The rule is merge-on-doubt, not merge-on-everything: a campaign
        parameter is a referral and goes, a content parameter is the address
        and stays.
        """
        first = research_origin_id(_finding(source_id="https://example.test/p?id=1"))
        second = research_origin_id(_finding(source_id="https://example.test/p?id=2"))
        assert first != second

        reordered = research_origin_id(
            _finding(source_id="https://example.test/p?b=2&a=1&utm_source=x")
        )
        assert reordered == research_origin_id(
            _finding(source_id="https://example.test/p?a=1&b=2")
        )

    def test_two_genuinely_different_sources_are_two_origins(self):
        assert research_origin_id(_finding(source_id=ONE_PAGE[0])) != research_origin_id(
            _finding(source_id=ANOTHER_PAGE)
        )

    def test_a_non_url_document_id_is_an_identity_too(self):
        """Doc 09 §6 says *document, page or dataset* — a DOI is a source."""
        doi = research_origin_id(_finding(source_id="10.1000/xyz123"))
        assert doi == "10.1000/xyz123"
        assert doi != research_origin_id(_finding(source_id="10.1000/xyz124"))
        assert research_origin_id(_finding(source_id=" 10.1000/XYZ123 ")) == doi

    @pytest.mark.asyncio
    async def test_refetching_one_page_does_not_increase_the_origin_count(self, session):
        """Done-when 1, end to end through the capture door.

        Three findings, one page, three different spellings — one origin on the
        rows the buffer actually holds.
        """
        gatherer = _StubGatherer([
            _finding("first pass", ONE_PAGE[0]),
            _finding("second pass, redirected", ONE_PAGE[1]),
            _finding("third pass, from a search result", ONE_PAGE[7]),
        ])
        result = await run_research(
            session, subject="pgvector", project=PROJECT,
            gatherer=gatherer, budget=ENABLED,
        )
        assert result.filed == 3

        keys = await _buffer_origin_keys(session)
        assert len(keys) == 3
        assert len(set(keys)) == 1, f"a refetch minted a second origin: {set(keys)}"
        assert set(keys) == {f"{RESEARCH_SOURCE}:example.test/docs/pgvector"}

    @pytest.mark.asyncio
    async def test_two_runs_over_one_page_share_the_origin(self, session):
        """The per-run counterfeit, refused where it would be minted.

        A run id is available at the call site and would be the easy identity
        to reach for; two runs over one page are one source fetched twice, so
        the second run must add no origin.
        """
        for _ in range(2):
            await run_research(
                session, subject="pgvector", project=PROJECT,
                gatherer=_StubGatherer([_finding("evidence", ONE_PAGE[0])]),
                budget=ENABLED,
            )
        keys = await _buffer_origin_keys(session)
        assert len(keys) == 2
        assert len(set(keys)) == 1

    @pytest.mark.asyncio
    async def test_a_paraphrase_of_one_page_adds_no_origin(self, session):
        """Doc 09 §6's third clause: one source written up as two notes."""
        gatherer = _StubGatherer([
            _finding("pgvector stores fixed-dimension vectors.", ONE_PAGE[0]),
            _finding("Vectors in pgvector have a fixed dimension.", ONE_PAGE[0]),
        ])
        await run_research(
            session, subject="pgvector", project=PROJECT,
            gatherer=gatherer, budget=ENABLED,
        )
        assert len(set(await _buffer_origin_keys(session))) == 1


class TestRfc3986EquivalenceIsOneOrigin:
    """The classes RFC 3986 §6.2.2-6.2.3 call one identifier.

    Found by T3.08's adversarial review, which falsified the merge-only claim
    with six splitting inputs. These are not exotic spellings: `httpx` — this
    repo's own client — percent-encodes a non-ASCII path, so a gatherer storing
    `str(response.url)` and one storing the scraped href hand back two spellings
    of one page. Two such variants ≥ 7 days apart were two attributable origins,
    which is `required_n = 2`, which is a promotion manufactured off one page.
    """

    @pytest.mark.parametrize("left,right,why", [
        ("https://example.test/café", "https://example.test/caf%C3%A9",
         "percent-encoded non-ASCII path"),
        ("https://example.test/~user", "https://example.test/%7Euser",
         "percent-encoded unreserved character"),
        ("https://example.test/abc", "https://example.test/%61bc",
         "percent-encoded ASCII letter"),
        ("https://example.test/x/../docs/pg", "https://example.test/docs/pg",
         "dot-segment resolution"),
        ("https://bücher.example/a", "https://xn--bcher-kva.example/a",
         "IDN unicode against its punycode"),
        ("https://example.test/a?x=1", "https://example.test/a?x=1&x=1",
         "a duplicated identical parameter"),
    ])
    def test_one_page_under_two_spellings_is_one_origin(self, left, right, why):
        left_id = research_origin_id(_finding(source_id=left))
        right_id = research_origin_id(_finding(source_id=right))
        assert left_id is not None, why
        assert left_id == right_id, f"{why} split one source into two origins"

    def test_the_nfc_and_nfd_spellings_of_one_host_agree(self):
        """Two Unicode forms of one name, which a filesystem or a clipboard
        can each hand back."""
        composed = unicodedata.normalize("NFC", "https://café.example/a")
        decomposed = unicodedata.normalize("NFD", "https://café.example/a")
        assert composed != decomposed, "the fixture must really differ"
        assert research_origin_id(_finding(source_id=composed)) == \
            research_origin_id(_finding(source_id=decomposed))

    @pytest.mark.parametrize("left,right", [
        ("https://example.test/a?id=1", "https://example.test/a?id=2"),
        ("https://example.test/docs/a", "https://example.test/docs/b"),
        ("https://example.test/a?x=1&y=2", "https://example.test/a?x=1"),
    ])
    def test_the_merging_does_not_reach_genuinely_distinct_pages(self, left, right):
        """The control on the fix: merge-only must not become merge-everything.
        Dropping every parameter would collapse a site into one origin and the
        loop could never corroborate anything."""
        assert research_origin_id(_finding(source_id=left)) != research_origin_id(_finding(source_id=right))


class TestTheMergeOnlyClaimAfterTheSecondFalsification:
    """v0.5's version review falsified "merge-only by construction" again.

    T3.08's own review closed six splitting inputs and the claim was restated
    as absolute in `CHANGELOG.md`, `CLAUDE.md` and the function's docstring. A
    second adversarial pass found **eleven** more splits over 26 same-source
    pairs, of which ten are mechanical variation a fetcher or a scraper
    produces on its own. Two clear T3.08's own "this repo's `httpx` produces
    it" bar: the client emits IDNA2008 punycode while this module normalised
    through Python's IDNA2003 codec, so one page under its unicode and its
    fetched spelling was two attributable origins — which is `required_n = 2`
    at seven days' spacing, a promotion manufactured off one page.

    The lesson recorded with the fixture: an invariant asserted as "by
    construction" has now been falsified twice by the first party to attack it
    deliberately. These pins are what the phrase is allowed to rest on.
    """

    @pytest.mark.parametrize("left,right,why", [
        ("https://straße.example/a", "https://xn--strae-oqa.example/a",
         "IDNA2008 deviation character against the punycode httpx emits"),
        ("https://βόλος.example/a", "https://xn--nxasmm1c.example/a",
         "IDNA final-sigma deviation, against the punycode httpx emits"),
        ("https://example.test.:443/a", "https://example.test/a",
         "trailing-dot FQDN carrying an explicit default port"),
        ("https://example.test:0443/a", "https://example.test/a",
         "a default port written with a leading zero"),
        ("https://[2001:db8::1]/a", "https://[2001:db8:0:0:0:0:0:1]/a",
         "IPv6 zero-compression against its expanded form"),
        ("https:example.test/a", "https://example.test/a",
         "a scheme-relative href written without its slashes"),
        ("https://exa\nmple.test/a", "https://example.test/a",
         "an embedded newline, which the URL spec strips"),
        ("https://example.test/a\tb", "https://example.test/ab",
         "an embedded tab, likewise"),
        ("https://example.test/%2e%2e/a", "https://example.test/a",
         "percent-encoded dot-segments popping past the root"),
    ])
    def test_one_page_under_two_spellings_is_still_one_origin(self, left, right, why):
        left_id = research_origin_id(_finding(source_id=left))
        right_id = research_origin_id(_finding(source_id=right))
        assert left_id is not None, why
        assert left_id == right_id, f"{why} split one source into two origins"

    def test_the_opaque_fallback_normalises_before_it_gives_up(self):
        """An id `urlsplit` refuses still has to reach one form.

        The fallback returned the **pre-NFC** value, so a locator that could not
        be parsed split on Unicode spelling alone — the one path where the
        normalisation this module does first was thrown away.
        """
        composed = unicodedata.normalize("NFC", "café℀z")
        decomposed = unicodedata.normalize("NFD", "café℀z")
        assert composed != decomposed, "the fixture must really differ"
        assert research_origin_id(_finding(source_id=composed)) == \
            research_origin_id(_finding(source_id=decomposed))

    @pytest.mark.parametrize("left,right,why", [
        ("https://example.test:8443/a", "https://example.test/a",
         "a non-default port is part of the identity"),
        ("https://strasse.example/a", "https://straße.example/a",
         "a genuinely different host that IDNA2003 would have conflated"),
        ("https://[2001:db8::1]/a", "https://[2001:db8::2]/a",
         "two different addresses"),
        ("urn:isbn:0451450523", "urn:isbn:451450523",
         "a non-URL id whose digits sit where a port would: normalising them "
         "through int() drops the leading zero and merges two identifiers"),
        ("https://xn--nxasmm1c.example/a", "https://xn--nxasmq6b.example/a",
         "the IDNA2003 spelling of a final-sigma host decodes to a different "
         "label and is a different domain under IDNA2008"),
        ("https://example.test/a?x=1;y=2", "https://example.test/a?x=1&y=2",
         "`;` is not a separator a fetcher substitutes — servers may serve "
         "different content, so these stay two"),
    ])
    def test_the_repairs_did_not_become_merge_everything(self, left, right, why):
        """The control, widened with the fix.

        Over-merging is the safe direction for a *gate* — an undercount delays
        a promotion — but it is not free: merge everything and the loop can
        never corroborate anything at all. Each pair here must stay two.
        """
        assert research_origin_id(_finding(source_id=left)) != \
            research_origin_id(_finding(source_id=right)), why


class TestUnknownIdentity:
    @pytest.mark.parametrize("unestablished", [None, "", "   ", "\t\n", "://", "///", "..."])
    def test_an_identity_that_cannot_be_established_merges(self, unestablished):
        assert research_origin_id(_finding(source_id=unestablished)) is None

    def test_a_non_string_source_id_merges_rather_than_raising(self):
        """Attribution must not fail a write, and the gatherer is out of tree."""
        assert research_origin_id(ResearchFinding(content="c", source_id=object())) is None

    @pytest.mark.asyncio
    async def test_unknown_identity_collapses_per_the_t1_11_rule(self, session):
        """Done-when 3. The bucket is the capture layer's, not a second one.

        ``unknown:<source>:<project>`` is what ``resolve_origin_key`` mints for
        an undeclared identity on every other door, and ``fact_sources`` folds
        every ``unknown:``-prefixed key into one reserved bucket per fact that
        counts once and fires no gate. Minting an attributable key here — even
        a shared one — would put those rows *outside* that bucket, where one of
        them could supply the source-kind or time gate that drops N from 3 to
        2 alongside a single real witness.
        """
        gatherer = _StubGatherer([_finding(f"note {i}", None) for i in range(3)])
        await run_research(
            session, subject="pgvector", project=PROJECT,
            gatherer=gatherer, budget=ENABLED,
        )
        keys = set(await _buffer_origin_keys(session))
        assert keys == {f"{UNKNOWN_ORIGIN_PREFIX}:{RESEARCH_SOURCE}:{PROJECT}"}
        assert keys == {
            resolve_origin_key(None, None, source=RESEARCH_SOURCE, project=PROJECT)
        }

    def test_an_unestablished_identity_never_reaches_an_attributable_key(self):
        merged = research_origin_key(_finding(source_id=None), project=PROJECT)
        assert merged.startswith(f"{UNKNOWN_ORIGIN_PREFIX}:")
        declared = research_origin_key(_finding(source_id=ONE_PAGE[0]), project=PROJECT)
        assert not declared.startswith(f"{UNKNOWN_ORIGIN_PREFIX}:")
        assert merged != declared


class TestTheIdSurvivesTheCaptureLayer:
    """What this module emits has to be what lands, or the seam proves nothing."""

    HOSTILE = (
        *ONE_PAGE,
        ANOTHER_PAGE,
        "research:api",
        f"{UNKNOWN_ORIGIN_PREFIX}:api:{PROJECT}",
        "https://example.test:8080/a",
        "http://[::1]:8080/x",
        "10.1000/xyz123",
        " My Doc  1 ",
        "https://example.test/" + "a" * 400,
        "https://exaаmple.test/a",
        "line\x00break",
        "‮emdirtfel",
    )

    @pytest.mark.parametrize("raw", HOSTILE)
    def test_the_id_is_a_fixed_point_of_the_capture_layers_sanitizer(self, raw):
        """``_sanitize_origin`` must have nothing left to do.

        It strips ``:`` from a declared id — the removal that stops a caller
        forging a second key segment from outside — and truncates at 128. An id
        it rewrote would mean the identity this module computed and the identity
        the count sees are different strings, and the collapse tests above would
        be measuring the wrong one.
        """
        origin_id = research_origin_id(_finding(source_id=raw))
        if origin_id is None:
            return
        assert _sanitize_origin(origin_id) == origin_id
        assert ":" not in origin_id
        assert len(origin_id) <= ORIGIN_ID_MAX_LEN

    def test_an_over_long_locator_merges_rather_than_being_cut_loose(self):
        """Truncation is a merge, which is the direction that undercounts."""
        long_ids = {
            research_origin_id(_finding(source_id=f"https://example.test/{'a' * 400}{tail}"))
            for tail in ("one", "two")
        }
        assert len(long_ids) == 1
        assert len(long_ids.pop()) == ORIGIN_ID_MAX_LEN

    def test_a_gatherer_cannot_inject_a_second_key_segment(self):
        """The colon is the key's own separator; an id may not carry one."""
        forged = research_origin_key(_finding(source_id="api:claude-code"), project=PROJECT)
        assert forged.count(":") == 1
        assert forged.startswith(f"{RESEARCH_SOURCE}:")


class TestManufacturedOriginsStayVisible:
    def test_the_declared_form_is_recognised_as_researched(self):
        for spelling in (*ONE_PAGE, ANOTHER_PAGE, "10.1000/xyz123"):
            key = research_origin_key(_finding(source_id=spelling), project=PROJECT)
            assert is_researched_origin(key), key

    def test_a_researched_origin_never_looks_like_a_human_capture(self):
        """The slice has to hold against real keys, not only against itself.

        Forgery may only run in the widening direction: a human capture that
        declared ``source=research`` gets marked manufactured, which costs a
        measurement nothing, while a researched capture that shed its marker
        would silently pool with observed origins.
        """
        for human in (
            resolve_origin_key(None, None, source="api", project=PROJECT),
            resolve_origin_key(None, None, source="mcp", project=PROJECT),
            resolve_origin_key("boot-uuid", None, source="claude-code", project=PROJECT),
            resolve_origin_key("boot-uuid", None, source="codex", project=PROJECT),
            resolve_origin_key(
                "example.test/docs/pgvector", None, source="api", project=PROJECT,
            ),
        ):
            assert not is_researched_origin(human), human

    @pytest.mark.asyncio
    async def test_every_row_of_a_run_carries_the_marker(self, session):
        gatherer = _StubGatherer([
            _finding("a", ONE_PAGE[0]), _finding("b", ANOTHER_PAGE), _finding("c", None),
        ])
        await run_research(
            session, subject="pgvector", project=PROJECT,
            gatherer=gatherer, budget=ENABLED,
        )
        keys = await _buffer_origin_keys(session)
        assert len(keys) == 3
        assert all(is_researched_origin(key) for key in keys)


class TestCorroborationOutcome:
    """Done-when 2, against the ladder itself rather than a proxy for it.

    The counting layer is ``fact_sources`` and the decision is
    ``verification_ladder.decide``; asserting on the stamped keys alone would
    prove the ids differ without proving that a difference in ids is what moves
    a fact. Both tests below hold the fact, the kinds and the timing fixed and
    vary only the origin identity this task computes.
    """

    @pytest.mark.asyncio
    async def test_two_independent_sources_promote_the_fact(self, session):
        fact_id = await _fact(session)
        for index, page in enumerate((ONE_PAGE[0], ANOTHER_PAGE)):
            await _cite(
                session, fact_id,
                ref=f"memory-{index}",
                origin=research_origin_key(_finding(source_id=page), project=PROJECT),
                at=NOW + timedelta(days=7 * index),
            )
        profile = await FactSourceRepository(session).origin_profile(fact_id)
        decision = decide(fact_id, "candidate", profile, await get_ladder_config(session))

        assert profile.origin_count == 2
        assert not profile.has_unknown_origin, "both origins must be attributable"
        assert (decision.required_n, decision.gate_fired) == (2, "time_gap")
        assert decision.outcome == "promote"
        assert decision.target_status == "corroborated"

    @pytest.mark.asyncio
    async def test_one_page_fetched_twice_does_not_promote_the_fact(self, session):
        """The twin of the test above: same fact, same kinds, same seven-day
        spread, two capture rows — and one origin, so no promotion."""
        fact_id = await _fact(session)
        for index, spelling in enumerate((ONE_PAGE[0], ONE_PAGE[3])):
            await _cite(
                session, fact_id,
                ref=f"memory-{index}",
                origin=research_origin_key(_finding(source_id=spelling), project=PROJECT),
                at=NOW + timedelta(days=7 * index),
            )
        profile = await FactSourceRepository(session).origin_profile(fact_id)
        decision = decide(fact_id, "candidate", profile, await get_ladder_config(session))

        assert profile.origin_count == 1, "a refetch bought a second origin"
        assert decision.outcome == "hold"
        assert decision.target_status == "candidate"

    @pytest.mark.asyncio
    async def test_three_same_day_sources_promote_at_the_undiverse_bar(self, session):
        """No time gap and no kind diversity, so N is 3 — and three genuinely
        distinct pages reach it. This is the shape a single research run can
        produce on its own, which is why the collapse rules above are the only
        thing standing between one page and a promotion."""
        fact_id = await _fact(session)
        pages = (ONE_PAGE[0], ANOTHER_PAGE, "https://third.test/pgvector")
        for index, page in enumerate(pages):
            await _cite(
                session, fact_id,
                ref=f"memory-{index}",
                origin=research_origin_key(_finding(source_id=page), project=PROJECT),
                at=NOW,
            )
        profile = await FactSourceRepository(session).origin_profile(fact_id)
        decision = decide(fact_id, "candidate", profile, await get_ladder_config(session))

        assert (profile.origin_count, decision.required_n) == (3, 3)
        assert decision.outcome == "promote"

    @pytest.mark.asyncio
    async def test_the_merged_bucket_still_cannot_lower_the_bar(self, session):
        """An unestablished identity beside one real witness holds at N = 3.

        This is the property the merge preserves and an attributable
        unknown-identity key would have destroyed: the bucket counts toward K
        and supplies neither gate, so it can never pair with a single source to
        reach the diversity bar.
        """
        fact_id = await _fact(session)
        await _cite(
            session, fact_id, ref="memory-0",
            origin=research_origin_key(_finding(source_id=ONE_PAGE[0]), project=PROJECT),
            at=NOW,
        )
        await _cite(
            session, fact_id, ref="memory-1",
            origin=research_origin_key(_finding(source_id=None), project=PROJECT),
            at=NOW + timedelta(days=30),
        )
        profile = await FactSourceRepository(session).origin_profile(fact_id)
        decision = decide(fact_id, "candidate", profile, await get_ladder_config(session))

        assert (profile.origin_count, decision.required_n) == (2, 3)
        assert decision.outcome == "hold"


class _StubGatherer:
    """The capability that lives outside darkmem's box, standing still."""

    def __init__(self, findings):
        self.findings = findings

    async def gather(self, subject: str, *, limit: int):
        return self.findings
