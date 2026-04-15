"""One-off emitter for classification top-up batch-013 — short ambiguous mixed-domain.

Writes 100 rows to data/v2/classification/batch_013.tmp.jsonl with ids
class-01201..01300. No pair_id. Each row is a short (3-12 word) standalone
statement that is genuinely difficult to classify because it could plausibly
map to multiple memory_types; we assign the best single fit.

Schema: {id, domain, text, memory_type}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_013.tmp.jsonl"
ID_OFFSET = 1200

# (text, memory_type, domain)
# Targets:
#   memory_type: fact=17 (all from noise), decision=14, preference=14,
#                problem=14, reference=14, architecture=14, milestone=13
#   domain: technical=17, ai_coding=17, personal=17, knowledge=16, cross=16, noise=17
ENTRIES: list[tuple[str, str, str]] = [
    # ===== technical (17) =====
    ("We standardized on Postgres for all tenant data.", "decision", "technical"),
    ("Redis is faster than Memcached for our workload.", "preference", "technical"),
    ("The primary node went read-only last Tuesday.", "problem", "technical"),
    ("See RFC 7231 for HTTP method semantics.", "reference", "technical"),
    ("Services talk over a shared message bus.", "architecture", "technical"),
    ("Shipped the cluster autoscaler to production.", "milestone", "technical"),
    ("Kafka consumers rebalance on every restart.", "problem", "technical"),
    ("We picked gRPC over REST for internal calls.", "decision", "technical"),
    ("I like Caddy better than Nginx for autocert.", "preference", "technical"),
    ("The data plane and control plane are separated.", "architecture", "technical"),
    ("Hit 99.99% availability across the quarter.", "milestone", "technical"),
    ("Documentation lives in the internal wiki.", "reference", "technical"),
    ("We moved queues off SQS to NATS.", "decision", "technical"),
    ("The ingress terminates TLS at the edge.", "architecture", "technical"),
    ("Prometheus scrape fails every ten minutes.", "problem", "technical"),
    ("Consul docs cover the ACL model well.", "reference", "technical"),
    ("Completed the Kubernetes 1.29 upgrade rollout.", "milestone", "technical"),

    # ===== ai_coding (17) =====
    ("Prefer Claude over GPT for long refactors.", "preference", "ai_coding"),
    ("We chose LangGraph over bare LangChain.", "decision", "ai_coding"),
    ("Tool calls silently drop when tokens overflow.", "problem", "ai_coding"),
    ("See the Anthropic cookbook on tool use.", "reference", "ai_coding"),
    ("Agents share a single vector memory store.", "architecture", "ai_coding"),
    ("Landed the first autonomous PR agent.", "milestone", "ai_coding"),
    ("Copilot suggestions ignore our lint config.", "problem", "ai_coding"),
    ("I like pair-programming with Cursor most days.", "preference", "ai_coding"),
    ("Settled on Opus for planning, Sonnet for edits.", "decision", "ai_coding"),
    ("The retriever feeds the reranker before the LLM.", "architecture", "ai_coding"),
    ("First successful fine-tune hit 0.82 F1.", "milestone", "ai_coding"),
    ("Refer to the DSPy paper for optimizer details.", "reference", "ai_coding"),
    ("Agents deadlock when two edit the same file.", "problem", "ai_coding"),
    ("Switched from BM25 to hybrid retrieval.", "decision", "ai_coding"),
    ("Embeddings are cached behind a thin service.", "architecture", "ai_coding"),
    ("Closed out the RAG migration epic.", "milestone", "ai_coding"),
    ("The transformer survey covers rotary embeddings.", "reference", "ai_coding"),

    # ===== personal (17) =====
    ("I prefer pour-over coffee in the morning.", "preference", "personal"),
    ("Decided to skip the conference this year.", "decision", "personal"),
    ("My back has been sore since the move.", "problem", "personal"),
    ("Finally ran a half marathon last weekend.", "milestone", "personal"),
    ("Family dinners are Sunday at six.", "architecture", "personal"),
    ("Check the family calendar for birthdays.", "reference", "personal"),
    ("I like quiet cafes better than coworking spaces.", "preference", "personal"),
    ("Cut back on late-night screen time.", "decision", "personal"),
    ("Sleep has been uneven for two weeks.", "problem", "personal"),
    ("Hit my savings goal for the quarter.", "milestone", "personal"),
    ("Morning walks start at seven sharp.", "architecture", "personal"),
    ("Renewed the passport at the city office.", "milestone", "personal"),
    ("Prefer reading paper books over ebooks.", "preference", "personal"),
    ("Switched dentists after the last cleaning.", "decision", "personal"),
    ("The knee flares up during long runs.", "problem", "personal"),
    ("See my notebook for travel checklists.", "reference", "personal"),
    ("Household chores rotate weekly by person.", "architecture", "personal"),

    # ===== knowledge (16) =====
    ("Photosynthesis converts light into chemical energy.", "fact", "knowledge"),
    ("The Treaty of Westphalia was signed in 1648.", "fact", "knowledge"),
    ("Refer to Feynman's lectures volume one.", "reference", "knowledge"),
    ("Euclidean geometry assumes parallel lines never meet.", "reference", "knowledge"),
    ("Historians consider 1914 a turning point.", "decision", "knowledge"),
    ("The ecosystem collapsed after the drought.", "problem", "knowledge"),
    ("Cells are organized into tissues and organs.", "architecture", "knowledge"),
    ("Humans first reached the moon in 1969.", "milestone", "knowledge"),
    ("Economists debate the causes of the crash.", "problem", "knowledge"),
    ("The solar system has eight recognized planets.", "fact", "knowledge"),
    ("Most educators favor active learning methods.", "preference", "knowledge"),
    ("Nations adopted the Paris Agreement in 2016.", "milestone", "knowledge"),
    ("The brain is divided into distinct lobes.", "architecture", "knowledge"),
    ("Philosophers prefer clarity over rhetorical flourish.", "preference", "knowledge"),
    ("Scholars chose the standard model as baseline.", "decision", "knowledge"),
    ("Consult Britannica for historical overviews.", "reference", "knowledge"),

    # ===== cross (16) =====
    ("Our retro was productive but overran by an hour.", "problem", "cross"),
    ("The team picked Friday demos over Monday ones.", "decision", "cross"),
    ("I like async standups more than live ones.", "preference", "cross"),
    ("Onboarding docs live on the team Notion.", "reference", "cross"),
    ("Squads own services end to end.", "architecture", "cross"),
    ("Launched the new design system internally.", "milestone", "cross"),
    ("Hiring stalled for three consecutive sprints.", "problem", "cross"),
    ("Leadership chose quality over speed this half.", "decision", "cross"),
    ("Prefer written decisions to hallway conversations.", "preference", "cross"),
    ("The playbook is pinned in the main channel.", "reference", "cross"),
    ("Cross-team sync runs every other Thursday.", "architecture", "cross"),
    ("Closed the security audit with no criticals.", "milestone", "cross"),
    ("Merges keep blocking on flaky CI jobs.", "problem", "cross"),
    ("Adopted weekly bug-bash afternoons.", "decision", "cross"),
    ("Teams prefer Slack huddles to scheduled calls.", "preference", "cross"),
    ("Reached the quarterly OKR two weeks early.", "milestone", "cross"),

    # ===== noise (17) — all memory_type=fact, off-topic filler =====
    ("The sky looked unusually orange at dusk.", "fact", "noise"),
    ("Lorem ipsum dolor sit amet, consectetur.", "fact", "noise"),
    ("A red balloon drifted over the rooftops.", "fact", "noise"),
    ("She hummed a tune nobody could quite place.", "fact", "noise"),
    ("Asdf qwerty zxcv placeholder content here.", "fact", "noise"),
    ("Penguins waddled across the imaginary beach.", "fact", "noise"),
    ("Random filler sentence number forty-two.", "fact", "noise"),
    ("The teapot whistled in three-quarter time.", "fact", "noise"),
    ("Blue moose danced beneath cardboard stars.", "fact", "noise"),
    ("Quick brown fox jumps over lazy dogs again.", "fact", "noise"),
    ("Nothing meaningful happens in this sentence.", "fact", "noise"),
    ("Bananas rolled gently down the escalator.", "fact", "noise"),
    ("Foo bar baz qux quux corge grault.", "fact", "noise"),
    ("A polite toaster applied for a library card.", "fact", "noise"),
    ("The hat fit the cat, more or less.", "fact", "noise"),
    ("Marbles scattered across the mahogany table.", "fact", "noise"),
    ("Jello wobbled at precisely seven in the evening.", "fact", "noise"),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    assert len(ENTRIES) == 100, f"expected 100 entries, got {len(ENTRIES)}"
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, mt, domain) in enumerate(ENTRIES, start=1):
            row = {
                "id": f"class-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(ENTRIES)


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
