import os,sys,json,asyncio,re,httpx,random
B="/home/claude/darkmem/backend"; sys.path.insert(0,B)
from app.services.reranker import _RERANK_PROMPT,_RERANK_SYSTEM_PROMPT
MODE=sys.argv[1]; AK=os.environ["AK"]; H={"x-api-key":AK,"anthropic-version":"2023-06-01"}
c=json.load(open(B+"/scripts/benchlib/retrieval/corpus.json"))["memories"]
g=[p for p in json.load(open(B+"/scripts/benchlib/retrieval/gold.json"))["pairs"] if not p.get("retired")]
byid={m["memory_id"]:m["content"] for m in c}
tok=lambda s:set(re.findall(r"[a-z0-9]+",s.lower()))
random.seed(7); qs=random.sample(g,40)
items=[]
for p in qs:
    rel=[i for i in p["relevant_memory_ids"] if i in byid]
    neg=sorted((i for i in byid if i not in rel),key=lambda i:-len(tok(byid[i])&tok(p["query"])))[:6]
    for i in rel: items.append((p["id"],p["query"],i,1))
    for i in neg: items.append((p["id"],p["query"],i,0))
async def main():
    sem=asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=120,verify=os.environ["SSL_CERT_FILE"]) as cl:
        async def one(it):
            body={"model":"claude-haiku-5-5","max_tokens":32,"system":_RERANK_SYSTEM_PROMPT,
                  "messages":[{"role":"user","content":_RERANK_PROMPT.format(query=it[1],document=byid[it[2]][:1000])}]}
            if MODE=="nothink": body["thinking"]={"type":"disabled"}
            elif MODE!="default": body["output_config"]={"effort":MODE}
            async with sem:
                for a in range(4):
                    r=await cl.post("https://api.anthropic.com/v1/messages",headers=H,json=body)
                    if r.status_code==200: break
                    await asyncio.sleep(4*(a+1))
            j=r.json(); t="".join(b.get("text","") for b in j["content"] if b["type"]=="text")
            try: s=float(json.loads(t)["score"])   # Darkmem's exact parse
            except Exception: s=None
            return it,s,t,j["usage"]
        return await asyncio.gather(*[one(i) for i in items])
res=asyncio.run(main())
fail=sum(s is None for _,s,_,_ in res)
by=dict()
for it,s,t,u in res: by.setdefault(it[0],[]).append((it[3],s if s is not None else -1))
auc_n=auc_d=0; mrr=0; top1=0
for q,l in by.items():
    pos=[s for y,s in l if y]; neg=[s for y,s in l if not y]
    for a in pos:
        for b in neg: auc_d+=1; auc_n+= 1 if a>b else .5 if a==b else 0
    rk=sorted(l,key=lambda x:-x[1]); first=next(i for i,(y,_) in enumerate(rk) if y)
    mrr+=1/(first+1); top1+= first==0
out=sum(u["output_tokens"] for *_,u in res); inp=sum(u["input_tokens"] for *_,u in res)
print(f"mode={MODE} calls={len(res)} parse_fail={fail} ({fail/len(res):.0%}) AUC={auc_n/auc_d:.3f} MRR={mrr/len(by):.3f} top1={top1}/{len(by)} input={inp} output={out}")
bad=[t for _,s,t,_ in res if s is None][:3]; print("sample failures:",bad)
