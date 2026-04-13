"""Domain definitions for fine-tuning data generation.

Each domain specifies entity types, relationship types, content categories
with target counts, and an example prompt hint for Claude.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentCategory:
    name: str
    count: int
    hint: str


@dataclass(frozen=True)
class DomainConfig:
    name: str
    entity_types: list[str]
    relationship_types: list[str]
    categories: list[ContentCategory]
    memory_types: list[str]

    @property
    def total(self) -> int:
        return sum(c.count for c in self.categories)


TECHNICAL = DomainConfig(
    name="technical",
    entity_types=[
        "technology", "service", "library", "database", "framework",
        "protocol", "algorithm", "project", "language", "platform",
        "infrastructure",
    ],
    relationship_types=[
        "USES", "DEPENDS_ON", "REPLACES", "IMPROVES_ON", "IS_A",
        "HAS_PART", "COMMUNICATES_WITH", "DEPLOYED_ON", "PRODUCES",
        "IMPLEMENTS",
    ],
    categories=[
        ContentCategory("dev_decision", 400,
                        "switched from X to Y, chose X over Y, decided to use X"),
        ContentCategory("debug_root_cause", 300,
                        "found the bug in X, root cause was Y, fixed by Z"),
        ContentCategory("architecture", 300,
                        "multi-entity system descriptions with HAS_PART relationships"),
        ContentCategory("dependency_config", 250,
                        "X depends on Y, X communicates with Y, requires Z"),
        ContentCategory("code_knowledge", 200,
                        "project X uses library Y, implemented with Z"),
        ContentCategory("deployment", 150,
                        "deployed X on Y, running X in Z container"),
        ContentCategory("protocol_standard", 150,
                        "implements OAuth2, uses gRPC protocol, follows REST"),
        ContentCategory("migration_upgrade", 100,
                        "upgraded from X to Y, migrated from A to B"),
        ContentCategory("edge_cases", 150,
                        "acronyms, lists of technologies, hypothetical mentions, multi-paragraph"),
    ],
    memory_types=["fact", "decision", "architecture", "debug", "workflow"],
)

AI_CODING = DomainConfig(
    name="ai_coding",
    entity_types=[
        "technology", "service", "library", "database", "framework",
        "project", "language", "platform", "file", "command", "error",
        "config", "pattern", "api",
    ],
    relationship_types=[
        "USES", "DEPENDS_ON", "REPLACES", "FIXES", "IMPLEMENTS",
        "CONFIGURES", "PRODUCES", "DEPLOYED_ON", "EXTENDS", "CAUSES",
    ],
    categories=[
        ContentCategory("debug_session", 200,
                        "found the bug in auth_middleware.py line 42, the token expiry check was wrong"),
        ContentCategory("architectural_decision", 150,
                        "Claude suggested factory pattern, went with that over strategy pattern"),
        ContentCategory("dependency_discovery", 150,
                        "installed gliner-finetune, it requires torch>=2.0 and datasets>=2.14"),
        ContentCategory("config_fix", 100,
                        "had to set num_gpu: 999 in Ollama options to force full GPU offload"),
        ContentCategory("code_pattern", 100,
                        "async context manager pattern needs __aenter__ and __aexit__"),
        ContentCategory("error_resolution", 80,
                        "TypeError: expected str got UUID, fixed by calling str() on memory_id"),
        ContentCategory("environment_setup", 80,
                        "RTX 5060 needs CUDA 12.8, pip install torch with cu128 index"),
        ContentCategory("workaround_gotcha", 60,
                        "GLiNER on CUDA before Ollama embedding calls causes hang"),
        ContentCategory("session_summary", 50,
                        "finished implementing extraction pipeline v2 with tool calling and dedup"),
        ContentCategory("noise", 30,
                        "let me think about this, that looks right, moving on to next task"),
        ContentCategory("refactoring", 350,
                        "extracted validation logic from routes.py into validators.py, refactored to use strategy pattern"),
        ContentCategory("test_strategy", 300,
                        "added integration tests for the auth flow, mocking the OAuth provider but hitting real DB"),
        ContentCategory("git_workflow", 200,
                        "rebased feature branch onto main, resolved merge conflict in schema.prisma"),
        ContentCategory("ci_cd_pipeline", 200,
                        "GitHub Actions workflow fails on Windows because path separator, added cross-platform fix"),
        ContentCategory("api_design", 200,
                        "designed /api/v2/memories endpoint with cursor pagination, returns 50 per page"),
        ContentCategory("performance_fix", 200,
                        "N+1 query in the graph endpoint, added select_related and prefetch, latency dropped from 800ms to 50ms"),
        ContentCategory("security_fix", 150,
                        "found SQL injection in search endpoint, switched to parameterized queries"),
        ContentCategory("code_review_feedback", 150,
                        "PR review: extract the retry logic into a decorator, add timeout to the HTTP client"),
        ContentCategory("database_migration", 150,
                        "Alembic migration adds index on memories.created_at, took 30s on 1M rows"),
        ContentCategory("package_management", 100,
                        "pinned transformers to 4.45.0 because 4.46 breaks the tokenizer cache"),
    ],
    memory_types=["fact", "decision", "debug", "session", "workflow"],
)

PERSONAL = DomainConfig(
    name="personal",
    entity_types=[
        "person", "place", "organization", "event", "date",
        "food", "activity", "goal", "emotion", "hobby",
    ],
    relationship_types=[
        "KNOWS", "LIVES_IN", "WORKS_AT", "VISITED", "HAPPENED_ON",
        "FEELS_ABOUT", "PLANS_TO", "PART_OF", "LOCATED_IN", "PREFERS",
    ],
    categories=[
        ContentCategory("social_people", 300,
                        "had lunch with Alex, Alex works at Google, met Sarah at the conference"),
        ContentCategory("place_travel", 200,
                        "visited Tokyo last March, favorite cafe in downtown Portland"),
        ContentCategory("preference_taste", 200,
                        "love Italian food, prefer dark mode, always use vim"),
        ContentCategory("plan_goal", 150,
                        "want to learn Rust by December, planning to run a marathon"),
        ContentCategory("milestone_achievement", 150,
                        "finished the marathon, got promoted to senior engineer"),
        ContentCategory("emotional_reflection", 100,
                        "feeling overwhelmed by the workload, grateful for the team"),
        ContentCategory("routine_habit", 100,
                        "started morning runs on Tuesdays, weekly book club on Fridays"),
    ],
    memory_types=["fact", "preference", "decision", "session"],
)

KNOWLEDGE = DomainConfig(
    name="knowledge",
    entity_types=[
        "concept", "theory", "person", "organization", "publication",
        "method", "finding", "claim", "field", "tool",
    ],
    relationship_types=[
        "SUPPORTS", "CONTRADICTS", "BUILDS_ON", "AUTHORED_BY",
        "PUBLISHED_IN", "APPLIES_TO", "EXAMPLE_OF", "RELATED_TO",
        "CAUSES", "MEASURES",
    ],
    categories=[
        ContentCategory("factual_claim", 300,
                        "quantum entanglement does not enable FTL communication"),
        ContentCategory("method_technique", 250,
                        "RAG combines retrieval with generation, HNSW uses skip-list graphs"),
        ContentCategory("publication_reference", 200,
                        "published in Nature 2025, Vaswani et al introduced the transformer"),
        ContentCategory("cause_effect", 150,
                        "sleep deprivation causes impaired judgment, overfitting leads to poor generalization"),
        ContentCategory("comparison_contrast", 150,
                        "HNSW outperforms IVF on recall, BERT is slower but more accurate than TF-IDF"),
        ContentCategory("definition_explanation", 150,
                        "a knowledge graph is a structured representation of entities and relations"),
    ],
    memory_types=["fact", "decision", "architecture"],
)

ALL_DOMAINS: list[DomainConfig] = [TECHNICAL, AI_CODING, PERSONAL, KNOWLEDGE]

CROSS_DOMAIN_COUNT = 300
NOISE_COUNT = 300

TOTAL_EXAMPLES = sum(d.total for d in ALL_DOMAINS) + CROSS_DOMAIN_COUNT + NOISE_COUNT

ALL_ENTITY_TYPES: list[str] = sorted(set(
    t for d in ALL_DOMAINS for t in d.entity_types
))

ALL_RELATIONSHIP_TYPES: list[str] = sorted(set(
    t for d in ALL_DOMAINS for t in d.relationship_types
))

ALL_MEMORY_TYPES: list[str] = sorted(set(
    t for d in ALL_DOMAINS for t in d.memory_types
))
