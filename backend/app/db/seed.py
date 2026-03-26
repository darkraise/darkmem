import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.config import SystemPromptProfile

logger = logging.getLogger(__name__)

PROFILES = [
    {
        "name": "default",
        "display_name": "Default",
        "content": """You have access to a centralized memory system. Use it to store and retrieve important context.

## When to save
- Decisions and their reasoning
- User preferences and corrections
- Infrastructure details (IPs, ports, services)
- Debugging insights and root causes
- Project context (deadlines, people, constraints)

## When to search
- At the start of conversations for relevant context
- When working on unfamiliar code or systems
- Before making architectural decisions

## Tagging
Use slash-separated tags: project/<name>, infra/<component>, user/preferences, debug/root-cause""",
        "save_triggers": {"decisions": True, "preferences": True, "infrastructure": True, "debugging": True},
        "search_behavior": {"on_start": True, "on_unfamiliar": True, "frequency": "balanced"},
        "tagging_conventions": {"prefixes": ["project", "infra", "user", "debug", "workflow"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.9, "auto_merge": False},
        "is_default": True,
    },
    {
        "name": "coding-assistant",
        "display_name": "Coding Assistant",
        "content": """You have access to a centralized memory system optimized for software development.

## When to save
- Architectural decisions and trade-offs
- Debugging insights: what failed and why
- Code patterns and conventions specific to this project
- User corrections to your behavior
- Cross-session context (what was started but not finished)

## When to search
- At conversation start: search for project context
- When touching unfamiliar code areas
- Before proposing architectural changes
- When debugging: search for past similar issues

## Tagging
- project/<repo-name> — always include
- debug/root-cause, debug/workaround
- project/decisions, project/architecture
- feedback/behavior, feedback/style""",
        "save_triggers": {"decisions": True, "preferences": True, "debugging": True, "architecture": True, "corrections": True},
        "search_behavior": {"on_start": True, "on_unfamiliar": True, "frequency": "aggressive"},
        "tagging_conventions": {"prefixes": ["project", "debug", "feedback", "workflow"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.85, "auto_merge": False},
        "is_default": False,
    },
    {
        "name": "devops-agent",
        "display_name": "DevOps Agent",
        "content": """You have access to a centralized memory system optimized for infrastructure work.

## When to save
- Service configurations, IPs, ports
- Networking topology and routing rules
- Incident root causes and resolutions
- Configuration gotchas and workarounds
- Version incompatibilities encountered

## When to search
- Before modifying any service configuration
- When debugging infrastructure issues
- When setting up new services

## Tagging
- infra/services, infra/networking, infra/environment
- debug/root-cause, debug/workaround, debug/gotcha
- workflow/migration, workflow/performance""",
        "save_triggers": {"infrastructure": True, "debugging": True, "networking": True, "incidents": True},
        "search_behavior": {"on_start": True, "on_unfamiliar": True, "frequency": "aggressive"},
        "tagging_conventions": {"prefixes": ["infra", "debug", "workflow"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.9, "auto_merge": False},
        "is_default": False,
    },
    {
        "name": "research-agent",
        "display_name": "Research Agent",
        "content": """You have access to a centralized memory system optimized for knowledge gathering.

## When to save
- Facts and findings from research
- Sources and references
- Summaries of long documents
- Comparisons and evaluations

## When to search
- Always search before saving to avoid duplicates
- Search for existing knowledge before researching

## Tagging
- research/findings, research/sources
- project/<topic>""",
        "save_triggers": {"facts": True, "sources": True, "summaries": True},
        "search_behavior": {"on_start": True, "before_save": True, "frequency": "aggressive"},
        "tagging_conventions": {"prefixes": ["research", "project"]},
        "extraction_depth": "full",
        "dedup_strategy": {"threshold": 0.8, "auto_merge": True},
        "is_default": False,
    },
    {
        "name": "automation",
        "display_name": "Automation",
        "content": """Centralized memory system for automated pipelines. Store structured data. Minimal LLM processing.

Save: pipeline results, job outputs, structured findings.
Search: by tags for specific data.
Tags: automation/<pipeline-name>, data/<type>""",
        "save_triggers": {"results": True, "outputs": True},
        "search_behavior": {"on_start": False, "frequency": "minimal"},
        "tagging_conventions": {"prefixes": ["automation", "data"]},
        "extraction_depth": "light",
        "dedup_strategy": {"threshold": 0.95, "auto_merge": False},
        "is_default": False,
    },
    {
        "name": "minimal",
        "display_name": "Minimal",
        "content": "Raw memory storage. No LLM processing. Store and retrieve content as-is.",
        "save_triggers": {},
        "search_behavior": {"on_start": False, "frequency": "none"},
        "tagging_conventions": {"prefixes": []},
        "extraction_depth": "none",
        "dedup_strategy": {"threshold": 1.0, "auto_merge": False},
        "is_default": False,
    },
]


async def seed_profiles(session: AsyncSession):
    for profile_data in PROFILES:
        existing = await session.execute(
            select(SystemPromptProfile).where(SystemPromptProfile.name == profile_data["name"])
        )
        if existing.scalar_one_or_none():
            continue

        profile = SystemPromptProfile(**profile_data)
        session.add(profile)
        logger.info(f"Seeded profile: {profile_data['name']}")

    await session.commit()


async def seed_default_api_key(session: AsyncSession):
    from app.api.auth import hash_api_key
    from app.config import settings

    raw_key = settings.default_api_key
    key_hash = hash_api_key(raw_key)

    existing = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if existing.scalar_one_or_none():
        return

    key = ApiKey(
        name="default-admin",
        key_hash=key_hash,
        scopes=["read", "write", "admin"],
        profile="default",
    )
    session.add(key)
    await session.commit()
    logger.info(f"Seeded default admin API key: {raw_key}")
