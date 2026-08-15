# Origin canonicalisation — handover to a fresh implementer

**Dispatch brief, 2026-08-15.** Written by the party that failed at this three
times in a row. Read the failure pattern before the task, because the pattern is
the more useful of the two.

## The one-sentence problem

`research_origin_id` (`backend/app/services/auto_research.py`) turns a
gatherer's `source_id` into an origin identity. Corroboration counts
`COUNT(DISTINCT origin_key)`, so **an input that splits one source into two ids
fabricates a witness** — two attributable origins seven days apart is
`required_n = 2`, which is a promotion off a single page. Over-merging is the
safe direction (an undercount only delays a promotion) but is not free: merge
everything and the loop can never corroborate anything.

## The failure pattern, which is why you are being handed this

The merge-only property has been **falsified four times, by every party that
attacked it deliberately, and never once by its author's own tests.**

| Round | Found by | What it found |
|---|---|---|
| T3.08 review | adversarial review | 6 splitting inputs, each a spelling this repo's `httpx` produces |
| v0.5 version review | adversarial review | 9 more over 26 same-source pairs, incl. IDNA2003-vs-2008 |
| rescope 1 | adversarial review | the repair **relocated** the ordering bug; and *created* an IDN+port split |
| rescope 2 | adversarial review | the repair's scheme fold **created** a `file:` split |

**Three consecutive repairs introduced the failure class they were closing.**
That is the signal. Each fix was locally reasonable, each was pinned by
red-first tests, each passed a green floor, and each was wrong in a way its
author could not see. Assume the same is true of whatever you write first.

Two related notes on the author's own reasoning, recorded because they are
instructive rather than to flagellate: the phrase "merge-only **by
construction**" appeared in `CLAUDE.md`, `CHANGELOG.md` and the docstring and
was false every time it was written — it has since been retired in favour of
"tested property with named pins". And the current open finding is an
inconsistency *inside a comment the author wrote*: it cites `file:///` as the
reason not to fold three slashes, while the one-slash fold it ships destroys
that same empty authority for the spelling `httpx` actually emits.

## What is open

1. **Finding B (Important, open).** `_SCHEME_NO_SLASHES_RE`
   (`auto_research.py:109`) folds `scheme:` and `scheme:/` to `scheme://`.
   `str(httpx.URL("file:///tmp/a.pdf"))` returns `'file:/tmp/a.pdf'`, so that
   fold yields `tmp/a.pdf` — inventing `tmp` as a host — while the three-slash
   spelling yields `/tmp/a.pdf`. One file, two origins. RFC 8089 makes them one
   resource. Second witness: `https:///example.test/a` versus the `https:/…`
   spelling regressed merge→split in the same change.
   **No scheme-agnostic slash rule is correct for both `https:` and `file:`.**
2. **A surviving mutant (coverage gap, minor).** Dropping the port suffix on the
   **IPv6 return path only** passes all 82 tests — nothing pairs an
   IPv6-with-port against its portless spelling.
3. **`CHANGELOG.md`'s v0.5 line 34** ("collapses the variation a fetcher
   produces mechanically") is falsified at the margin by Finding B's pairs. It
   must be true or reworded before the release is cut.

## What is explicitly invited

**Do not assume a fourth round of spelling-by-spelling patching is the answer.**
It is the approach that has now failed three times. Two alternatives are
sanctioned, and choosing one over another patch is a legitimate outcome of this
task:

- **A property test over generated URL spellings** — generate variations
  mechanically (case, slashes, ports, IDN forms, percent-encoding, dot-segments,
  Unicode normalisation), assert the identity collapses, and let the generator
  find what hand-written pairs keep missing. The known-good pairs stay as
  regression pins.
- **Delegate canonicalisation to a library that has already litigated these
  cases**, rather than re-deriving URL equivalence by hand. Check what is
  actually available in the lock before proposing this; the constraint is that
  it must not *split*, and a library tuned for something other than identity may
  do so happily.

If you conclude the current shape is right and only Finding B needs closing,
that is an acceptable answer — but say why the pattern above does not apply,
rather than not mentioning it.

## Constraints, non-negotiable

- **No bar moves**, in any direction. Nothing in this task touches
  `promotion_bars.py` or the verification ladder.
- **Do not arm the loop.** `auto_research` stays disabled; no config-row writer
  may appear in the tree. Nothing here is operationally live today, which is why
  this is a correctness-and-honesty task rather than an incident.
- **Merge-only is a direction, not a licence to merge everything.** The
  over-merge controls in `tests/test_research_origins.py` are load-bearing:
  `urn:isbn:0451450523` vs `urn:isbn:451450523` must stay two, a non-default
  port must stay part of the identity, and two punycode labels decoding to
  different strings are different hosts.
- **Red-first pins for every repair**, and mutation-drill each one. The tests
  that missed three rounds of defects were all written after the fact was
  believed rather than before it was checked.
- `./scripts/gate.sh` must be green before you are done. Run it on a quiet host:
  this box has 8 GB and vitest forks per core, so a loaded run times out the
  frontend step for reasons no diff caused.
- **Do not cut the release.** `v0.5` is drafted and unreleased on purpose.

## Artifacts

- Reports, in order: `docs/planning/reviews/2026-08-15-v0.5-version-review.md`
  (Finding 1), `.../2026-08-15-t3.08-origin-fix-rescope.md` (round 1),
  `.../2026-08-15-t3.08-origin-fix-rescope-2.md` (round 2). The original T3.08
  review has no standalone file; its findings are in `progress.md`'s `T3.08` row.
- The adversarial driver both reviewers used:
  `/tmp/claude-0/-root-repositories-darkmem/20c90966-191c-49f9-9fb1-2bd4adb7e3b6/scratchpad/origin_attack.py`
  (currently 2 splits / 24 merges; **both survivors are adjudicated correct** —
  `;` vs `&` is not fetcher-produced variation, and the driver's own final-sigma
  fixture pairs `βόλος` with `σόλοσ`, two different hosts).
- Tests: `backend/tests/test_research_origins.py`,
  `backend/tests/test_auto_research.py` (125 passing).

## Verify

`cd backend && .venv/bin/python -m pytest tests/test_research_origins.py tests/test_auto_research.py -q`,
then `./scripts/gate.sh`. Never two pytest sessions at once — the suites share
databases and a collision produces failures indistinguishable from real ones.
