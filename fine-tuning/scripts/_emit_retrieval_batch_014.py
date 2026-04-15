"""One-off emitter for retrieval top-up batch-014 — hard-negative kind, target shared rows at line offsets 1300..1399.

Writes 100 rows to data/v2/retrieval/batch_014.tmp.jsonl with ids ret-01301..01400.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_014.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 1300
SHARED_OFFSET = 1300
QUERY_KIND = "hard-negative"

# One (query, negative_line_offset) per target row, in target-row order.
# `query` is about the TARGET row; `negative_line_offset` points to a different shared row
# whose text is topically close but does not answer the query.
ENTRIES: list[tuple[str, int]] = [
    # 1300 shared-01301 ESLint kept on legacy React, Biome on new services
    ("Why did legacy React apps stay on ESLint while new services picked Biome?", 1339),
    # 1301 shared-01302 Oxlint 800 ms vs ESLint 42 s
    ("How long did Oxlint take to scan the repo compared to ESLint?", 1302),
    # 1302 shared-01303 Prefer Biome over Oxlint; conservative autofixes
    ("Why do we prefer Biome over Oxlint for linting right now?", 1301),
    # 1303 shared-01304 prettier-plugin-tailwindcss sorts classes
    ("What tool sorts Tailwind class names into canonical order to end review nits?", 1312),
    # 1304 shared-01305 Rome deprecation caught us mid-migration, fork kept config compatible
    ("How did Rome's deprecation in favor of Biome impact our in-flight migration?", 1321),
    # 1305 shared-01306 TypeScript project references on 14-package monorepo
    ("How did TypeScript project references help the 14-package monorepo build?", 1317),
    # 1306 shared-01307 SWC cut CI test compile from 38s to 6s
    ("How much did SWC cut the CI test compile step time?", 1350),
    # 1307 shared-01308 esbuild minimal plugin API, SVG loader 80 lines
    ("How many lines did our esbuild SVG-to-component loader take?", 1310),
    # 1308 shared-01309 Rollup tree-shaking kept lodash helpers until sideEffects:false
    ("Why did Rollup tree-shaking fail to drop unused lodash helpers at first?", 1336),
    # 1309 shared-01310 NOISE second monitor for config files
    ("What offhand remark was made about needing a second monitor?", 1383),
    # 1310 shared-01311 Vite plugin ecosystem covered SSR, PWA, MDX via Rollup API
    ("Which needs did Vite's plugin ecosystem cover without custom code?", 1334),
    # 1311 shared-01312 PostCSS 8 plugin order: autoprefixer before cssnano misfired
    ("Why did our PostCSS 8 pipeline run vendor expansion on already-minified output?", 1339),
    # 1312 shared-01313 Tailwind JIT, content-path glob scope affects startup
    ("What performance pitfall do Tailwind JIT content globs create?", 1303),
    # 1313 shared-01314 CSS Modules beat styled-components on critical path
    ("Why did we choose CSS Modules over styled-components for the critical path?", 1337),
    # 1314 shared-01315 tsconfig paths worked in IDE but broke at Node runtime; tsc-alias fixed it
    ("How did we fix tsconfig paths breaking at Node runtime?", 1326),
    # 1315 shared-01316 pnpm dlx and bunx cache more aggressively than npx
    ("Which runners replaced npx with more aggressive caching?", 1318),
    # 1316 shared-01317 Corepack enforces packageManager field; CI rejects mismatches
    ("How does Corepack now enforce the lockfile's packageManager field?", 1321),
    # 1317 shared-01318 Rush with phased builds handles 80-package monorepo better than Turborepo
    ("Why did Rush's phased builds win over Turborepo on our 80-package monorepo?", 1330),
    # 1318 shared-01319 pnpm patch to fix a third-party type
    ("How did we patch a broken type in a third-party SDK without blocking?", 1322),
    # 1319 shared-01320 Yarn PnP migration stalled on Jest/Webpack resolver gaps
    ("What stalled the Yarn PnP migration and forced a rollback to node-modules?", 1318),
    # 1320 shared-01321 Deno npm compat fails on native addons; argon2 and better-sqlite3 excluded
    ("Which packages do we keep out of Deno scripts because of native addons?", 1321),
    # 1321 shared-01322 Bun binary lockfile unreadable; switched to text mode
    ("Why did we switch Bun install from the binary lockfile to the text lockfile?", 1319),
    # 1322 shared-01323 Cargo workspaces and proc-macro sub-workspace fix
    ("How did we resolve circular dep warnings on our proc-macro crate in Cargo?", 1323),
    # 1323 shared-01324 cargo tree --duplicates found serde minor-version drift
    ("What cargo command surfaced the four minor-version drifts of serde?", 1322),
    # 1324 shared-01325 Go //go:build directives migration on 2026-01-18
    ("When did we finish replacing Go // +build comments with //go:build directives?", 1330),
    # 1325 shared-01326 Python packaging settled on pyproject.toml with Hatchling
    ("What backend did our Python packaging settle on with pyproject.toml?", 1345),
    # 1326 shared-01327 Java module path split-package errors trace to missing module-info.java
    ("What recurring Java module-path issue comes back to a missing module-info?", 1328),
    # 1327 shared-01328 Moved Gradle build scripts to Kotlin DSL for IntelliJ autocomplete
    ("Why did we move Gradle build scripts from Groovy DSL to Kotlin DSL?", 1328),
    # 1328 shared-01329 Maven BOMs solved transitive version drift
    ("How did Maven BOMs fix transitive version drift for platform consumers?", 1327),
    # 1329 shared-01330 Rolldown experimental; stable on ESM, chokes on CJS dynamic require
    ("Why is Rolldown still parked for us despite working on ESM libraries?", 1310),
    # 1330 shared-01331 Lerna-to-Nx migration wrapped 2026-02-24; CI from 18 min to 7 min
    ("When did the Lerna to Nx migration finish and what did it save?", 1317),
    # 1331 shared-01332 source-map-explorer found moment.js locales; date-fns saved 180 KB
    ("How did we find moment.js locales bloating the production bundle?", 1336),
    # 1332 shared-01333 Switched to hidden-source-map with Sentry uploader
    ("Why did we move from inline to hidden source maps with an uploader?", 1335),
    # 1333 shared-01334 esm.sh CDN bundling for prototypes needed CSP allowance
    ("Which CDN bundler did we use for zero-install prototype demos?", 1310),
    # 1334 shared-01335 Snowpack influence on modern dev servers
    ("What Snowpack ideas live on in modern dev servers?", 1340),
    # 1335 shared-01336 Vite plugin rewrites import.meta.env for env-per-feature branches
    ("How do preview deploys target the right API without rebuilding?", 1310),
    # 1336 shared-01337 rollup-plugin-visualizer treemap showed the 2 MB vendor chunk owners
    ("What tool pinpointed owners of the 2 MB vendor chunk in five minutes?", 1331),
    # 1337 shared-01338 Parcel chosen over Vite for internal dashboard
    ("Why did we pick Parcel over Vite for the internal dashboard?", 1338),
    # 1338 shared-01339 rspack replaced Webpack on legacy admin with 3-line config change
    ("How painful was the rspack migration replacing Webpack on the admin app?", 1337),
    # 1339 shared-01340 Stylelint still wins for CSS rules until Biome catches up
    ("Why do we still run Stylelint as a second lint pass alongside Biome?", 1300),
    # 1340 shared-01341 Turbopack dev HMR stays under 50 ms on 200k-LOC Next app
    ("How fast is Turbopack dev-server HMR on our 200k-LOC Next app?", 1306),
    # 1341 shared-01342 tsup published dual ESM/CJS with one config block and exports map
    ("Which tool let us publish dual ESM and CJS builds from a single config?", 1348),
    # 1342 shared-01343 GitHub Actions pnpm-store cache hit went 40% to 92% via key change
    ("How did we raise GitHub Actions pnpm-store cache hit rate from 40% to 92%?", 1330),
    # 1343 shared-01344 Stopped pinning exact versions; caret ranges plus lockfile
    ("Why did we stop pinning exact versions in package.json?", 1321),
    # 1344 shared-01345 GraalVM native-image Kotlin CLI startup 600 ms to 15 ms
    ("How much did GraalVM native-image cut Kotlin CLI startup time?", 1346),
    # 1345 shared-01346 Python wheels ABI3 tags; CI matrix shrank by four rows
    ("How did Python ABI3 wheel tags shrink our CI matrix?", 1325),
    # 1346 shared-01347 cargo-nextest 32 s vs cargo test 110 s
    ("How much faster is cargo-nextest than cargo test on our suite?", 1323),
    # 1347 shared-01348 Dropped husky to lefthook, then to lazygit hooks on small repos
    ("Which git hook manager are we using on the smallest repos now?", 1342),
    # 1348 shared-01349 TS 5.5 isolatedDeclarations halved declaration emit time
    ("What did the TypeScript 5.5 isolatedDeclarations flag change for us?", 1305),
    # 1349 shared-01350 Babel kept only for ancient Android WebViews where SWC fails
    ("Why do we still keep Babel around for one use case?", 1306),
    # 1350 shared-01351 Turned down staff engineer offer at Helvetia Analytics 2026-01-22
    ("Why did I turn down the Helvetia Analytics staff engineer offer?", 1351),
    # 1351 shared-01352 Negotiated base 165k to 182k at Torrent Labs by waiting 12 days
    ("How did I negotiate the Torrent Labs base salary up from 165k?", 1395),
    # 1352 shared-01353 Priya performance review flagged meeting-heavy calendar
    ("What did Priya flag as the main drag on my deep-work output in the review?", 1388),
    # 1353 shared-01354 Colin standoff after roadmap meeting; HR mediation
    ("How did the three-week standoff with Colin end?", 1384),
    # 1354 shared-01355 Mentoring Jules weekly for two quarters
    ("Why did I agree to mentor Jules for the next two quarters?", 1392),
    # 1355 shared-01356 Parental leave 2026-07-15, twenty weeks with Hamza
    ("When does my parental leave start and how is it split with Hamza?", 1368),
    # 1356 shared-01357 Sabbatical application 2025-09-18 for three months late 2026
    ("What did the 2025-09-18 sabbatical application request?", 1355),
    # 1357 shared-01358 Four days a week at Meridian from 2026-03-01, 22% cut
    ("What pay cut came with dropping to four days a week at Meridian?", 1367),
    # 1358 shared-01359 Career pivot to technical writing, Marigold course 2026-02-10
    ("What course did I sign up for as part of the tech comms pivot?", 1366),
    # 1359 shared-01360 NOISE offer letter pull-up
    ("What brief aside about pulling up the offer letter happened?", 1309),
    # 1360 shared-01361 Director all-hands keynote 2026-04-03 in Austin, 340 people
    ("How many people were in the room for the Austin director keynote?", 1390),
    # 1361 shared-01362 Office moved to Rosemont, 52-min train beats 40-min drive on bad weather
    ("How did the Rosemont office move change my commute math?", 1379),
    # 1362 shared-01363 Prefers remote Tuesdays and Thursdays
    ("Which two weekdays do I prefer fully remote?", 1386),
    # 1363 shared-01364 Orchid Systems side consulting capped at 8 hours/week
    ("What is the cap on my Orchid Systems side consulting hours?", 1387),
    # 1364 shared-01365 WIC Chicago 2025-11-12 reconnected with Maya from 2019 Kellogg cohort
    ("Who did I reconnect with at the WIC Chicago chapter in November 2025?", 1365),
    # 1365 shared-01366 Franco from 2017 grad program, Barcelona fintech product role
    ("What role is Franco from the 2017 grad program considering me for?", 1387),
    # 1366 shared-01367 PMP exam on 2026-05-04 after three-year delay
    ("When did I finally schedule the PMP exam?", 1380),
    # 1367 shared-01368 Healthcare SaaS to renewable energy after Lumeris sale
    ("Why does moving from healthcare SaaS into renewable energy feel right?", 1398),
    # 1368 shared-01369 Returning to Torrent Labs 2026-08-04, phased three-day ramp
    ("What ramp-up schedule did I get returning to Torrent Labs?", 1355),
    # 1369 shared-01370 Vanguard projection 2026-02-28, earliest retirement 57
    ("What earliest retirement age did the Vanguard projection show?", 1397),
    # 1370 shared-01371 Promoted to principal at Meridian 2025-12-01; paperwork lagged 3 weeks
    ("When was I promoted to principal engineer at Meridian?", 1396),
    # 1371 shared-01372 Prefers writing reviews in one Sunday morning sitting
    ("Why do I prefer writing performance reviews in one sitting?", 1386),
    # 1372 shared-01373 Mateo 1:1 on 2025-11-30 signaled direct-report flip
    ("What did the 2025-11-30 one-on-one with Mateo signal?", 1384),
    # 1373 shared-01374 Burnout signs Q3 2025: weekends, flat affect, skipping therapy
    ("What were the signs of my Q3 2025 burnout?", 1396),
    # 1374 shared-01375 Halide Robotics board observer seat 2026-03-12, four meetings/year
    ("What were the terms of the Halide Robotics board observer seat?", 1391),
    # 1375 shared-01376 Career narrative doc in February, five years mapped with three decision points
    ("What does the February career narrative document lay out?", 1389),
    # 1376 shared-01377 Lumeris exit interview 2026-01-30 surfaced three buried items
    ("What came out of the Lumeris exit interview on 2026-01-30?", 1367),
    # 1377 shared-01378 Moved from gmail networking to Fathom CRM in 2025
    ("Why did I switch from gmail-based networking to a Fathom CRM?", 1392),
    # 1378 shared-01379 Dropped certified Scrum Master program 2025-10-22
    ("Why did I drop out of the certified Scrum Master program?", 1366),
    # 1379 shared-01380 Commute to Lombard, 45 minutes reframed as audiobook time
    ("How did I reframe the 45-minute Lombard commute into productive time?", 1361),
    # 1380 shared-01381 AWS Solutions Architect Pro on 2026-02-19, 890/1000 after Sept fail
    ("What score and certification did I get on 2026-02-19?", 1366),
    # 1381 shared-01382 Lost autumn promotion bid; feedback cited scope not quality
    ("What did the autumn promotion feedback actually point at?", 1388),
    # 1382 shared-01383 Prefers Lake Geneva quarterly offsites over remote summits
    ("Why do I prefer Lake Geneva offsites over remote summit formats?", 1362),
    # 1383 shared-01384 NOISE W-2 lookup
    ("What brief aside was about checking the W-2?", 1359),
    # 1384 shared-01385 Coaching with Annika 2026-03-27 re avoidance since Colin standoff
    ("What did the 2026-03-27 coaching session with Annika surface?", 1352),
    # 1385 shared-01386 Reports now eight after 2026-03-15 reorg; six eng plus two designers
    ("How many reports do I have after the 2026-03-15 reorg?", 1353),
    # 1386 shared-01387 Prefers Friday afternoons for thinking time
    ("What slot do I block for thinking time each week?", 1362),
    # 1387 shared-01388 Declined Barcelona role; relocation blew up parental leave timing
    ("Why did I decline the Barcelona role from Franco?", 1365),
    # 1388 shared-01389 360 results 2025-12-10 called me strategic but slow on hard calls
    ("What did my 360 results on 2025-12-10 tell me?", 1352),
    # 1389 shared-01390 Blocked first 30 min daily for solo work since 2026-01-06
    ("What morning block did I start protecting on 2026-01-06?", 1386),
    # 1390 shared-01391 ORD chapter panel on 2026-09-18 as first external panel
    ("What is my first external panel appearance as principal?", 1360),
    # 1391 shared-01392 Considered fractional CTO but health insurance math blocked it
    ("Why did I not go independent as a fractional CTO in early 2026?", 1374),
    # 1392 shared-01393 Donna's 2014 mentorship still shapes my 1:1s
    ("Whose 2014 mentorship still shapes how I run 1:1s today?", 1354),
    # 1393 shared-01394 Rahim PIP ended 2025-11-04 with exit; worst three months
    ("When did the Rahim performance improvement plan end?", 1353),
    # 1394 shared-01395 Kellogg EMBA alumni summit 2026-05-21 Evanston; Serena panel reframed next decade
    ("What reframed the next decade for me at the Kellogg alumni summit?", 1364),
    # 1395 shared-01396 Sunita caught cliff clause in Torrent equity on 2026-01-18
    ("Who caught the cliff clause in my Torrent equity package?", 1351),
    # 1396 shared-01397 Imposter feeling post-principal promotion didn't fade until week 11
    ("How long did the post-promotion imposter feeling take to fade?", 1370),
    # 1397 shared-01398 Retirement glidepath spreadsheet, target 58; 529 plans for kids parallel
    ("What age is the retirement glidepath target?", 1369),
    # 1398 shared-01399 Professional identity stapled to VP title at Lumeris; felt hollow after sale
    ("How did the Lumeris sale change my relationship with the VP title?", 1367),
    # 1399 shared-01400 Prefers market-data compensation conversations over annual 3% raises
    ("Why do I prefer market-data comp conversations over annual raise rituals?", 1343),
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    targets = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(ENTRIES) == 100
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, ((query, neg_off), tgt) in enumerate(zip(ENTRIES, targets), start=1):
            neg_row = json.loads(lines[neg_off])
            if neg_row["id"] == tgt["id"]:
                raise ValueError(f"negative row must differ from target at index {i}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": tgt["id"],
                "query": query,
                "negative": neg_row["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
