import uuid

import pytest
import pytest_asyncio
from app.models.chat import Conversation, Message
from app.services.chat import ChatService, MENTION_RE


class TestChatModels:
    @pytest.mark.asyncio
    async def test_create_conversation(self, session):
        conv = Conversation(title="Test Chat")
        session.add(conv)
        await session.flush()
        assert conv.id is not None
        assert conv.title == "Test Chat"
        assert conv.is_archived is False

    @pytest.mark.asyncio
    async def test_create_message(self, session):
        conv = Conversation()
        session.add(conv)
        await session.flush()

        msg = Message(conversation_id=conv.id, role="user", content="Hello")
        session.add(msg)
        await session.flush()
        assert msg.id is not None
        assert msg.role == "user"

    @pytest.mark.asyncio
    async def test_cascade_delete(self, session):
        conv = Conversation()
        session.add(conv)
        await session.flush()

        msg = Message(conversation_id=conv.id, role="user", content="Hello")
        session.add(msg)
        await session.flush()

        await session.delete(conv)
        await session.flush()

        result = await session.get(Message, msg.id)
        assert result is None


class TestMentionParsing:
    def test_extract_entity_mentions(self):
        matches = MENTION_RE.findall("What about @PostgreSQL and @Docker?")
        assert "PostgreSQL" in matches
        assert "Docker" in matches

    def test_extract_cluster_mentions(self):
        from app.services.chat import CLUSTER_RE
        match = CLUSTER_RE.search("Tell me about @cluster:3")
        assert match is not None
        assert match.group(1) == "3"

    def test_no_mentions(self):
        matches = MENTION_RE.findall("Just a normal question")
        assert len(matches) == 0


class TestChatServiceCRUD:
    @pytest_asyncio.fixture
    async def chat_service(self, session):
        from unittest.mock import AsyncMock
        llm = AsyncMock()
        return ChatService(session, llm)

    @pytest.mark.asyncio
    async def test_create_and_list_conversations(self, chat_service):
        await chat_service.create_conversation(title="Chat 1")
        await chat_service.create_conversation(title="Chat 2")
        convs = await chat_service.list_conversations()
        assert len(convs) >= 2

    @pytest.mark.asyncio
    async def test_update_conversation_title(self, chat_service):
        conv = await chat_service.create_conversation(title="Old")
        updated = await chat_service.update_conversation(conv.id, title="New")
        assert updated.title == "New"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, chat_service):
        conv = await chat_service.create_conversation()
        deleted = await chat_service.delete_conversation(conv.id)
        assert deleted is True
        result = await chat_service.get_conversation(conv.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, chat_service):
        import uuid
        deleted = await chat_service.delete_conversation(uuid.uuid4())
        assert deleted is False


class TestChatServiceRetrieveSourcesId:
    """T1.60 Step 5: the live SSE `sources` event's formatted rows
    (`_retrieve`) previously had no `id` key at all — only the persisted
    snapshot (`send_message`'s assistant_msg.context) did, breaking
    citation links during a live stream specifically.

    T2.58 moved the rows underneath these assertions from
    `vector_repo.search` to the composition, so the id now arrives already
    normalised to `str` by the composition's admission step. The pair of
    assertions is unchanged in intent: a row that reaches the panel carries an
    id, and a row that cannot be keyed is never quietly served without one.
    """

    @pytest_asyncio.fixture
    async def chat_service(self, session):
        from unittest.mock import AsyncMock
        llm = AsyncMock()
        llm.embed = AsyncMock(return_value=([0.0], "fp"))
        return ChatService(session, llm)

    @staticmethod
    def _stub_memory_channel(monkeypatch, rows):
        from app.services import hybrid_search

        async def _search_with_trace(self, query, **kwargs):
            return hybrid_search.ChannelTrace(results=list(rows))

        monkeypatch.setattr(
            hybrid_search.HybridSearchService, "search_with_trace", _search_with_trace,
        )

    @pytest.mark.asyncio
    async def test_retrieve_includes_the_memory_id_on_every_formatted_row(
        self, chat_service, session, monkeypatch
    ):
        from app.models.memory import Memory

        memory = Memory(
            id=uuid.uuid4(), content="x", source="api", importance=0.5,
            metadata_={}, project="default", status="active", is_archived=False,
        )
        session.add(memory)
        await session.flush()
        self._stub_memory_channel(monkeypatch, [
            {
                "memory_id": memory.id,
                "score": 0.9,
                "rrf_score": 0.9,
                "payload": {"content": "x", "source": "api", "tags": []},
                "project": "default",
                "status": "active",
            }
        ])

        result = await chat_service._retrieve("question")

        assert result["memories"][0]["id"] == str(memory.id)

    @pytest.mark.asyncio
    async def test_retrieve_lets_an_unkeyable_row_raise_rather_than_degrade(
        self, chat_service, monkeypatch
    ):
        # A row missing memory_id is structurally impossible from either
        # hybrid arm, so one arriving is a defect in the producer and not an
        # outage in it. The composition refuses to key it, and chat lets that
        # refusal out: reported as a degraded turn instead, it would claim the
        # channels failed when they answered perfectly well, and would send an
        # operator to the database for a bug that lives in the code. The
        # sibling MCP door propagates the same class of error.
        self._stub_memory_channel(monkeypatch, [
            {
                "score": 0.9,
                "payload": {"content": "x", "source": "api", "tags": []},
                "project": "default",
                "status": "active",
            }
        ])

        with pytest.raises(TypeError):
            await chat_service._retrieve("question")
