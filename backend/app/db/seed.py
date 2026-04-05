import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SystemPromptProfile

logger = logging.getLogger(__name__)

PROFILES = [
    {
        "purpose": "extraction",
        "display_name": "Knowledge Extraction",
        "content": (
            "You are a knowledge extraction engine. Extract structured information from text.\n"
            "Return ONLY valid JSON with no additional text."
        ),
        "is_editable": True,
    },
    {
        "purpose": "summarization",
        "display_name": "Summarization",
        "content": "You are a code documentation assistant. Be concise and precise.",
        "is_editable": True,
    },
    {
        "purpose": "chat",
        "display_name": "Chat Assistant",
        "content": (
            "You are a knowledge assistant for a personal memory system called darkmem. "
            "Answer questions based on the retrieved memories and entity data provided below. "
            "When citing information, reference the memory source and content. "
            "If the retrieved context doesn't contain enough information to answer, say so honestly. "
            "Keep answers concise and well-structured. Use markdown formatting."
        ),
        "is_editable": True,
    },
    {
        "purpose": "reasoning",
        "display_name": "Reasoning",
        "content": (
            "You are a knowledge retrieval assistant. Answer questions using only the provided memory context. "
            "Be concise and accurate."
        ),
        "is_editable": True,
    },
    {
        "purpose": "cluster_naming",
        "display_name": "Cluster Naming",
        "content": (
            "You are a naming assistant. Given a group of related memory snippets, "
            "generate a short descriptive name (2-4 words, no quotes). "
            "Just output the name, nothing else."
        ),
        "is_editable": True,
    },
    {
        "purpose": "agent_instructions",
        "display_name": "Agent Instructions",
        "content": (
            "darkmem is a centralized memory and code knowledge system for AI agents.\n"
            "\n"
            "## Memory tools\n"
            "Use memory_search at the start of conversations to retrieve relevant context. "
            "Save important decisions, debugging insights, preferences, and project context with memory_add. "
            "Always include project/<repo-name> tags.\n"
            "\n"
            "## Code knowledge tools\n"
            "Indexed codebases are available for semantic search and structural exploration:\n"
            "- **code_search**: Find relevant code by natural language description. "
            "Use this BEFORE reading files to reduce token usage.\n"
            "- **code_symbol**: Look up a function/class by name — get source, summary, signature, and location.\n"
            "- **code_file_symbols**: List all symbols in a file to understand its structure before reading it.\n"
            "- **code_blast_radius**: Before refactoring, check what depends on a symbol. "
            "Walks the call graph transitively.\n"
            "- **code_dependencies**: Show import relationships for a file or repo.\n"
            "- **list_repos**: See which repositories are indexed.\n"
            "\n"
            "### Priority order\n"
            "1. Use code_search to find relevant code\n"
            "2. Use code_file_symbols to understand file structure\n"
            "3. Only read the actual file if you need full context\n"
            "4. Use code_blast_radius before any refactoring"
        ),
        "is_editable": True,
    },
]


async def seed_profiles(session: AsyncSession):
    for profile_data in PROFILES:
        result = await session.execute(
            select(SystemPromptProfile).where(
                SystemPromptProfile.purpose == profile_data["purpose"]
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            continue

        profile = SystemPromptProfile(**profile_data)
        session.add(profile)
        logger.info(f"Seeded profile: {profile_data['purpose']}")

    await session.commit()
