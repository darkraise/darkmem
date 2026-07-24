"""Reference side of the .NET benchlib spike.

Produces reference.json + prompt.txt for the C# program to reproduce bit-for-bit:
- the extraction bench's exact cache keys (sha256(content + "\\x00" + prompt)[:16])
  against the REAL Python-built cache under backend/scripts/extraction_bench/.cache
- the exact 4-dimension micro P/R/F1 scoring of run_bench.py, applied to the raw
  cached LLM outputs vs gold.json (raw, so no clean_extraction dependency — the
  scorer parity is what the spike must prove; the cleanup passes are ported later
  and will be measured BY this scorer).

The ent_keys/rel_keys/prf/f1p functions are faithful copies from
backend/scripts/extraction_bench/run_bench.py (importing run_bench pulls app
database imports; the copies are 25 lines and byte-comparable by eye).
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[3] / "backend"
BENCH = BACKEND / "scripts" / "extraction_bench"
sys.path.insert(0, str(BACKEND))

from app.services import prompt as prompt_constants  # noqa: E402


def _norm(s):
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


def f1p(gset, pset):
    if not gset and not pset:
        return 1.0
    return prf(len(gset & pset), len(pset - gset), len(gset - pset))[2]


system_prompt = prompt_constants.get("extraction")
(HERE / "prompt.txt").write_bytes(system_prompt.encode("utf-8"))

gold = json.loads((BENCH / "gold.json").read_text(encoding="utf-8"))["memories"]

dims = {"ent_nt": [0, 0, 0], "ent_n": [0, 0, 0], "rel_full": [0, 0, 0], "rel_pair": [0, 0, 0]}
per_mem = []
hits = 0
for g in gold:
    key = hashlib.sha256((g["content"] + "\x00" + system_prompt).encode("utf-8")).hexdigest()[:16]
    cf = BENCH / ".cache" / f"{key}.json"
    entry = {"id": g["id"], "key": key, "cached": cf.exists()}
    if cf.exists():
        hits += 1
        raw = json.loads(cf.read_text(encoding="utf-8"))
        pe, pr = raw.get("entities", []) or [], raw.get("relationships", []) or []
        ge_nt, pe_nt = ent_keys(g["entities"], True), ent_keys(pe, True)
        ge_n, pe_n = ent_keys(g["entities"], False), ent_keys(pe, False)
        gr_f, pr_f = rel_keys(g["relations"], True), rel_keys(pr, True)
        gr_p, pr_p = rel_keys(g["relations"], False), rel_keys(pr, False)
        for dim, (gs, ps) in {"ent_nt": (ge_nt, pe_nt), "ent_n": (ge_n, pe_n),
                              "rel_full": (gr_f, pr_f), "rel_pair": (gr_p, pr_p)}.items():
            tp = len(gs & ps); fp = len(ps - gs); fn = len(gs - ps)
            dims[dim][0] += tp; dims[dim][1] += fp; dims[dim][2] += fn
        entry["ent_f1"] = f1p(ge_nt, pe_nt)
        entry["rel_f1"] = f1p(gr_f, pr_f)
    per_mem.append(entry)

out = {
    "prompt_sha16": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16],
    "gold_count": len(gold), "cache_hits": hits,
    "dims": {d: {"tp": v[0], "fp": v[1], "fn": v[2],
                 "p": prf(*v)[0], "r": prf(*v)[1], "f1": prf(*v)[2]} for d, v in dims.items()},
    "per_memory": per_mem,
}
(HERE / "reference.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"gold={len(gold)} cache_hits={hits}")
for d, v in out["dims"].items():
    print(f"  {d:<9} P={v['p']:.3f} R={v['r']:.3f} F1={v['f1']:.3f} (tp={v['tp']} fp={v['fp']} fn={v['fn']})")
