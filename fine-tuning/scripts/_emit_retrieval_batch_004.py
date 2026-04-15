"""One-off emitter for retrieval top-up batch-004 — acronym-kind queries slice.

Writes 100 rows to data/v2/retrieval/batch_004.tmp.jsonl with ids ret-00301..00400.
Each row references a source row in shared.jsonl at lines SHARED_OFFSET+1..SHARED_OFFSET+100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_004.tmp.jsonl"
ID_OFFSET = 300
SHARED_OFFSET = 300
QUERY_KIND = "acronym"

QUERIES: list[str] = [
    # 301 npm install / CI / sh / bash
    "why did npm i fail scripts on CI image with sh",
    # 302 Playwright over Cypress for e2e
    "picked PW over Cypress for e2e tests; parallel browsers",
    # 303 ESLint v9 flat config migration, monorepo
    "ESLint v9 flat cfg migration across monorepo completion date",
    # 304 Rust Book ownership chapter
    "Rust Book ownership ch for noob onboarding wk 1",
    # 305 Vercel preview URL per PR
    "PR preview URL via Vercel bot comment on green CI",
    # 306 Flutter hot reload / riverpod
    "Flutter HR broken post riverpod bump, provider scope outside app",
    # 307 pytest --pdb flag
    "pytest --pdb flag enters debugger when in a run",
    # 308 dataclasses over attrs, frozen True
    "prefer dataclasses over attrs w/ frozen=True for invariants",
    # 309 Sentry breadcrumb auto-capture
    "disabled Sentry bc auto-capture after quota blown on bad deploy",
    # 310 noise
    "FYI lmk when you wanna move on",
    # 311 mypy CI cache
    "mypy OK locally, CI FAIL due to stale dep sig in cache",
    # 312 reranker nDCG 0.85 milestone
    "FT reranker crossed 0.85 nDCG on 2026-03-29",
    # 313 TanStack Router / TanStack Query
    "FE uses TSR file-based routes + TSQ for server state",
    # 314 Pact -> OpenAPI
    "migrated API contract checks from Pact to OAS validators",
    # 315 Playwright modal timeout
    "PW test hung on modal close anim vs default TO",
    # 316 golangci-lint testifylint
    "golangci-lint needs testifylint enabled for test lints",
    # 317 bisect, print, debugger order
    "debug order: git bisect, then print, then debugger IDE",
    # 318 services structured JSON to stdout
    "svcs log JSON to stdout, container RT ships to collector",
    # 319 SWR pagination stale cursor
    "SWR cached stale cursor after pagination back-click bug",
    # 320 jscodeshift React.FC codemod
    "JS codemod moved from React.FC to explicit prop types",
    # 321 feature branches named by ticket-id
    "prefer branch names w/ ticket-id over slug for tracker link",
    # 322 Nx affected graph build time
    "cold build 14 min to 3 min 40 s using Nx affected on 2026-04-02",
    # 323 Kent Beck TDD book, code review
    "Kent Beck's TDD book anchors CR vocab on fake-it-till-you-make-it",
    # 324 ALTER TABLE lock migration timeout
    "DB migration TO on staging; ALTER TABLE serial under default lock",
    # 325 pnpm workspaces / Turborepo / changesets
    "monorepo stack: pnpm WS + Turbo + changesets for versioning",
    # 326 trunk-based development feature flags
    "adopted TBD with FF after long-lived branches stopped merging",
    # 327 Python match statements over elif
    "Py match stmt over elif chain for JSON shape matching",
    # 328 GraphQL codegen nullability Apollo
    "GQL codegen all-optional types since Apollo schema lacked NN",
    # 329 Node.js worker threads SharedArrayBuffer
    "Node WT share mem via SAB, not structured clone",
    # 330 React 19 migration
    "FE moved to React 19 on 2026-01-20 with zero runtime regressions",
    # 331 tests co-located, pre-commit hook
    "tests colocated with src; pre-commit hook rewrites imports",
    # 332 Vitest over Jest with Vite
    "Vitest over Jest for Vite-based pkgs; same API, faster startup",
    # 333 Django migration squash rolled back
    "Django migration squash dropped BC shim, rolled back on staging",
    # 334 Zen of Python in code review
    "Zen of Py still quoted in CR for unneeded abstractions",
    # 335 XState vs bespoke reducers
    "XState over hand-rolled reducers for FSM; visualiser ROI",
    # 336 pytest-asyncio strict mode
    "pytest-asyncio strict mode forces explicit event_loop_policy fx",
    # 337 git worktrees
    "git worktrees let multiple branches share one object DB",
    # 338 Dependabot jsonwebtoken JWT
    "Dependabot bumped jsonwebtoken, default alg flip broke JWT verify",
    # 339 API gateway OpenAPI-first, Git
    "API GW uses OAS-first; contracts in Git, stubs gen on merge",
    # 340 Husky -> lefthook
    "swapped Husky for lefthook; parallel hooks + nicer cfg",
    # 341 CI matrix 8 min median
    "CI matrix under 10 min median on 2026-03-14 after flaky quarantine",
    # 342 asyncio.Queue unbounded OOM
    "unbounded asyncio.Queue OOM'd worker; no BP from producers",
    # 343 TS noUncheckedIndexedAccess
    "TS noUncheckedIndexedAccess covers idx sigs, not tuples",
    # 344 Typer over argparse
    "Typer over argparse for new CLIs; decorators beat manual wiring",
    # 345 Clean Architecture dependency rule
    "Clean Arch dep rule shapes intra-svc import direction",
    # 346 SQLAlchemy selectinload vs joined loading
    "SA selectinload worsened N+1; joined loading fixed the ORM query",
    # 347 Storybook / Chromatic preview per PR
    "CI posts SB preview per PR; design review via Chromatic pre-merge",
    # 348 Pylint -> Ruff
    "linting moved from Pylint to Ruff; startup 11 s -> 300 ms",
    # 349 tree-sitter code search
    "shipped TS-based code search repo-wide on 2026-04-05 for CR quotes",
    # 350 Docker multi-stage cache lockfile
    "Docker multi-stage cached stale node_modules; lockfile skipped in COPY",
    # 351 pottery class, Camden, Priya
    "started ceramics class Tue PM at Camden studio w/ Priya",
    # 352 sourdough vs banana bread
    "SD loaf over banana bread as wknd bake focus",
    # 353 Mom's tiramisu recipe blue index card
    "Mom's TM recipe on blue idx card taped in kitchen drawer",
    # 354 knee brace, Dolomites
    "knee brace helped on the Dolomites PT vacation hike",
    # 355 Osteria Francescana 2026-07-04 anniversary
    "anniversary dinner booked at OF Modena for 2026-07-04",
    # 356 gratitude list Moleskine bedside
    "nightly 3-entry gratitude list in bedside Moleskine nb",
    # 357 early-morning coffee balcony over indoor breakfast
    "prefer AM coffee on balcony over indoor brekkie",
    # 358 Uncle Ben 2024 family reunion estranged
    "Uncle B silent since 2024 fam reunion; waiting for him to DM first",
    # 359 grain-free dog kibble vet recommendation
    "vet Rx'd grain-free kibble for dog's skin flare; 2-wk switch",
    # 360 noise
    "hmm give me a sec to think about that, brb",
    # 361 Mum 70th 2028-05-12 Rachel
    "Mum's 70th bday on 2028-05-12; Rachel organising surprise w/ cousins",
    # 362 07:15 bus over underground
    "commute moved to 07:15 bus from the tube; daylight wins",
    # 363 rooibos over black tea
    "PM brew: rooibos over black; no caffeine, no 3 PM crash",
    # 364 Dad Kodak slides 1970s attic
    "Dad's 70s Kodak slides in attic trunk; first box DG'd last summer",
    # 365 pilates instructor Nadia standing desk
    "pilates instructor Nadia rec'd sit-stand desk for LBP",
    # 366 garden tomatoes 2026-06-22
    "garden tom harvest first basket on 2026-06-22, two wks early",
    # 367 Jake Lisbon apartment September
    "Jake's new Lisbon apt has spare rm; Sept visit sketched",
    # 368 foster kitten replaces second adult cat plan
    "foster kitten replaced plan for a 2nd adult cat this spring",
    # 369 Jess Barcelona trip cancelled
    "Jess cxl'd the BCN trip; work ext'd contract, rebooked for late fall",
    # 370 Audible over Storytel
    "Audible > Storytel for audiobooks; bigger lib + better VAs",
    # 371 Sam holiday gift tradition 2021
    "w/ Sam since 2021: 1 xp + 1 DIY gift, no shop-bought",
    # 372 meditation streak day 143
    "fell off meditation streak @ day 143; restarted count on Mon",
    # 373 Nigella chocolate olive oil cake Notion Jamie
    "saved Nigella choc OO cake in shared Notion; Jamie's go-to bday bake",
    # 374 Mum Lisbon assisted-living 2025-10-12
    "helped Mum move into Lisbon AL flat on 2025-10-12; settled fast",
    # 375 quiet Saturdays over long brunches
    "prefer quiet Sat at home over long brunches; 3 hr reading > chit-chat",
    # 376 Wednesday yoga replaced by pilates
    "Wed yoga class swapped for pilates after studio reno",
    # 377 Friday chess club King's Indian defence
    "joined Fri PM chess club at CC; pulled out my old KID defence",
    # 378 Rufus 5th birthday 2026-03-11
    "Rufus turned 5 on 2026-03-11; cardboard crown bday pics",
    # 379 grandfather clock Aunt Rosa estate
    "hallway GF clock came from Aunt Rosa's estate; ~1 min/wk drift",
    # 380 personal newsletter issue 24
    "dropped the personal newsletter after iss #24; readership flat",
    # 381 paper log replaces phone app treadmill
    "paper log replaced the app for logging treadmill pace",
    # 382 Dr. Singh Maya braces 2026-05-07
    "ped dentist Dr. Singh booked Maya's braces consult for 2026-05-07",
    # 383 Grandpa Navy letters 1953 1957
    "finally read Grandpa's Navy letters from '53 to '57",
    # 384 noise
    "1 sec, gonna pull up the right pg first",
    # 385 board games over video games Catan
    "kids prefer board games to vid games on fam night; ~3 Catan/mo",
    # 386 Hip MRI 2026-04-03 labral wear
    "hip MRI on 2026-04-03 showed mild labral wear; ortho said no OR",
    # 387 Jamie Easter lunch alternate years
    "Easter lunch: Jamie's fam @ noon, mine in PM, alternating yrs",
    # 388 Lisbon vs Barcelona autumn trip
    "autumn trip: Lisbon flat at 1/3 BCN's price; booking tmrw",
    # 389 Clara quinces membrillo
    "neighbour Clara dropped off qnc basket Sun; membrillo turned out great",
    # 390 1000km running 2026-04-09
    "hit my 1000 km run total on 2026-04-09; celebratory 5k by the river",
    # 391 Sam airport drop-offs pickups
    "Sam and I split apt runs; I do DOs, he does pickups",
    # 392 Christmas tree Epiphany
    "Xmas tree stays up til Epiphany; kids decorate, adults light, no solo teardown",
    # 393 fast fashion second-hand
    "killed FF shopping 2 yrs ago; all new clothes are 2nd-hand or vintage",
    # 394 arthritis right thumb physio grip exercises
    "pepper grinder pain = arthritis in R thumb; PT Rx'd grip drills",
    # 395 Ben Van Gogh Amsterdam 2025-09-18
    "took Ben to VG show in AMS on 2025-09-18; Wheatfield w/ Crows stuck",
    # 396 tea cupboard loose leaf steel tins
    "tea cupboard redo; all loose leaf now in labelled SS tins",
    # 397 Tokyo language exchange Yuki Sapporo
    "Fri Tokyo lang exchange went online after Yuki moved to Sapporo",
    # 398 hand-written thank-you cards over texts
    "prefer hand-written TY cards over SMS for real gifts",
    # 399 Mum's carrot cake birthday standard
    "Mum's carrot cake = the bday std for me; no subs even from bakeries",
    # 400 gym membership cancelled outdoor workouts
    "cxl'd gym and moved to outdoor WO in the park; saved 40 GBP",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with SHARED_PATH.open("r", encoding="utf-8") as f:
        source_lines = f.readlines()

    rows = []
    for i, query in enumerate(QUERIES):
        shared_line_idx = SHARED_OFFSET + i
        source_row = json.loads(source_lines[shared_line_idx])
        source_id = source_row["id"]
        positive = source_row["text"]

        row_id = f"ret-{ID_OFFSET + i + 1:05d}"
        rows.append({
            "id": row_id,
            "source_id": source_id,
            "query": query,
            "positive": positive,
            "query_kind": QUERY_KIND,
        })

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
