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
    """T1.60 Step 5: the live SSE `sources` event's formatted_memories dicts
    (`_retrieve`) previously had no `id` key at all — only the persisted
    snapshot (`send_message`'s assistant_msg.context) did, breaking
    citation links during a live stream specifically."""

    @pytest_asyncio.fixture
    async def chat_service(self, session):
        from unittest.mock import AsyncMock
        llm = AsyncMock()
        llm.embed = AsyncMock(return_value=([0.0], "fp"))
        vector_repo = AsyncMock()
        return ChatService(session, llm, vector_repo=vector_repo)

    @pytest.mark.asyncio
    async def test_retrieve_includes_the_memory_id_on_every_formatted_row(
        self, chat_service
    ):
        seeded_id = uuid.uuid4()
        chat_service.vector_repo.search.return_value = [
            {
                "memory_id": seeded_id,
                "score": 0.9,
                "payload": {"content": "x", "source": "api", "tags": []},
                "project": "default",
                "status": "active",
            }
        ]

        result = await chat_service._retrieve("question")

        assert result["memories"][0]["id"] == str(seeded_id)

    @pytest.mark.asyncio
    async def test_retrieve_fails_loud_when_memory_id_is_absent(self, chat_service):
        # A row missing memory_id should be structurally impossible from
        # PostgresVectorRepository.search() — direct indexing (not
        # `.get(..., "")`) makes that assumption fail loud instead of
        # degrading into a dead, unclickable citation.
        chat_service.vector_repo.search.return_value = [
            {
                "score": 0.9,
                "payload": {"content": "x", "source": "api", "tags": []},
                "project": "default",
                "status": "active",
            }
        ]

        with pytest.raises(KeyError):
            await chat_service._retrieve("question")
