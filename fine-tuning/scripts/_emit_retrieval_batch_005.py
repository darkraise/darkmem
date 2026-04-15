"""One-off emitter for retrieval top-up batch-005 — acronym queries for shared rows 400-499.

Writes 100 rows to data/v2/retrieval/batch_005.tmp.jsonl with ids ret-00401..00500.

Each query uses at least one acronym, abbreviation, or shortform (technical or
non-technical) that maps to the source row's content. Queries are 3-15 words.
Schema: {id, source_id, query, positive, query_kind="acronym"}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_005.tmp.jsonl"

ID_OFFSET = 400
SHARED_OFFSET = 400
QUERY_KIND = "acronym"

# One acronym-laden query per source row (shared rows 400-499, zero-indexed).
QUERIES: list[str] = [
    # 400 — shared-00401 — second law of thermodynamics
    "2nd law of thermo entropy in an iso system",
    # 401 — shared-00402 — Dawkins Selfish Gene replicator
    "Dawkins TSG reframed evo around replicator",
    # 402 — shared-00403 — preregistration
    "prereg locks the analysis plan pre data collection",
    # 403 — shared-00404 — scientific method cycle
    "sci method OHE A R cycle explained",
    # 404 — shared-00405 — p-hacking
    "NHST p-hacking via many tests reporting sig",
    # 405 — shared-00406 — ATLAS CMS Higgs 2012-07-04
    "ATLAS and CMS announce Higgs discovery date",
    # 406 — shared-00407 — SciPy vs MATLAB preference
    "prefers SciPy over MATLAB for repro collab stack",
    # 407 — shared-00408 — Godel incompleteness
    "Godel's 1st incompleteness thm on undecidable stmts",
    # 408 — shared-00409 — Kuhn paradigm shifts
    "Kuhn's SSR introduced paradigm shifts vocab",
    # 409 — shared-00410 — noise: look up figures
    "BRB let me check the exact figures",
    # 410 — shared-00411 — single-blind peer review
    "SBPR bias toward known author affiliations",
    # 411 — shared-00412 — Human Genome Project 2000 2003
    "HGP first draft 2000-06-26 finished seq 2003",
    # 412 — shared-00413 — randomisation vs quasi-experiments
    "RCTs preferred over quasi-exp for causal Qs",
    # 413 — shared-00414 — Avogadro's number
    "Avogadro's N counts particles in one mol",
    # 414 — shared-00415 — IRB approval
    "IRBs approve protocols pre recruitment starts",
    # 415 — shared-00416 — Nature structured abstract 200 words
    "Nature structured-abstract 200-word w/ sig line",
    # 416 — shared-00417 — researcher degrees of freedom
    "researcher DoF inflate false-pos rates invisibly",
    # 417 — shared-00418 — GLP-1 STEP trials 2021
    "GLP-1 RA class cleared STEP P3 obesity endpoints",
    # 418 — shared-00419 — double-blind single-arm
    "DBSA beats OL for subjective endpoint bias",
    # 419 — shared-00420 — Ebbinghaus forgetting curve
    "Ebbinghaus curve: unreinforced memory fades exp",
    # 420 — shared-00421 — NIH grant reviews study sections
    "NIH grant review via study section panels",
    # 421 — shared-00422 — Cochrane Handbook chapter 10
    "Cochrane Hdbk ch 10 on dichotomous outcomes",
    # 422 — shared-00423 — WEIRD-sample bias
    "WEIRD bias: psych over-relies on W.E.I.R.D. pops",
    # 423 — shared-00424 — PSR B1919+21 Jocelyn Bell Burnell
    "PSR B1919+21 detected 1967 by Bell Burnell PhD",
    # 424 — shared-00425 — variational inference vs MCMC
    "VI replaces MCMC when approx posteriors suffice",
    # 425 — shared-00426 — Zotero vs Mendeley preference
    "prefers Zotero over Mendeley for ref mgmt",
    # 426 — shared-00427 — thermodynamic arrow of time
    "thermo arrow of time ties macro dir to S growth",
    # 427 — shared-00428 — clinical trial phases 1-4
    "clinical trial phases P1 P2 P3 P4 surveillance",
    # 428 — shared-00429 — Flyvbjerg megaproject overruns
    "Flyvbjerg on megaproject overruns vs optimism bias",
    # 429 — shared-00430 — measurement invariance
    "MI must be checked pre latent score comparison",
    # 430 — shared-00431 — ENCODE 2012 80 percent
    "ENCODE 2012 annotated 80% of human genome",
    # 431 — shared-00432 — Bayesian vs NHST small sample
    "lab prefers Bayesian est over NHST at small n",
    # 432 — shared-00433 — BibTeX preference
    "prefers BibTeX over hand-typed refs auto cite",
    # 433 — shared-00434 — noise: double-check source
    "hold on gotta DC the source",
    # 434 — shared-00435 — Occam's razor
    "Occam's razor: simpler hypo wins w/ equal fit",
    # 435 — shared-00436 — systematic reviews PRISMA
    "SR stages under PRISMA: ID screen elig incl",
    # 436 — shared-00437 — Popper falsifiability 1959 LSD
    "Popper LSD 1959: falsifiability demarcates science",
    # 437 — shared-00438 — publication bias null results
    "pub bias: null results under-reported in lit",
    # 438 — shared-00439 — JWST first images 2022-07-11
    "JWST first-colour deep field galaxy imgs date",
    # 439 — shared-00440 — meta-regression continuous
    "MR replaces subgroup when moderators are cont",
    # 440 — shared-00441 — Zipf's law
    "Zipf's law: nth token freq prop 1/n in corpus",
    # 441 — shared-00442 — ERC grants two-stage panel
    "ERC grants: remote pool plus central panel IV",
    # 442 — shared-00443 — NIH open access PMC 12 months
    "NIH OA mandate: manuscripts to PMC w/in 12 mo",
    # 443 — shared-00444 — small sample NHST fails
    "NHST misbehaves at low n when dist assumptions fail",
    # 444 — shared-00445 — cryo-EM 1.8 A ribosome 2023
    "cryo-EM at 1.8 A on ribosome by Scheres 2023",
    # 445 — shared-00446 — multiple imputation MAR MCAR
    "MI for missing data under MAR or MCAR mech",
    # 446 — shared-00447 — Overleaf vs local LaTeX
    "prefers Overleaf over local TeX for joint papers",
    # 447 — shared-00448 — Shannon entropy bits
    "Shannon's H ties info to log prob in bits",
    # 448 — shared-00449 — triple-anonymised review
    "TA review hides authors revs and eds each cycle",
    # 449 — shared-00450 — OECD AI Principles 2019
    "OECD AI Principles 2019 int'l trustworthy AI frame",
    # 450 — shared-00451 — Cursor SwiftUI side project
    "Cursor completes SwiftUI view faster than I sketch",
    # 451 — shared-00452 — Whoop Grafana recovery
    "Whoop recovery scores feed a Grafana dash AM coffee",
    # 452 — shared-00453 — Vaultwarden self-hosted mom
    "self-hosted VW so mum avoids US cloud bank pwds",
    # 453 — shared-00454 — DDIA Kleppmann SQLite tree-sitter
    "DDIA by Kleppmann pushed SQLite for TS cache",
    # 454 — shared-00455 — Duolingo streak 400 Tokyo
    "Duo streak hits 400 day same AM we book TYO",
    # 455 — shared-00456 — Logseq tomato cucumber yield
    "logs veg yields in Logseq vs last szn's notes",
    # 456 — shared-00457 — RAW vs HEIC Lightroom Fuji
    "picks RAW over HEIC for LR Fuji colour headroom",
    # 457 — shared-00458 — TurboTax ITIN transposed
    "TurboTax rejected joint return: ITIN digit swap",
    # 458 — shared-00459 — Pico-8 nephew 128 pixel
    "teaching nephew via Pico-8 128-px constraint",
    # 459 — shared-00460 — noise: pull that up
    "1 sec lemme pull that up for u",
    # 460 — shared-00461 — Home Assistant Emporia Vue dryer 2kW
    "HA uses Emporia Vue to cut dryer below 2 kW PV",
    # 461 — shared-00462 — August Level Bolt Airbnb
    "swapped August smart lock for Level Bolt BnB no app",
    # 462 — shared-00463 — Google Calendar Outlook daycare
    "GCal feed shared with Outlook for daycare pickups",
    # 463 — shared-00464 — Pocket Readwise Anki Sunday
    "Pocket to Readwise to Anki cards on Sun",
    # 464 — shared-00465 — VHS Domesday Duplicator LSI capture
    "VHS rip via Domesday Duplicator and LSI capture",
    # 465 — shared-00466 — Behringer UMC204HD Ableton mini PC
    "UMC204HD feeds Ableton on mini PC bedroom rig",
    # 466 — shared-00467 — RTX 5060 Baldur's Gate Qwen fine-tune
    "RTX 5060 drives BG3 by day Qwen FT by night",
    # 467 — shared-00468 — Alexa skill manifest plaintext
    "killed Alexa routines: skill sends utterances plain",
    # 468 — shared-00469 — Cleveland Brews Shure MV7 Reaper
    "CLE Brews podcast: Shure MV7 cut in Reaper",
    # 469 — shared-00470 — Twilio Lyft ETA wife
    "Twilio auto-SMS Lyft ETA to wife past 8 PM",
    # 470 — shared-00471 — Raspberry Pi freezer Discord cron
    "RPi on freezer DMs Discord via cron below -12 C",
    # 471 — shared-00472 — Deep Work Newport 9-noon block
    "Deep Work by Newport: 9-12 focus block on cal",
    # 472 — shared-00473 — Signal vs WhatsApp Berlin team
    "prefers Signal over WA for Berlin team coord",
    # 473 — shared-00474 — iA Writer iPad Nextcloud Hugo
    "iA Writer iPad to NC then transcluded to Hugo blog",
    # 474 — shared-00475 — Scratch birthday stage retro
    "twins' Scratch b-day card froze: retro stage dims",
    # 475 — shared-00476 — noise: check notes
    "hold on lemme check my notes rn",
    # 476 — shared-00477 — Kiwix Steam Deck Patagonia
    "offline Kiwix Wiki on Steam Deck for Patagonia trek",
    # 477 — shared-00478 — Hue bridge firmware Home Assistant
    "Hue bridge lost HA devices post FW push 2026-02-07",
    # 478 — shared-00479 — Greenlight allowance bus
    "moved kids' allowance to Greenlight cards post bus loss",
    # 479 — shared-00480 — Atomic Habits 2-minute rule Git
    "AH 2-min rule drives chores and my git cadence",
    # 480 — shared-00481 — Notion Calendar Fantastical family
    "Notion Cal replaces Fantastical for family DB links",
    # 481 — shared-00482 — FreshRSS VPS Hacker News
    "FreshRSS on VPS serves HN front page each AM",
    # 482 — shared-00483 — Piper TTS Markdown dialect
    "Piper TTS reads MD bedtime stories in local dialect",
    # 483 — shared-00484 — Kindle Scribe Moleskine Whispersync
    "Scribe replaces Moleskine: WSync tags by mtg date",
    # 484 — shared-00485 — Meditations on-call runbook
    "Meditations by MA next to on-call runbook",
    # 485 — shared-00486 — medical records Bitwarden PDF
    "moved mum's med records to BW-encrypted PDF 2026-04-02",
    # 486 — shared-00487 — Zed vs Tuple Oscar Lisbon
    "prefers Zed over Tuple for OSS pairing w/ Oscar",
    # 487 — shared-00488 — Teslamate Proxmox Model 3
    "Teslamate on PVE logs every Model 3 daycare drive",
    # 488 — shared-00489 — Whisper Polish accent
    "fine-tuned local Whisper for mum's PL accent VMs",
    # 489 — shared-00490 — Kayak Google Flights Vueling
    "BER trip planned in Kayak: GFlights hides VY leg",
    # 490 — shared-00491 — Claude Code pytest SaaS
    "CC writes pytest fixtures for side SaaS project",
    # 491 — shared-00492 — Tasmota Sonoff espresso MQTT
    "Tasmota Sonoff tracks espresso warm-up via MQTT",
    # 492 — shared-00493 — Peloton Apple Fitness Plus
    "cancelled Peloton: AF+ fits dad lunch window",
    # 493 — shared-00494 — Leila Polish Duolingo 2026-03-11
    "Leila read first PL sentence 2026-03-11 post Duo",
    # 494 — shared-00495 — Karpathy micrograd niece
    "Karpathy's micrograd taught niece matrix calc SB",
    # 495 — shared-00496 — Kagi replaces Google search
    "Kagi replaces Google as default SE no-ads ethos",
    # 496 — shared-00497 — Sonos hearing aids Radio 4
    "dad's HAs pair to Sonos for BBC R4 at parity vol",
    # 497 — shared-00498 — Toronto meetup homelab cookbook 2026-06-30
    "homelab cookbook deadline 2026-06-30 for YYZ meetup",
    # 498 — shared-00499 — Reolink Frigate Synology
    "Reolink doorbell scrubbed via Frigate pre NAS sync",
    # 499 — shared-00500 — embedder fine-tune dehumidifier breaker
    "embedder FT 2026-04-14 died: dehumidifier tripped breaker",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    for i, q in enumerate(QUERIES):
        word_count = len(q.split())
        assert 3 <= word_count <= 15, (
            f"queries[{i}] has {word_count} words (must be 3-15): {q!r}"
        )

    source_rows: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f):
            if line_no < SHARED_OFFSET:
                continue
            if line_no >= SHARED_OFFSET + 100:
                break
            source_rows.append(json.loads(line))
    assert len(source_rows) == 100, (
        f"expected 100 source rows at offset {SHARED_OFFSET}, got {len(source_rows)}"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(source_rows, QUERIES), start=1):
            row_id = f"ret-{ID_OFFSET + i:05d}"
            row = {
                "id": row_id,
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
