import os, sys, json, asyncio, time, httpx
B="/home/claude/darkmem/backend"; sys.path.insert(0,B); sys.path.insert(0,B+"/scripts/extraction_bench")
import run_bench as rb
from app.services.extraction import ExtractionService, clean_extraction, _loads_extraction
AK=os.environ["AK"]; MODE=sys.argv[1]; GOLD=sys.argv[2]
H={"x-api-key":AK,"anthropic-version":"2023-06-01"}
async def call(c, req):
    sysmsg=req.messages[0]["content"]; user=req.messages[1]["content"]
    body={"model":"claude-haiku-5-5","max_tokens":8192,
          "system":[{"type":"text","text":sysmsg,"cache_control":{"type":"ephemeral"}}],
          "messages":[{"role":"user","content":user}]}
    if MODE=="nothink": body["thinking"]={"type":"disabled"}
    else: body["output_config"]={"effort":MODE}
    for a in range(4):
        t=time.time(); r=await c.post("https://api.anthropic.com/v1/messages",headers=H,json=body)
        if r.status_code==200: break
        await asyncio.sleep(5*(a+1))
    j=r.json(); text="".join(b.get("text","") for b in j["content"] if b["type"]=="text")
    return text, j["usage"], time.time()-t, j["stop_reason"]
async def main():
    gold=json.load(open(f"{B}/scripts/extraction_bench/{GOLD}"))["memories"]
    sem=asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=300, verify=os.environ["SSL_CERT_FILE"]) as c:
        # warm the cache with the first item, then fan out
        async def one(g):
            async with sem:
                req=ExtractionService.build_extraction_request(g["content"],with_classification=True)
                return g, await call(c, req)
        first=await one(gold[0]); rest=await asyncio.gather(*[one(g) for g in gold[1:]])
    res=[first]+list(rest)
    dims={k:[0,0,0] for k in ("ent_nt","ent_n","rel_full","rel_pair")}; usage=[]; fails=0; lat=[]
    out=[]
    for g,(text,u,dt,stop) in res:
        usage.append(u); lat.append(dt)
        try: raw=_loads_extraction(text)
        except Exception: fails+=1; raw={"entities":[],"relationships":[]}
        pred=clean_extraction(raw,g["content"],relation_rescue=True)
        pe,pr=pred.get("entities",[]),pred.get("relationships",[])
        pairs={"ent_nt":(rb.ent_keys(g["entities"],True),rb.ent_keys(pe,True)),"ent_n":(rb.ent_keys(g["entities"],False),rb.ent_keys(pe,False)),
               "rel_full":(rb.rel_keys(g["relations"],True),rb.rel_keys(pr,True)),"rel_pair":(rb.rel_keys(g["relations"],False),rb.rel_keys(pr,False))}
        for d,(gs,ps) in pairs.items():
            dims[d][0]+=len(gs&ps); dims[d][1]+=len(ps-gs); dims[d][2]+=len(gs-ps)
        out.append({"id":g["id"],"raw":raw,"usage":u,"stop":stop,"summary":raw.get("summary"),"memory_type":raw.get("memory_type")})
    json.dump(out,open(f"ext_{MODE}_{GOLD}","w"),indent=1)
    print(f"== {GOLD} mode={MODE} n={len(res)} parse_fail={fails}")
    for d,(tp,fp,fn) in dims.items():
        p,r,f=rb.prf(tp,fp,fn); print(f"  {d:9} P={p:.3f} R={r:.3f} F1={f:.3f} tp={tp} fp={fp} fn={fn}")
    s=lambda k: sum(x.get(k,0) or 0 for x in usage)
    th=sum((x.get("output_tokens_details") or {}).get("thinking_tokens",0) for x in usage)
    print(f"  tokens: input={s('input_tokens')} cache_read={s('cache_read_input_tokens')} cache_write={s('cache_creation_input_tokens')} output={s('output_tokens')} thinking={th}")
    lat.sort(); print(f"  latency median={lat[len(lat)//2]:.1f}s p90={lat[int(len(lat)*.9)-1]:.1f}s")
asyncio.run(main())
