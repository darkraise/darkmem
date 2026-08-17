"""Drive the Layer-3 blind resample with a non-Claude model (owner-directed).

LABELLING.md assigns Layer 3 to the owner, and its History entry argues the
resample "must come from outside the family that labelled it". The owner
directed on 2026-08-08 that a model perform the sitting. This runner exists so
that decision is executed **legibly**: what was sent, to which model, and what
came back are all recorded, and the resample block names the model rather than
a person. A future reader must never have to guess whether a human sat.

The standing objection is recorded here rather than in a commit message, because
this is where the next person will look: the gold's pairs are deliberately built
so some hypotheses are true in the corpus world but unsupported by the premise,
and scoring plausibility instead of entailment is a *generic* frontier-model
failure rather than a Claude-specific one. The judge T2.41 qualifies is itself
an LLM entailment judge. So a passing number here measures inter-model agreement
more than it measures label correctness. It is evidence; it is weaker evidence
than the protocol assumed.

Integrity properties, enforced rather than promised:

* **Blind.** The only corpus input is ``resample_blind.json`` (id, premise,
  hypothesis). The gold is opened once, at scoring time, inside
  ``resample_score.score``. This module never reads a verdict.
* **Independent per pair.** One request per pair, no shared conversation, so a
  verdict cannot condition on another pair's — LABELLING.md's "one labeller
  never sees other batches' verdicts", applied per item.
* **Not Claude.** A model id that looks Claude-family is refused: running one
  would reproduce exactly the correlated error the resample exists to detect.
* **Measure, then record.** Scoring prints; it writes the gold only under
  ``--write-gold``. Same split the gate runners use.

Run from backend/:
  AGENT_ROUTER_KEY=... python scripts/benchlib/resample_llm.py \\
      --base-url https://<host>/v1 --model <non-claude-model>
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _p in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx  # noqa: E402

from benchlib import entailment_gold, resample_score, resample_sheet  # noqa: E402

RAW_DIR = HERE / "entailment" / "resample_runs"
CLAUDE_MARKERS = ("claude", "anthropic", "opus", "sonnet", "haiku", "fable")

SYSTEM = (
    "You are labelling premise/hypothesis pairs for an entailment gold set. "
    "Decide exactly one verdict per pair and name the rule you used. Answer "
    "only from the printed premise: no world knowledge, no plausibility, no "
    "guessing at what is probably true. Several pairs are built so the "
    "hypothesis is true in the world but NOT supported by the premise; the "
    "correct verdict for those is unsupported.\n\n"
    "Reply with a single JSON object and nothing else:\n"
    '{"verdict": "entailed|contradicted|unsupported", "rule": "<rule name>"}'
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def assert_not_claude_family(model: str) -> None:
    lowered = model.lower()
    hit = next((m for m in CLAUDE_MARKERS if m in lowered), None)
    if hit is not None:
        raise SystemExit(
            f"refusing to run the resample on {model!r}: {hit!r} marks it "
            "Claude-family, and every label in this gold was produced by "
            "Claude-family agents. The second blind pass already measured that "
            "failure -- it 'added ~zero bits and diverged identically to pass "
            "A'. Such a run would pass the bar comfortably and certify "
            "nothing, which is the one outcome LABELLING.md's protocol exists "
            "to prevent. Choose a model from another vendor."
        )


def build_prompt(rulebook: str, row: dict) -> str:
    return (
        f"{rulebook}\n\n"
        "---\n\n"
        f"**Premise:** {row['premise']}\n\n"
        f"**Hypothesis:** {row['hypothesis']}\n"
    )


def parse_reply(text: str) -> dict:
    """Pull the verdict object out of a reply, tolerating prose around it.

    Returns whatever it finds without validating the verdict word: the closed
    vocabulary is `resample_score.score`'s to enforce, and it raises there with
    the pair id attached. A parse that silently substituted a default would
    turn a refusing model into a confident one.
    """
    match = _JSON_RE.search(text or "")
    if match is None:
        return {"verdict": "", "rule": "", "raw": text}
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"verdict": "", "rule": "", "raw": text}
    return {
        "verdict": str(obj.get("verdict", "")).strip().lower(),
        "rule": str(obj.get("rule", "")).strip(),
        "raw": text,
    }


async def label_one(client, base_url, model, api_key, rulebook, row, sem, params) -> tuple[str, dict]:
    async with sem:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                **params,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": build_prompt(rulebook, row)},
                ],
            },
        )
        resp.raise_for_status()
        body = resp.json()
        text = body["choices"][0]["message"]["content"]
        return row["id"], parse_reply(text)


async def run(
    *, base_url: str, model: str, api_key: str, concurrency: int, timeout: float,
    params: dict,
) -> dict[str, dict]:
    blind = json.loads(Path(resample_sheet.BLIND_EXPORT_PATH).read_text(encoding="utf-8"))
    rulebook = resample_sheet.rulebook_excerpt(resample_sheet.LABELLING_PATH)
    sem = asyncio.Semaphore(concurrency)
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [
            label_one(client, base_url, model, api_key, rulebook, row, sem, params)
            for row in blind
        ]
        for n, coro in enumerate(asyncio.as_completed(tasks), start=1):
            pid, verdict = await coro
            out[pid] = verdict
            if n % 10 == 0 or n == len(tasks):
                print(f"  labelled {n}/{len(tasks)}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", required=True, help="OpenAI-compatible root, e.g. https://host/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key-env", default="AGENT_ROUTER_KEY")
    ap.add_argument("--raw-dir", default=None, metavar="PATH", help=(
        "where to write the run's raw replies (default: the committed "
        "entailment/resample_runs/). A test must pass its own -- the default "
        "is a corpus directory, and test output landed in it once already."
    ))
    ap.add_argument("--concurrency", type=int, default=4)
    # The GPT-5 line refuses temperature=0 ("only the default (1) is
    # supported"), so temperature is omitted unless asked for. `seed` is what
    # buys reproducibility on that line instead, and it is recorded beside the
    # verdicts: a certifying run nobody can repeat certifies less.
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--seed", type=int, default=20260808)
    ap.add_argument("--reasoning-effort", default="high")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument(
        "--write-gold", action="store_true",
        help="persist the resample block into gold.json (default: measure only)",
    )
    ap.add_argument(
        "--force", action="store_true",
        help=(
            "record over an existing resample block. Lawful for one case only: "
            "the gold's PAIRS have moved since the prior sitting, so that "
            "sitting certifies a set that no longer exists. The prior block is "
            "kept under 'supersedes', never dropped, and the content-hash leg "
            "of gate_eligibility is what proves the move rather than this flag "
            "asserting it. Never use it to re-sit the same pairs for a better "
            "number: one sitting is recorded once per draw, and that is the "
            "whole point of the guard this opens."
        ),
    )
    ap.add_argument(
        "--from-raw", default=None, metavar="PATH",
        help=(
            "score and record a sitting that ALREADY HAPPENED, from its raw "
            "replies, with no model call. Use this to record what you "
            "measured: a second invocation with --write-gold re-sits the "
            "model, and an LLM sitting is not reproducible, so the number "
            "certified would come from a different sitting than the one you "
            "read. Measured 1 disagreement and recorded 0 that way once "
            "(T2.115, 2026-08-10)."
        ),
    )
    ap.add_argument(
        "--performed-by", default=None, metavar="TEXT",
        help=(
            "provenance for the record. Defaults to naming the model and this "
            "run's date; never a person, since the record must not read as a "
            "human sitting when no human sat."
        ),
    )
    args = ap.parse_args(argv)

    assert_not_claude_family(args.model)
    api_key = os.environ.get(args.api_key_env)
    if not api_key and not args.from_raw:
        raise SystemExit(f"{args.api_key_env} is not set")

    params: dict = {}
    if args.temperature is not None:
        params["temperature"] = args.temperature
    if args.seed is not None:
        params["seed"] = args.seed
    if args.reasoning_effort:
        params["reasoning_effort"] = args.reasoning_effort

    gold_path = Path(entailment_gold.GOLD_PATH)
    gold_bytes = gold_path.read_bytes()
    gold_sha = hashlib.sha256(gold_bytes).hexdigest()

    if args.from_raw:
        recorded = json.loads(Path(args.from_raw).read_text(encoding="utf-8"))
        if recorded.get("gold_sha256") != gold_sha:
            raise SystemExit(
                f"{args.from_raw} certifies gold {recorded.get('gold_sha256', '?')[:8]} "
                f"and this gold is {gold_sha[:8]} -- a resample means nothing "
                "except relative to the file it certifies"
            )
        verdicts = recorded["verdicts"]
        params = recorded.get("params", params)
        raw_path = Path(args.from_raw)
        print(f"scoring the recorded sitting at {raw_path} -- no model call")
    else:
        print(f"model: {args.model}  host: {urlsplit(args.base_url).netloc}  params: {params}")
        verdicts = asyncio.run(run(
            base_url=args.base_url, model=args.model, api_key=api_key,
            concurrency=args.concurrency, timeout=args.timeout, params=params,
        ))

    raw_dir = Path(args.raw_dir) if args.raw_dir else RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    # The gold sha is part of the filename, not merely of the payload: a
    # resample means nothing except relative to the file it certifies, and
    # {date}-{model} alone collides whenever the same model re-sits a re-drawn
    # gold on the same day — which silently destroyed the previous round's
    # record once. Runs predating this carry the bare name.
    if not args.from_raw:
        raw_path = (raw_dir / f"{args.date}-{re.sub(r'[^a-zA-Z0-9]+', '-', args.model)}"
                              f"-{gold_sha[:8]}.json")
        # **A second sitting never overwrites the first.** The sha in the name
        # separates sittings of different golds; it does nothing for two
        # sittings of the SAME gold on the same day, which is the ordinary
        # shape of measure-then-record -- and one of them destroyed the other's
        # evidence (T2.115). An LLM sitting is not reproducible, so each one is
        # its own artifact.
        suffix = 2
        while raw_path.exists():
            raw_path = raw_path.with_name(
                f"{raw_path.name.removesuffix('.json')}".rsplit("-sitting", 1)[0]
                + f"-sitting{suffix}.json"
            )
            suffix += 1
        raw_path.write_text(
            json.dumps({"model": args.model, "host": urlsplit(args.base_url).netloc,
                        "date": args.date, "params": params,
                        "gold_sha256": gold_sha, "verdicts": verdicts},
                       indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"raw replies: {raw_path}")

    block, disagreements = resample_score.score(
        {k: {"verdict": v["verdict"], "rule": v["rule"]} for k, v in verdicts.items()},
        gold_bytes=gold_bytes,
        gold_pairs=json.loads(gold_bytes)["pairs"],
        manifest=resample_score.load_manifest(),
        blind_ids=resample_score.load_blind_ids(),
        # Names the instrument, never a person: the record must not read as a
        # human sitting when no human sat.
        performed_by=args.performed_by or (
            f"LLM pass: {args.model} (non-Claude, owner-directed {args.date})"
        ),
        date=args.date,
    )
    print(f"\nn={block['n']}  disagreements={block['disagreements']}  "
          f"bar<={resample_score.RESAMPLE_MAX_DISAGREEMENTS}")
    for d in disagreements:
        print(f"  {d}")

    if args.write_gold:
        resample_score.write_resample(gold_path, block, force=args.force)
        print(f"\nresample block written to {gold_path}")
    else:
        print("\nmeasure-only: pass --write-gold to record this into gold.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
