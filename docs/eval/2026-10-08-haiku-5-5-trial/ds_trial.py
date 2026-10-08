"""DeepSeek twin of haiku_bench.py, rerank.py and summ.py: same inputs, same scoring.

Usage (from this directory, backend venv): ds_trial.py ext <gold.json|gold_heldout.json>
                                         ds_trial.py rerank
                                         ds_trial.py summ
Reads the key from $DK; it is never written anywhere. Request params mirror the seeded
deepseek-flash-* profiles in app/services/llm_seed.py.
"""
import os, sys, json, ast, asyncio, time, random, re, httpx
B = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend"))
sys.path.insert(0, B); sys.path.insert(0, B + "/scripts/extraction_bench")
DK = os.environ["DK"]; URL = "https://api.deepseek.com/v1/chat/completions"
H = {"Authorization": f"Bearer {DK}"}
VERIFY = os.environ.get("SSL_CERT_FILE", True)


async def chat(c, body):
    for a in range(5):
        t = time.time()
        try:
            r = await c.post(URL, headers=H, json=body)
            if r.status_code == 200:
                j = r.json()
                return j["choices"][0]["message"].get("content") or "", j["usage"], time.time() - t, j["choices"][0]["finish_reason"], j.get("model")
            err = r.text[:200]
        except httpx.HTTPError as e:
            err = repr(e)
        await asyncio.sleep(4 * (a + 1))
    raise RuntimeError(err)


def toks(usage):
    s = lambda k: sum(u.get(k, 0) or 0 for u in usage)
    return dict(prompt=s("prompt_tokens"), cache_hit=s("prompt_cache_hit_tokens"),
                cache_miss=s("prompt_cache_miss_tokens"), output=s("completion_tokens"),
                reasoning=sum((u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0 for u in usage))


async def ext(gold_name):
    import run_bench as rb
    from app.services.extraction import ExtractionService, clean_extraction, _loads_extraction
    gold = json.load(open(f"{B}/scripts/extraction_bench/{gold_name}"))["memories"]
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=300, verify=VERIFY) as c:
        async def one(g):
            req = ExtractionService.build_extraction_request(g["content"], with_classification=True)
            body = {"model": "deepseek-v4-flash", "messages": req.messages, "temperature": 0, "max_tokens": 8192,
                    "thinking": {"type": "disabled"}, "response_format": req.response_format, "seed": req.seed}
            async with sem:
                return g, await chat(c, body)
        first = await one(gold[0]); rest = await asyncio.gather(*[one(g) for g in gold[1:]])
    res = [first] + list(rest)
    dims = {k: [0, 0, 0] for k in ("ent_nt", "ent_n", "rel_full", "rel_pair")}; usage = []; fails = 0; lat = []; out = []
    for g, (text, u, dt, stop, model) in res:
        usage.append(u); lat.append(dt)
        try: raw = _loads_extraction(text)
        except Exception: fails += 1; raw = {"entities": [], "relationships": []}
        pred = clean_extraction(raw, g["content"], relation_rescue=True)
        pe, pr = pred.get("entities", []), pred.get("relationships", [])
        pairs = {"ent_nt": (rb.ent_keys(g["entities"], True), rb.ent_keys(pe, True)), "ent_n": (rb.ent_keys(g["entities"], False), rb.ent_keys(pe, False)),
                 "rel_full": (rb.rel_keys(g["relations"], True), rb.rel_keys(pr, True)), "rel_pair": (rb.rel_keys(g["relations"], False), rb.rel_keys(pr, False))}
        for d, (gs, ps) in pairs.items():
            dims[d][0] += len(gs & ps); dims[d][1] += len(ps - gs); dims[d][2] += len(gs - ps)
        out.append({"id": g["id"], "raw": raw, "usage": u, "stop": stop, "model": model})
    json.dump(out, open(f"ds_ext_{gold_name}", "w"), indent=1)
    print(f"== {gold_name} deepseek n={len(res)} parse_fail={fails} model={res[0][1][4]}")
    for d, (tp, fp, fn) in dims.items():
        p, r, f = rb.prf(tp, fp, fn); print(f"  {d:9} P={p:.3f} R={r:.3f} F1={f:.3f} tp={tp} fp={fp} fn={fn}")
    print("  tokens:", toks(usage))
    lat.sort(); print(f"  latency median={lat[len(lat)//2]:.1f}s p90={lat[int(len(lat)*.9)-1]:.1f}s")


async def rerank():
    from app.services.reranker import _RERANK_PROMPT, _RERANK_SYSTEM_PROMPT
    c = json.load(open(B + "/scripts/benchlib/retrieval/corpus.json"))["memories"]
    g = [p for p in json.load(open(B + "/scripts/benchlib/retrieval/gold.json"))["pairs"] if not p.get("retired")]
    byid = {m["memory_id"]: m["content"] for m in c}
    tok = lambda s: set(re.findall(r"[a-z0-9]+", s.lower()))
    random.seed(7); qs = random.sample(g, 40)
    items = []
    for p in qs:
        rel = [i for i in p["relevant_memory_ids"] if i in byid]
        neg = sorted((i for i in byid if i not in rel), key=lambda i: -len(tok(byid[i]) & tok(p["query"])))[:6]
        for i in rel: items.append((p["id"], p["query"], i, 1))
        for i in neg: items.append((p["id"], p["query"], i, 0))
    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=120, verify=VERIFY) as cl:
        async def one(it):
            body = {"model": "deepseek-chat", "temperature": 0, "max_tokens": 32, "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": _RERANK_SYSTEM_PROMPT},
                                 {"role": "user", "content": _RERANK_PROMPT.format(query=it[1], document=byid[it[2]][:1000])}]}
            async with sem:
                t, u, *_ = await chat(cl, body)
            try: s = float(json.loads(t)["score"])
            except Exception: s = None
            return it, s, t, u
        res = await asyncio.gather(*[one(i) for i in items])
    fail = sum(s is None for _, s, _, _ in res); by = {}
    for it, s, t, u in res: by.setdefault(it[0], []).append((it[3], s if s is not None else -1))
    auc_n = auc_d = 0; mrr = 0; top1 = 0
    for q, l in by.items():
        pos = [s for y, s in l if y]; neg = [s for y, s in l if not y]
        for a in pos:
            for b in neg: auc_d += 1; auc_n += 1 if a > b else .5 if a == b else 0
        rk = sorted(l, key=lambda x: -x[1]); first = next(i for i, (y, _) in enumerate(rk) if y)
        mrr += 1 / (first + 1); top1 += first == 0
    print(f"rerank deepseek calls={len(res)} parse_fail={fail} AUC={auc_n/auc_d:.3f} MRR={mrr/len(by):.3f} top1={top1}/{len(by)}")
    print("  tokens:", toks([u for *_, u in res]))
    json.dump([{"q": it[0], "mem": it[2], "rel": it[3], "score": s, "text": t} for it, s, t, _ in res], open("ds_rerank.json", "w"), indent=1)


async def summ():
    from app.services.enrichment_worker import SUMMARY_PROMPT, MAX_SOURCE_CHARS
    from app.services import prompt
    SYS = prompt.get("summarization")
    files = ["app/services/usage_pricing.py", "app/services/llm_quirks.py", "app/services/rank_fusion.py",
             "app/services/capture_lint.py", "app/services/supersession.py", "app/services/worklog.py"]
    syms = []
    for f in files:
        src = open(f"{B}/{f}").read(); t = ast.parse(src)
        for n in t.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and 8 <= n.end_lineno - n.lineno <= 60:
                syms.append((f, n.name, ast.get_source_segment(src, n)))
    random.seed(3); syms = random.sample(syms, min(14, len(syms)))
    async with httpx.AsyncClient(timeout=120, verify=VERIFY) as c:
        async def one(s):
            body = {"model": "deepseek-chat", "temperature": 0.3, "max_tokens": 512,
                    "messages": [{"role": "system", "content": SYS},
                                 {"role": "user", "content": SUMMARY_PROMPT.format(kind="function", source_code=s[2][:MAX_SOURCE_CHARS])}]}
            t, u, dt, stop, _ = await chat(c, body)
            return s, t, u, stop
        res = await asyncio.gather(*[one(s) for s in syms])
    json.dump([{"sym": f"{s[0]}:{s[1]}", "text": t, "usage": u, "stop": st} for s, t, u, st in res], open("ds_summ.json", "w"), indent=1)
    print("summ deepseek n", len(res), "empty", sum(not t for _, t, _, _ in res), "stops", {st for *_, st in res})
    print("  tokens:", toks([u for _, _, u, _ in res]))


mode = sys.argv[1]
asyncio.run({"ext": lambda: ext(sys.argv[2]), "rerank": rerank, "summ": summ}[mode]())
