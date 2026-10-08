"""Blind grading of reason_trial.py qa answers by two judges from different vendors.

  judge.py <judge> <answers.json> [<answers.json> ...]     judge: claude-opus-5-5 | deepseek-v4-pro
Answers are shuffled and stripped of model names before grading. Writes judged_<judge>.json and
prints per-file scores. Keys from $AK / $DK.
"""
import os, sys, json, asyncio, random, re, httpx
B = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend"))
VERIFY = os.environ.get("SSL_CERT_FILE", True)
JUDGE, FILES = sys.argv[1], sys.argv[2:]
corpus = {m["memory_id"]: m["content"] for m in json.load(open(B + "/scripts/benchlib/retrieval/corpus.json"))["memories"]}

RUBRIC = """You grade one answer from a memory Q&A system. The system was given numbered memories and a
question and told to answer ONLY from the memories, cite memory numbers, and say the memories do not
contain enough information when they don't.

You are told which memory numbers (if any) actually hold the answer. Grade strictly on these fields:
- "correct": true if the answer states the information from the answering memories accurately
  (for a case with no answering memories: true if it says the memories don't contain the answer, and
  may mention related but non-answering memories only as such).
- "unsupported": number of claims in the answer that no provided memory supports (invented facts).
- "miscited": number of citations pointing at a memory that does not support the cited claim.
- "complete": true if every answering memory's relevant content is used (always true when there are none).
- "note": one short sentence on the main flaw, or "" if none.
Reply with JSON only: {"correct": bool, "unsupported": int, "miscited": int, "complete": bool, "note": str}"""


def case_text(r):
    mems = "\n".join(f"[{i+1}] {corpus[mid]}" for i, mid in enumerate(r["ids"]))
    ans = [str(r["ids"].index(m) + 1) for m in r["relevant"]]
    holds = f"Memories that hold the answer: {', '.join('[' + a + ']' for a in ans)}" if ans else "No memory holds the answer."
    return f"<memories>\n{mems}\n</memories>\n<question>What do my memories say about this: {r['query']}?</question>\n{holds}\n<answer>\n{r['answer']}\n</answer>"


async def grade(c, text):
    msgs = [{"role": "user", "content": text}]
    for a in range(5):
        try:
            if JUDGE.startswith("deepseek"):
                r = await c.post("https://api.deepseek.com/v1/chat/completions", headers={"Authorization": f"Bearer {os.environ['DK']}"},
                                 json={"model": JUDGE, "temperature": 0, "max_tokens": 2048, "response_format": {"type": "json_object"},
                                       "messages": [{"role": "system", "content": RUBRIC}] + msgs})
                if r.status_code == 200: t = r.json()["choices"][0]["message"]["content"]
            else:
                r = await c.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": os.environ["AK"], "anthropic-version": "2023-06-01"},
                                 json={"model": JUDGE, "max_tokens": 4096, "system": RUBRIC, "messages": msgs, "output_config": {"effort": "high"}})
                if r.status_code == 200: t = "".join(b.get("text", "") for b in r.json()["content"] if b["type"] == "text")
            if r.status_code == 200:
                return json.loads(re.search(r"\{.*\}", t, re.S).group(0))
        except Exception:
            pass
        await asyncio.sleep(4 * (a + 1))
    return None


async def main():
    rows = []
    for f in FILES:
        for r in json.load(open(f)): rows.append((f, r))
    random.Random(5).shuffle(rows)
    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=600, verify=VERIFY) as c:
        async def one(fr):
            async with sem:
                return fr, await grade(c, case_text(fr[1]))
        res = await asyncio.gather(*[one(x) for x in rows])
    out = [{"file": f, "pair": r["pair"], "kind": r["kind"], "verdict": v} for (f, r), v in res]
    json.dump(out, open(f"judged_{JUDGE}.json", "w"), indent=1)
    for f in FILES:
        for kind in ("pos", "neg"):
            vs = [o["verdict"] for o in out if o["file"] == f and o["kind"] == kind and o["verdict"]]
            n = len(vs)
            print(f"{JUDGE:16} {f:34} {kind} n={n} correct={sum(v['correct'] for v in vs)} complete={sum(v['complete'] for v in vs)} "
                  f"unsupported={sum(v['unsupported'] for v in vs)} miscited={sum(v['miscited'] for v in vs)}")


asyncio.run(main())
