"""One-off emitter for retrieval top-up batch-012 — multi-sentence queries.

Each row pairs a longer, paragraph-shaped query (2-4 sentences, 20-60 words) with
its source shared row as the positive. Queries simulate a careful user typing out
context and a specific question instead of a terse search phrase.

Writes 100 rows to data/v2/retrieval/batch_012.tmp.jsonl with ids ret-01101..01200,
pulling positives from shared rows at zero-indexed offsets 1100..1199.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_012.tmp.jsonl"
ID_OFFSET = 1100
SHARED_OFFSET = 1100
QUERY_KIND = "multi-sentence"

# 100 multi-sentence queries, aligned in order with shared rows 1101..1200.
QUERIES: list[str] = [
    # 01101 step-ca SSH host certs + YubiKey root
    "We're trying to move our bastion fleet off trust-on-first-use for SSH. How is step-ca being used to mint short-lived host certificates, and where does the signing root actually live in hardware?",
    # 01102 smallstep replaced Boundary
    "Our operator-access tooling is being reconsidered. Which product took over from HashiCorp Boundary for that flow, and what was it about the ACME-style enrolment that made it fit our existing TLS setup?",
    # 01103 SPIFFE + SPIRE AWS attestation
    "I need to understand how workloads across regions prove identity without sharing secrets. How do SPIFFE IDs solve that, and what mechanism do the SPIRE agents use to attest EC2 nodes?",
    # 01104 SPIRE preferred over custom JWT minters
    "A teammate is proposing a homegrown JWT minter for service identity. What's our stated preference instead, and what do we get out of the box by going that route for rotation and attestation?",
    # 01105 STUN vs TURN symmetric NAT
    "One carrier is killing our voice call setup. Is pure STUN enough in every NAT scenario, and what had to step in to keep the audio quality acceptable on that problematic symmetric NAT?",
    # 01106 ICE candidate gathering RFC 8445
    "I'm reading an ICE trace and want to understand the candidate selection. What are the three kinds of candidates ICE gathers, and where is the priority formula actually defined?",
    # 01107 BGP route flapping dampening + RPKI
    "A peer was misbehaving earlier this year. When did route flapping trigger dampening, and what additional control caught the bogus prefix that came along with it?",
    # 01108 Anycast auth resolver APAC
    "Latency in Asia-Pacific was hurting our auth path. What deployment pattern cut P50 there, and how does the system handle a point-of-presence that goes unhealthy?",
    # 01109 Let's Encrypt DNS-01 via Cloudflare wildcard
    "We need wildcard certs for internal subdomains without opening any public HTTP endpoints. Which ACME challenge flow are we using, and which DNS provider fronts it?",
    # 01110 noise
    "I just asked a question and got a blip like the console needed a moment. Is the other side pausing to refresh, or is this something worth retrying?",
    # 01111 Vault dynamic DB creds
    "We had a long-lived shared Postgres password floating around. What replaced it for day-to-day access, and roughly how long do the new database roles stick around before expiring?",
    # 01112 Doppler vs AWS Secrets Manager
    "The developer config story is getting messy. Which secrets product is preferred for developer-facing config over AWS Secrets Manager, and how does it surface those values to the app without an extra sidecar?",
    # 01113 OIDC PKCE mandatory public clients
    "Our mobile SDK suddenly had to ship a new version. What changed in the OIDC authorization code flow for public clients, and why did the older pinned SDK start breaking?",
    # 01114 SAML replay protection InResponseTo
    "Someone tried to reuse a SAML assertion a couple of seconds after it was issued. Which protection actually caught the replay, and what specific field tied it back to the original request?",
    # 01115 CSP strict-dynamic + SRI
    "Our content security posture was tightened after an XSS scare. What CSP configuration is being enforced now, and what was the long slog that came with making it work?",
    # 01116 SameSite=Lax vs Strict admin console
    "A top-frame GET CSRF got past our cookie settings. Why was SameSite=Lax not enough in that case, and what was changed on the admin console to actually stop it?",
    # 01117 JWT rotation JWKS two keys
    "How are we handling rotation for JWT signing without breaking live verifiers? How many keys sit in JWKS at once, and what does the jose library on the verifier side do during the overlap window?",
    # 01118 OAuth scopes vs roles split
    "Our scope list had been growing uncontrollably. What's the new split between OAuth scopes and roles in the resource server, and what problem did that division actually solve?",
    # 01119 AWS KMS CMK wrapping RDS
    "I need to trace how the RDS data keys are protected. Which KMS construct wraps them, and are the grants scoped per human user or per application role?",
    # 01120 Vault transit engine replaced homegrown KMS wrappers
    "We used to run our own key-wrapping code for internal services. What product replaced those homegrown KMS wrappers, and which of its features simplified the rotation audits afterwards?",
    # 01121 GCP KMS EKM customer-held root
    "A customer wants to hold their own root key against our workload on GCP. Which integration makes that possible, and how is break-glass handled when the customer side is unreachable?",
    # 01122 YubiKey attestation cert pinning
    "Someone asked whether a random YubiKey from the internet could be enrolled for a production role. What's pinned during enrolment, and what happens if the device isn't genuine?",
    # 01123 TPM platform attestation laptop access
    "How is laptop access to sensitive repos gated on the endpoint side? What role does the TPM play during boot, and which signals feed into the conditional-access policy?",
    # 01124 Cloudflare WAF Log4Shell false positive
    "Our reporting URL briefly started getting blocked at the edge. Which managed ruleset triggered on it, and was the block a true positive or a known false positive?",
    # 01125 token-bucket rate limiter edge
    "I want to understand how we rate-limit traffic per tenant. Where does the token bucket live in our stack, and what determines how fast each tenant's bucket refills?",
    # 01126 mTLS mandatory Istio payments
    "East-west traffic inside the mesh is now supposed to be mTLS only. When did that land for the payments service, and which Istio setting is enforcing it?",
    # 01127 Cilium Tetragon eBPF exec tracing
    "We're doing runtime policy on tier-0 pods now. Which tool traces exec events in the kernel via eBPF, and what does its rule engine block when it sees an unexpected process tree?",
    # 01128 Falco vs custom audit scripts
    "Our custom audit scripts keep missing attacker techniques. Which tool is preferred instead for kernel rule coverage, and what do we get from the community ruleset that we wouldn't have written ourselves?",
    # 01129 Syft SBOM SPDX + CycloneDX OCI registry
    "I'm being asked where the SBOMs live for each image. Which tool generates them, which formats does it produce, and where are they stored after the build?",
    # 01130 cosign replaced Notary v1 Fulcio keyless
    "We moved off an older container-signing stack. Which tool replaced Notary v1, and why did the keyless flow against Fulcio line up with our identity story in particular?",
    # 01131 SLSA L3 in-toto provenance
    "Compliance is asking for build provenance on every release. Which SLSA level are we at, what does the provenance build on, and what ships alongside each release as a result?",
    # 01132 DNSSEC signing KSK rollover
    "We had a rough DNSSEC rollout earlier this year. When did signing go live on the public zones, and what specific operational lesson came out of the KSK rollover mishap?",
    # 01133 HSTS preload apex domain subdomain mixed content
    "I'm trying to get the apex domain onto the HSTS preload list. What had to be fixed across the subdomains before the submission could go through?",
    # 01134 noise
    "The other side just said they'd poke the service and come back. Is there something I should do on my end while they check, or do I just wait for them to return?",
    # 01135 Pomerium replaced VPN zero-trust
    "Our legacy VPN as the single entry point to internal apps is on the way out. What replaced it, and at what granularity is device posture now being checked?",
    # 01136 Cloudflare Access SSO vendor consoles JWT
    "Vendor consoles each used to have their own SSO story. Which product now fronts them for SSO, and what does the upstream see so it can still apply its own RBAC?",
    # 01137 BeyondCorp assumption
    "A new hire wants the one-liner on our zero-trust philosophy. What's the core assumption a BeyondCorp-style model makes about the corporate network, and which controls replace the old perimeter?",
    # 01138 Tailscale mesh improvement over WireGuard
    "Hand-tuned WireGuard peer lists have been burning time whenever nodes churn. What mesh product improves on that situation, and specifically what does its coordination server remove from our workload?",
    # 01139 Netbird vs Netmaker self-hosted mesh
    "We evaluated self-hosted mesh options and picked one. Which one did we choose over Netmaker, and what was the deciding property that made it slot into our existing OIDC setup?",
    # 01140 Caddy automatic TLS ops dashboards internal ACME
    "The ops dashboards used to need manual cert renewals. Which server is handling TLS for them now, and where does it get its certificates from without leaning on public CAs?",
    # 01141 Traefik preferred over Nginx dynamic ingress
    "Our ingress tier churns a lot of containers. Which reverse proxy is preferred over Nginx for that tier, and what specifically beats the old template-regeneration scripts?",
    # 01142 Nginx static marketing site
    "Not every service wants a full dynamic ingress. Which site still runs on plain Nginx, and why did we decide there wasn't a reason to swap anything heavier in for it?",
    # 01143 Boundary session recording admin incident playback
    "An admin session needed review after an incident in early March. Which tool captured the full recording, and how does playback actually work for the reviewer?",
    # 01144 SPIFFE Workload API SVID socket
    "How do sidecars actually receive their identity material at runtime? Which SPIFFE API is wired into the injector, and where do the short-lived SVIDs land so they never touch disk?",
    # 01145 Fulcio keyless OIDC Rekor rollback audit
    "I want to understand how our signing identities work on each build. Which component issues the ephemeral certificate, what is it bound to, and how do we make rollbacks auditable later?",
    # 01146 AES-GCM-SIV nonce reuse at-rest
    "A threat model flagged nonce reuse as a risk for some at-rest blobs. Which AEAD replaced plain AES-GCM for those, and what was the throughput tradeoff we ended up accepting?",
    # 01147 Argon2id preferred over bcrypt
    "We're standardising on a new password hash for fresh accounts. Which algorithm replaced bcrypt, and how well did its memory-hardness tuning fit into the hot path on login?",
    # 01148 Vault KV v2 version 404 demoted
    "An app hit a confusing 404 on a secret that still existed. Which Vault KV mode are we running, and what specific version state caused the not-found even though the secret wasn't actually deleted?",
    # 01149 eBPF socket filter egress exfil ASN
    "An odd ASN started showing up as a destination from the egress gateway. What detected that shape of traffic, and how fast did the blocklist update close the hole?",
    # 01150 Ed25519 SSH keys RSA grandfather
    "Our SSH key policy has tightened. Which algorithm is mandatory for new enrolments, and what happens to existing RSA-2048 keys until the next rotation sweep?",
    # 01151 vLLM continuous batching PagedAttention
    "Generation throughput jumped recently on our serving stack. Which change in the batching strategy caused the 3x over the old static batcher, and what kept the memory footprint from exploding?",
    # 01152 TensorRT-LLM vs vLLM summarisation
    "We run both vLLM and TensorRT-LLM. Which one wins on single-stream latency for the summarisation endpoint, and which is still the better choice when concurrency matters?",
    # 01153 Triton ensemble scheduler reranker
    "The multi-model gateway needs to chain a reranker after a generator. Which inference server backs that gateway, and what scheduler feature actually pipelines the two steps together?",
    # 01154 Ray Serve replaced Flask idle cost
    "Our old Flask wrappers around model endpoints were expensive to keep running. Which framework took over, and what specifically lowered our idle cost after the switch?",
    # 01155 KServe InferenceService canary traffic split
    "Batch scoring jobs need to be exposed on Kubernetes with progressive rollout. Which CRD surfaces them, and how does canary rollout actually happen now in that setup?",
    # 01156 BentoML packaging vs hand Dockerfiles
    "Our Python dependency pinning in hand-rolled Dockerfiles kept drifting. Which packaging tool beat that approach, and where do the built artifacts end up afterwards?",
    # 01157 Modal Labs embedding backfill cold start
    "Bursty embedding backfills used to blow up cold-start times on our own Lambda attempt. Which platform hosts them now, and roughly how fast is a cold start these days?",
    # 01158 RunPod spot GPUs fine-tune preempt checkpoint
    "Overnight fine-tune jobs need to survive getting kicked off spot instances. Which provider are they running on, and what hook actually makes eviction survivable in practice?",
    # 01159 MLflow tracking signed eval report registry
    "I want to audit how a model got promoted. Which tool holds every fine-tune run, and what has to be attached as an artifact before a model can move into the registry?",
    # 01160 noise
    "The other side said to hold while they check queue depth. Should I treat this as a normal pause in the conversation, or is something actually wrong with the pipeline behind it?",
    # 01161 W&B sweeps LoRA Bayesian
    "LoRA hyperparameter search used to eat a lot of compute. Which tool's sweep feature drove the search, and how did the Bayesian strategy compare to a plain grid run in terms of trials?",
    # 01162 Comet rejected vs W&B dashboards
    "We reviewed experiment trackers for new projects. Which one ended up being picked, which one was rejected, and what specifically tipped the decision between the two?",
    # 01163 Neptune research group notebook REST
    "The research group kept its own tooling. Which tracker did they stay on for notebook-heavy work, and what property of it suited that workflow better than our main stack?",
    # 01164 Feast online Redis offline Snowflake
    "Ranking features need to serve both online and offline with one definition. Which feature store are we using, and which backends are sitting underneath each path?",
    # 01165 Tecton rejected cost Feast Redis
    "Tecton came up as an option for the ranking team. Why didn't we end up buying it, and what setup already covered the lookup SLAs well enough?",
    # 01166 Hopsworks research ops overhead
    "I noticed Hopsworks was on an older cluster. What role did it play there, and what about it didn't scale when only one engineer was running operations?",
    # 01167 Qdrant rejected pgvector shared retrieval
    "The shared retrieval path used to be a fresh decision. Which vector database was considered and rejected, and what operational preference pushed the team toward pgvector instead?",
    # 01168 Weaviate vs Milvus hybrid BM25
    "On the internal eval set we compared two engines on hybrid search. Which one delivered the cleaner top-10 results using BM25 plus vector, and which is still being used because of it?",
    # 01169 Milvus 2.4 archival DiskANN NVMe
    "The archival retrieval service holds a huge corpus. Which version of Milvus stayed on it, and which index type is handling the 120 million vectors off local NVMe?",
    # 01170 LanceDB desktop single file offline
    "The desktop app for field researchers needs offline-friendly storage. Which embedded vector engine runs there, and what about its file layout actually makes offline sync manageable?",
    # 01171 Chroma dropped prototype persistence
    "Chroma was in the original prototype stack. Why did it end up being dropped, and what specifically about its persistence story caused the friction?",
    # 01172 pgvector HNSW maintenance_work_mem
    "HNSW index build times on the 40M-row table were painful. What configuration change made build time drop, and what did that change unblock inside Postgres during the build?",
    # 01173 BGE-large-en-v1.5 MiniLM recall
    "Our document retriever used to run on MiniLM. Which embedder replaced it, and roughly what did recall@20 look like on the eval set before and after the swap?",
    # 01174 E5-Mistral long-form multilingual help
    "The multilingual help centre has long passages. Which embedder is preferred for that kind of content, and what prompting pattern makes it work well in practice?",
    # 01175 Jina v3 8k contracts no chunking
    "The contracts corpus is full of long documents. Which embedder handles those at 8k tokens, and what step in the pipeline did its extended context let us drop entirely?",
    # 01176 Cohere embed-v4 managed customer search
    "Customer-facing search has to keep running without us managing GPUs. Which embedding model is powering it, and what tradeoff did we accept to get out of the ops side?",
    # 01177 NVIDIA MIG A100 20GB vLLM pin
    "One A100 now serves both training and inference. How is the card being split, and which workload is pinned to which slice in the resulting arrangement?",
    # 01178 NVIDIA MPS time-slicing notebook memory cap
    "The shared notebook fleet kept thrashing on CUDA oversubscription. Which GPU-sharing mechanism replaced the naive setup, and what control actually stopped one user from starving the rest?",
    # 01179 xFormers memory-efficient attention FlashAttention-2
    "VRAM on the 7B model training runs was tight. Which kernel change cut 40 percent of the usage first, and what additional optimization shaved more on top of that?",
    # 01180 FlashAttention-3 H100 inference upgrade
    "H100s are online for inference now. Which attention kernel pushed forward-pass throughput up 1.7x over the previous version, and where was it rolled out first?",
    # 01181 AWQ Llama-3-70B 48 GB single card
    "We needed to fit Llama-3-70B on a single 48 GB GPU. Which quantisation scheme got us there, and roughly how much MMLU headroom did we lose in the process?",
    # 01182 GPTQ vs AWQ standardised
    "We trialled two 4-bit quantisation schemes side by side. Which one won on perplexity at the same bitrate, and which did we standardise on for production serving afterwards?",
    # 01183 bitsandbytes 8-bit optimizer RTX 5060
    "LoRA training on a single RTX 5060 looked impossible in full precision. Which library's 8-bit optimizer states made it fit, and what specifically wouldn't have worked without them?",
    # 01184 noise
    "Someone on the other side asked for a second to warm a cache. Should I just keep waiting, or is this pause a sign something's off with what's being served?",
    # 01185 SmoothQuant router W8A8
    "We wanted W8A8 quantisation on the router model without losing output quality. Which technique made that viable, and what was the observed effect on the regression tests?",
    # 01186 speculative decoding 1B draft 70B
    "Latency on the 70B target model dropped noticeably on common prompts. Which decoding technique caused the 2.4x speedup, and does output quality actually change when acceptance happens?",
    # 01187 Medusa vs separate draft model latency variance
    "We evaluated two approaches to speculative decoding. How did Medusa heads compare to a separate draft model, and which path ended up winning at our batch sizes?",
    # 01188 PagedAttention KV sharing chat 28 percent
    "The chat workload was eating KV cache. Which feature actually lets sibling requests share memory, and roughly how much KV cache did we save once it was enabled?",
    # 01189 KV cache eviction priority-by-tokens-seen
    "Long conversations kept losing their system prompts under memory pressure. What was the old eviction policy on the KV cache, and what replaced it so earlier tokens could stick around?",
    # 01190 LoRA adapter hot-swap per tenant
    "Per-tenant adapters used to force cold reloads. When did hot-swap land, and what does each tenant now hit without restarting the serving process?",
    # 01191 LoRA rank 16 vs 32 adapter size
    "We compared two LoRA ranks during the last sweep. Which rank did we prefer for adapter size, and how did that choice affect eval scores and serving memory?",
    # 01192 LangChain dropped RAG debugging
    "The production RAG path used to sit on a familiar framework. Which framework did we drop, and what specifically about it slowed down prompt and retrieval debugging?",
    # 01193 LlamaIndex ingestion postprocessors
    "Our custom serving layer still leans on an ingestion library. Which one continues to load the knowledge base, and which of its extension points slot into our layer cleanly?",
    # 01194 Haystack 2 considered LlamaIndex connectors wash
    "Someone pitched Haystack 2 for internal RAG. Was there a migration planned, and what tipped the comparison toward staying put instead?",
    # 01195 Ragas weekly eval faithfulness context recall
    "On-call wants the simplest eval signal they can look at weekly. Which framework drives the runs, and which two metrics are the ones that actually get read in practice?",
    # 01196 Promptfoo pre-merge config-as-code
    "We want prompt changes reviewed on pull requests, not in a separate UI. Which tool runs the pre-merge regression checks, and what does its config-as-code style give reviewers at review time?",
    # 01197 Helicone OpenAI proxy cost attribution session header
    "OpenAI traffic needs per-user cost attribution. Which proxy are we running, and how does it tie cost back to individual users through what it injects on the way through?",
    # 01198 Braintrust experiment views Jupyter
    "Our eval dashboard used to live in a local Jupyter notebook and kept disappearing with laptop reboots. What replaced it, and how are eval runs now shared across the team?",
    # 01199 Langfuse chat spans autoscaler backpressure
    "The chat app needed richer LLM-call observability. Which tracer was added, and what operational signal does span-level cost and latency feed into downstream?",
    # 01200 LiteLLM gateway prompt cache 35 percent
    "Every provider is behind a single gateway now for the support assistant. Which gateway product does that consolidation, and what cache hit rate has prompt caching reached on the shared system prompts?",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    with SHARED.open("r", encoding="utf-8") as f:
        shared_lines = f.readlines()
    positives = [json.loads(l) for l in shared_lines[SHARED_OFFSET:SHARED_OFFSET + 100]]
    assert len(positives) == 100, f"expected 100 positives, got {len(positives)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (query, pos) in enumerate(zip(QUERIES, positives), start=1):
            row_id = f"ret-{ID_OFFSET + i:05d}"
            row = {
                "id": row_id,
                "source_id": pos["id"],
                "query": query,
                "positive": pos["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
