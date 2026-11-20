"""Extraction F1 benchmark.

Measures entity + relation precision/recall/F1 of the **shipping** extraction
request against gold.json. The request is assembled by
``ExtractionService.build_extraction_request`` — the same function the pipeline
uses — so the bench cannot drift into scoring a configuration nobody runs.

The model call is cached per full assembled request (system message + user
message, which carries the schema string and the merge gate), so iterating on
the deterministic algorithm (``clean_extraction``) re-scores instantly without
re-calling the model. Changing the prompt, the schema, the taxonomy width or
the gate state invalidates the cache automatically, and ``--algo-only`` refuses
to replay a cache whose manifest no longer describes the current assembly.

Run from the backend/ directory:
    python scripts/extraction_bench/run_bench.py            # full (LLM + algo)
    python scripts/extraction_bench/run_bench.py --diffs    # also print per-memory diffs
    python scripts/extraction_bench/run_bench.py --algo-only  # error if any LLM output is uncached
"""
import argparse
import asyncio
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, BACKEND)
CACHE = os.path.join(HERE, ".cache")
MANIFEST = os.path.join(CACHE, "manifest.json")
os.makedirs(CACHE, exist_ok=True)

from app.database import async_session_factory  # noqa: E402
from app.services.config import get_llm_config  # noqa: E402
from app.services.llm import LLMOrchestrator  # noqa: E402
from app.services import prompt as prompt_constants  # noqa: E402
from app.services.extraction import ExtractionService  # noqa: E402
from app.services.extraction_clean import (  # noqa: E402
    clean_extraction, _build_extraction_schema,
)

# The gate ledger fixes the model for parity: a run on ``deepseek-v4-pro`` is
# not comparable to the recorded floors and must not be used for one.
PINNED_MODEL = "deepseek-v4-flash"

# A change is positive proof of a serving-stack swap, which would fold fresh
# vendor drift into whatever delta this bench is being used to measure.
#
# Rotated 2026-08-27. The prior value
# (``fp_8b330d02d0_prod0820_fp8_kvcache_20260402``, measured stable across
# lane D's 159 live calls on 2026-07-28) stopped being served; the value
# below was measured stable across five consecutive probes on 2026-08-27.
# The rotation is why the same-stack re-baseline exists: a prompt delta
# measured against the 2026-07-27 numbers would carry the vendor's drift
# inside it, so the floors were re-recorded on this stack with the prompt
# unchanged before any prompt edit was measured.
EXPECTED_SYSTEM_FINGERPRINT = "a26a7955944dc5c60445bff77fac9c8e"

GATES = {"merged": True, "extract-only": False}


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def request_cache_key(request) -> str:
    """Key the cache on the whole assembled request, not just the prompt.

    The schema string, the taxonomy width and the merge gate all ride the
    *user* message. Keying on the system message alone silently replays
    outputs produced by a request the code would no longer send.
    """
    payload = json.dumps(request.messages, ensure_ascii=False, sort_keys=True)
    return _sha16(payload)


def assembly_identity(with_classification: bool) -> dict:
    return {
        "prompt_sha16": _sha16(prompt_constants.get("extraction")),
        "schema_sha16": _sha16(_build_extraction_schema(with_classification=with_classification)),
        "with_classification": with_classification,
    }


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", BACKEND, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def load_manifest() -> dict | None:
    if not os.path.exists(MANIFEST):
        return None
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def write_manifest(with_classification: bool, gate: str, model: str,
                   gold_file: str, fingerprints: set[str]) -> None:
    prior = load_manifest() or {}
    identity = assembly_identity(with_classification)
    gold_files = sorted(set(prior.get("gold_files", [])) | {gold_file})
    prints = sorted(set(prior.get("system_fingerprints", [])) | fingerprints)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump({
            **identity,
            "gate": gate,
            "model": model,
            "git_sha": _git_sha(),
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "gold_files": gold_files,
            "system_fingerprints": prints,
        }, fh, indent=2, sort_keys=True)


def assert_manifest_current(with_classification: bool, gate: str) -> None:
    """Refuse to replay a cache that no longer describes the current assembly."""
    manifest = load_manifest()
    if manifest is None:
        raise SystemExit(
            "--algo-only but the cache has no manifest.json. The cache predates the "
            "shipping-path rework; restore a dated archive from docs/eval/ or re-record live."
        )
    identity = assembly_identity(with_classification)
    mismatches = [
        f"  {field}: manifest={manifest.get(field)!r} current={value!r}"
        for field, value in {**identity, "gate": gate}.items()
        if manifest.get(field) != value
    ]
    if mismatches:
        raise SystemExit(
            "--algo-only but the cached generation does not describe the current "
            "extraction assembly:\n" + "\n".join(mismatches) +
            "\nRe-record live, or restore the matching archive from docs/eval/."
        )


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def ent_keys(ents, with_type):
    out = set()
    for e in ents:
        n = _norm(e.get("name"))
        if not n:
            continue
        out.add((n, _norm(e.get("type"))) if with_type else (n,))
    return out


def rel_keys(rels, with_type):
    out = set()
    for r in rels:
        s, t = _norm(r.get("source")), _norm(r.get("target"))
        if not s or not t:
            continue
        out.add((s, (r.get("type") or "").upper(), t) if with_type else (s, t))
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def read_entry(payload: dict) -> dict:
    """Return the raw extraction dict from a cache entry.

    Entries recorded before response-metadata capture are a bare raw dict;
    current ones are ``{"raw": ..., "meta": ...}``.
    """
    if isinstance(payload, dict) and "raw" in payload and "meta" in payload:
        return payload["raw"]
    return payload


async def get_raw(svc, content, *, with_classification, algo_only, expect_fingerprint, seen):
    request = ExtractionService.build_extraction_request(
        content, with_classification=with_classification,
    )
    key = request_cache_key(request)
    cf = os.path.join(CACHE, key + ".json")
    if os.path.exists(cf):
        with open(cf, encoding="utf-8") as fh:
            return read_entry(json.load(fh))
    if algo_only:
        raise SystemExit(f"--algo-only but no cached LLM output for: {content[:60]!r}")
    raw, meta = await svc.extract_raw(
        content, with_classification=with_classification, return_meta=True,
    )
    fingerprint = (meta or {}).get("system_fingerprint")
    if expect_fingerprint and fingerprint != expect_fingerprint:
        raise SystemExit(
            f"system_fingerprint changed mid-measurement: expected "
            f"{expect_fingerprint!r}, served {fingerprint!r}. The serving stack "
            "rotated; every delta measured across this boundary carries fresh "
            "vendor drift. Stop and re-attribute before recording anything."
        )
    seen.add(fingerprint)
    with open(cf, "w", encoding="utf-8") as fh:
        json.dump({
            "raw": raw,
            "meta": {**(meta or {}),
                     "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
        }, fh, ensure_ascii=False)
    return raw


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diffs", action="store_true", help="print per-memory relation diffs")
    ap.add_argument("--algo-only", action="store_true", help="fail if any LLM output is uncached")
    ap.add_argument("--gold", default="gold.json", help="gold file under this dir")
    ap.add_argument("--gate", default="merged", choices=sorted(GATES),
                    help="extraction gate state to measure (default: the shipping default)")
    ap.add_argument("--expect-fingerprint", default=EXPECTED_SYSTEM_FINGERPRINT,
                    help="pinned served-stack fingerprint; empty string disables the check")
    args = ap.parse_args()

    with_classification = GATES[args.gate]

    with open(os.path.join(HERE, args.gold), encoding="utf-8") as fh:
        gold = json.load(fh)["memories"]

    svc = None
    model = None
    if args.algo_only:
        assert_manifest_current(with_classification, args.gate)
        model = (load_manifest() or {}).get("model")
    else:
        async with async_session_factory() as session:
            cfg = await get_llm_config(session)
        model = cfg["extraction"].model
        if model != PINNED_MODEL:
            raise SystemExit(
                f"extraction model is {model!r} but the gate ledger pins {PINNED_MODEL!r}; "
                "a run on another model is not comparable to the recorded floors. "
                "Seed the purpose rows (benchlib.run_smoke.seed_llm_purpose_configs) and "
                "point DATABASE_URL at the bench database."
            )
        svc = ExtractionService(LLMOrchestrator(cfg))

    identity = assembly_identity(with_classification)
    print("================ RUN HEADER ================")
    print(f"  gold file        : {args.gold}")
    print(f"  gate             : {args.gate} (with_classification={with_classification})")
    print(f"  model            : {model}")
    print(f"  system prompt    : sha256[:16]={identity['prompt_sha16']}")
    print(f"  schema           : sha256[:16]={identity['schema_sha16']}")
    print(f"  mode             : {'algo-only (cached raw)' if args.algo_only else 'live'}")
    print(f"  git sha          : {_git_sha()}")

    fingerprints: set[str] = set()
    # micro counters: dim -> [tp, fp, fn]
    dims = {"ent_nt": [0, 0, 0], "ent_n": [0, 0, 0], "rel_full": [0, 0, 0], "rel_pair": [0, 0, 0]}
    per_mem = []
    for g in gold:
        raw = await get_raw(
            svc, g["content"], with_classification=with_classification,
            algo_only=args.algo_only, expect_fingerprint=args.expect_fingerprint,
            seen=fingerprints,
        )
        pred = clean_extraction(raw, g["content"], relation_rescue=True)
        pe, pr = pred.get("entities", []), pred.get("relationships", [])

        ge_nt, pe_nt = ent_keys(g["entities"], True), ent_keys(pe, True)
        ge_n, pe_n = ent_keys(g["entities"], False), ent_keys(pe, False)
        gr_f, pr_f = rel_keys(g["relations"], True), rel_keys(pr, True)
        gr_p, pr_p = rel_keys(g["relations"], False), rel_keys(pr, False)

        for dim, (gset, pset) in {"ent_nt": (ge_nt, pe_nt), "ent_n": (ge_n, pe_n),
                                  "rel_full": (gr_f, pr_f), "rel_pair": (gr_p, pr_p)}.items():
            tp = len(gset & pset); fp = len(pset - gset); fn = len(gset - pset)
            dims[dim][0] += tp; dims[dim][1] += fp; dims[dim][2] += fn

        def f1p(gset, pset):  # F1, treating both-empty as perfect
            if not gset and not pset:
                return 1.0
            return prf(len(gset & pset), len(pset - gset), len(gset - pset))[2]
        per_mem.append((g["id"], f1p(ge_nt, pe_nt), f1p(gr_f, pr_f),
                        ge_nt - pe_nt, pe_nt - ge_nt, gr_f - pr_f, pr_f - gr_f))

    if not args.algo_only:
        write_manifest(with_classification, args.gate, model, args.gold, fingerprints)
        print(f"  served fingerprint: {sorted(fingerprints)}")

    print("\n================ PER-MEMORY (entity F1 / relation F1) ================")
    for mid, ef, rf, emiss, eextra, miss, extra in per_mem:
        flag = "" if (rf >= 0.8 and ef >= 0.8) else "  <--"
        print(f"  {mid:<5} ent={ef:.2f}  rel={rf:.2f}{flag}")
        if args.diffs:
            for m in sorted(emiss):
                print(f"        ENT MISS : {m[0]} :{m[1]}")
            for x in sorted(eextra):
                print(f"        ENT SPUR : {x[0]} :{x[1]}")
            for m in sorted(miss):
                print(f"        REL MISS : {m[0]} -{m[1]}-> {m[2]}")
            for x in sorted(extra):
                print(f"        REL SPUR : {x[0]} -{x[1]}-> {x[2]}")

    print("\n================ AGGREGATE (micro) ================")
    labels = {"ent_nt": "Entity (name+type)", "ent_n": "Entity (name only)",
              "rel_full": "Relation (s,TYPE,t)", "rel_pair": "Relation (s,t) type-agnostic"}
    measured = {}
    for dim, lab in labels.items():
        tp, fp, fn = dims[dim]
        p, r, f = prf(tp, fp, fn)
        measured[dim] = f
        print(f"  {lab:<32} P={p:.3f} R={r:.3f} F1={f:.3f}   (tp={tp} fp={fp} fn={fn})")

    _assert_floors(measured, labels)


# The four gold-corpus floors, from the G-B ledger row (T1.50, 2026-07-28).
# These are not new numbers and carry no new tolerance: T0.05 set the parity
# tolerance on 2026-07-26, *before* Phase 1 opened, and these floors are that
# tolerance already applied to the recorded baseline. Enforcing them here
# changes nothing about what G-B decided; it changes only whether a later
# regression can pass unnoticed.
GOLD_F1_FLOORS = {
    "ent_nt": 0.881,
    "ent_n": 0.910,
    "rel_full": 0.784,
    "rel_pair": 0.811,
}


def _assert_floors(measured: dict[str, float], labels: dict[str, str]) -> None:
    """Fail the run when a dimension drops below its recorded floor.

    Until 2026-08-08 this script printed the cells and exited 0 unconditionally,
    so ``./scripts/gate.sh``'s "extraction F1 bench" arm could fail on a cache
    miss, a manifest mismatch or a crash — but never on the number it names. A
    reader seeing GATE GREEN reasonably concludes F1 is healthy; nothing was
    checking. That is the completion-gate-masquerading-as-a-measurement-gate
    shape, and it is the arm most likely to be trusted blind.
    """
    breaches = [
        (labels[dim], measured[dim], floor)
        for dim, floor in GOLD_F1_FLOORS.items()
        if measured.get(dim, 0.0) < floor
    ]
    if not breaches:
        print(f"\n  floors: all {len(GOLD_F1_FLOORS)} dimensions at or above "
              f"the G-B recorded floors")
        return
    lines = "\n".join(
        f"    {lab:<32} F1={value:.3f} < floor {floor:.3f}"
        for lab, value, floor in breaches
    )
    raise SystemExit(
        f"\nEXTRACTION F1 BELOW THE RECORDED FLOOR ({len(breaches)} of "
        f"{len(GOLD_F1_FLOORS)} dimensions):\n{lines}\n\n"
        "  These floors are the T0.05 parity tolerance applied to the G-B\n"
        "  baseline; see gate-ledger.md's G-B row. Do not widen them to make\n"
        "  a run pass — the ledger says so explicitly. Triage with --diffs."
    )


if __name__ == "__main__":
    asyncio.run(main())
