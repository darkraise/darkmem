import re
import uuid
from collections.abc import AsyncGenerator
from sqlalchemy import select, func as sa_func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message
from app.services.llm import LLMOrchestrator
from app.repositories.vector import QdrantVectorRepository
from app.repositories.graph import Neo4jGraphRepository

SYSTEM_PROMPT = (
    "You are a knowledge assistant for a personal memory system called darkmem. "
    "Answer questions based on the retrieved memories and entity data provided below. "
    "When citing information, reference the memory source and content. "
    "If the retrieved context doesn't contain enough information to answer, say so honestly. "
    "Keep answers concise and well-structured. Use markdown formatting."
)

MENTION_RE = re.compile(r"@([\w./-]+)")
CLUSTER_RE = re.compile(r"@cluster:(\d+)")

MAX_HISTORY_MESSAGES = 20


class ChatService:
    def __init__(
        self,
        session: AsyncSession,
        llm: LLMOrchestrator,
        vector_repo: QdrantVectorRepository | None = None,
        graph_repo: Neo4jGraphRepository | None = None,
    ):
        self.session = session
        self.llm = llm
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo

    # ── Conversation CRUD ─────────────────────────────────

    async def list_conversations(
        self, limit: int = 50, offset: int = 0, archived: bool = False
    ) -> list[dict]:
        stmt = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.created_at,
                Conversation.updated_at,
                Conversation.is_archived,
                sa_func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message)
            .where(Conversation.is_archived == archived)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "is_archived": r.is_archived,
                "message_count": r.message_count,
            }
            for r in rows
        ]

    async def create_conversation(self, title: str | None = None) -> Conversation:
        conv = Conversation(title=title)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def update_conversation(
        self, conversation_id: uuid.UUID, title: str | None = None, is_archived: bool | None = None
    ) -> Conversation | None:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return None
        if title is not None:
            conv.title = title
        if is_archived is not None:
            conv.is_archived = is_archived
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return False
        await self.session.delete(conv)
        await self.session.flush()
        return True

    # ── Chat Completion ───────────────────────────────────

    async def send_message(
        self,
        conversation_id: uuid.UUID | None,
        content: str,
        context: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Yields SSE event dicts: {type, ...payload}"""

        # Create conversation if needed
        if conversation_id is None:
            conv = await self.create_conversation()
            conversation_id = conv.id
        else:
            conv = await self.get_conversation(conversation_id)
            if not conv:
                yield {"type": "error", "message": "Conversation not found"}
                return

        # Save user message
        user_msg = Message(conversation_id=conversation_id, role="user", content=content)
        self.session.add(user_msg)
        await self.session.flush()

        # Retrieve context
        retrieval = await self._retrieve(content, context)

        # Emit sources event
        yield {
            "type": "sources",
            "memories": retrieval["memories"],
            "entities": retrieval["entities"],
        }

        # Build LLM messages
        llm_messages = await self._build_prompt(conversation_id, content, retrieval)

        # Stream LLM response
        full_response = []
        async for token in self.llm.chat_completion_stream("reasoning", llm_messages):
            full_response.append(token)
            yield {"type": "token", "content": token}

        # Save assistant message
        assistant_content = "".join(full_response)
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            context={
                "memories": [
                    {
                        "id": str(m["memory_id"]),
                        "score": m.get("score", 0),
                        "content": m.get("payload", {}).get("content", "")[:150],
                        "source": m.get("payload", {}).get("source", ""),
                        "tags": m.get("payload", {}).get("tags", []),
                        "created_at": m.get("payload", {}).get("created_at", ""),
                    }
                    for m in retrieval["raw_memories"]
                ],
                "entities": [
                    {
                        "id": e.get("id", ""),
                        "name": e["name"],
                        "entity_type": e.get("entity_type", ""),
                    }
                    for e in retrieval["entities"]
                    if not e.get("_relation")
                ],
            },
        )
        self.session.add(assistant_msg)
        await self.session.flush()

        # Auto-title if first message
        if conv and not conv.title:
            conv.title = content[:60] + ("…" if len(content) > 60 else "")
            await self.session.flush()

        # Update conversation timestamp
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=sa_func.now())
        )
        await self.session.flush()

        yield {
            "type": "done",
            "message_id": str(assistant_msg.id),
            "conversation_id": str(conversation_id),
        }

    # ── Retrieval ─────────────────────────────────────────

    async def _retrieve(self, question: str, context: dict | None = None) -> dict:
        import asyncio

        context = context or {}
        mentions = set(MENTION_RE.findall(question))
        if context.get("mentions"):
            mentions.update(context["mentions"])

        memories_task = self._search_memories(question)

        entity_names = [m for m in mentions if not m.startswith("cluster:")]
        graph_task = self._lookup_entities(
            entity_names,
            context.get("selected_entity_id"),
            context.get("selected_node_id"),
        )

        raw_memories, entities = await asyncio.gather(memories_task, graph_task)

        # Auto-discover entities from top retrieved memories
        if not entities and self.graph_repo and raw_memories:
            entities = await self._entities_from_memories(raw_memories[:5])

        formatted_memories = []
        for i, m in enumerate(raw_memories, 1):
            payload = m.get("payload", {})
            formatted_memories.append({
                "index": i,
                "content": payload.get("content", ""),
                "source": payload.get("source", ""),
                "tags": payload.get("tags", []),
                "score": round(m.get("score", 0), 3),
            })

        return {
            "memories": formatted_memories,
            "entities": entities,
            "raw_memories": raw_memories,
        }

    async def _search_memories(self, query: str, limit: int = 10) -> list[dict]:
        if not self.vector_repo:
            return []
        vector = await self.llm.embed(query)
        return await self.vector_repo.search(vector, limit=limit)

    async def _lookup_entities(
        self,
        entity_names: list[str],
        selected_entity_id: str | None = None,
        selected_node_id: str | None = None,
    ) -> list[dict]:
        if not self.graph_repo:
            return []

        entities = []

        if selected_entity_id:
            result = await self.graph_repo.get_neighbors_by_id(selected_entity_id)
            if result.get("entity"):
                entities.append(result["entity"])
                entities.extend(result.get("neighbors", [])[:5])

        for name in entity_names[:5]:
            found = await self.graph_repo.get_entities(name_query=name, limit=1)
            for e in found:
                if not any(ex.get("name") == e["name"] for ex in entities):
                    entities.append(e)
                    neighbors = await self.graph_repo.get_neighbors_by_id(e["id"])
                    for rel in neighbors.get("relations", [])[:5]:
                        entities.append({"_relation": True, **rel})

        return entities

    async def _entities_from_memories(self, memories: list[dict], max_entities: int = 10) -> list[dict]:
        import asyncio

        mids = [
            str(m.get("memory_id", m.get("id", "")))
            for m in memories
            if m.get("memory_id") or m.get("id")
        ]
        if not mids:
            return []

        results = await asyncio.gather(
            *(self.graph_repo.get_entities_by_memory_id(mid) for mid in mids)
        )

        seen_names: set[str] = set()
        entities: list[dict] = []
        for linked in results:
            for e in linked:
                name = e.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    entities.append(e)
                    if len(entities) >= max_entities:
                        return entities
        return entities

    # ── Prompt Building ───────────────────────────────────

    async def _build_prompt(
        self, conversation_id: uuid.UUID, current_message: str, retrieval: dict
    ) -> list[dict]:
        messages: list[dict] = []

        context_parts = [SYSTEM_PROMPT, "", "## Retrieved Memories", ""]
        for m in retrieval["memories"]:
            context_parts.append(
                f"[{m['index']}] (source: {m['source']}, tags: {', '.join(m['tags'])}, relevance: {m['score']})\n{m['content']}"
            )

        entity_facts = [e for e in retrieval["entities"] if not e.get("_relation")]
        relations = [e for e in retrieval["entities"] if e.get("_relation")]

        if entity_facts:
            context_parts.append("")
            context_parts.append("## Entity Knowledge")
            for e in entity_facts:
                context_parts.append(f"- {e.get('name', '?')} ({e.get('entity_type', '?')})")

        if relations:
            context_parts.append("")
            context_parts.append("## Entity Relationships")
            for r in relations:
                context_parts.append(f"- {r.get('source', '?')} --[{r.get('type', '?')}]--> {r.get('target', '?')}")

        messages.append({"role": "system", "content": "\n".join(context_parts)})

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(MAX_HISTORY_MESSAGES + 1)
        )
        history = list(reversed((await self.session.execute(stmt)).scalars().all()))

        for msg in history[:-1]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": current_message})
        return messages
