import os,sys,json,ast,asyncio,httpx,random
B="/home/claude/darkmem/backend"; sys.path.insert(0,B)
from app.services.enrichment_worker import SUMMARY_PROMPT,MAX_SOURCE_CHARS
from app.services import prompt
SYS=prompt.get("summarization"); MODE=sys.argv[1]; AK=os.environ["AK"]; H={"x-api-key":AK,"anthropic-version":"2023-06-01"}
files=["app/services/usage_pricing.py","app/services/llm_quirks.py","app/services/rank_fusion.py","app/services/capture_lint.py","app/services/supersession.py","app/services/worklog.py"]
syms=[]
for f in files:
    src=open(f"{B}/{f}").read(); t=ast.parse(src)
    for n in t.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and 8<=n.end_lineno-n.lineno<=60:
            syms.append((f,n.name,ast.get_source_segment(src,n)))
random.seed(3); syms=random.sample(syms,min(14,len(syms)))
async def main():
    async with httpx.AsyncClient(timeout=120,verify=os.environ["SSL_CERT_FILE"]) as c:
        async def one(s):
            body={"model":"claude-haiku-5-5","max_tokens":512,"system":SYS,"messages":[{"role":"user","content":SUMMARY_PROMPT.format(kind="function",source_code=s[2][:MAX_SOURCE_CHARS])}]}
            if MODE=="nothink": body["thinking"]={"type":"disabled"}
            r=await c.post("https://api.anthropic.com/v1/messages",headers=H,json=body); j=r.json()
            return s,"".join(b.get("text","") for b in j["content"] if b["type"]=="text"),j["usage"],j["stop_reason"]
        return await asyncio.gather(*[one(s) for s in syms])
res=asyncio.run(main())
json.dump([{"sym":f"{s[0]}:{s[1]}","text":t,"usage":u,"stop":st} for s,t,u,st in res],open(f"summ_{MODE}.json","w"),indent=1)
print(MODE,"n",len(res),"empty",sum(not t for _,t,_,_ in res),"stops",{st for *_,st in res},"in",sum(u["input_tokens"] for _,_,u,_ in res),"out",sum(u["output_tokens"] for _,_,u,_ in res),"think",sum((u.get("output_tokens_details")or{}).get("thinking_tokens",0) for _,_,u,_ in res))
