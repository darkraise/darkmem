import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_chat_service
from app.main import app
from app.services.chat import ChatService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def chat_client(session):
    mock_llm = AsyncMock()

    async def override_chat_service():
        yield ChatService(session, llm=mock_llm)

    from app.database import get_session

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_chat_service] = override_chat_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_create_conversation(chat_client, auth_headers):
    resp = await chat_client.post(
        "/api/v1/chat/conversations",
        json={"title": "Test Convo"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Convo"
    assert "id" in data


async def test_list_conversations(chat_client, auth_headers):
    await chat_client.post(
        "/api/v1/chat/conversations",
        json={"title": "Convo A"},
        headers=auth_headers,
    )
    resp = await chat_client.get(
        "/api/v1/chat/conversations",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["conversations"]) >= 1


async def test_get_conversation_detail(chat_client, auth_headers):
    create_resp = await chat_client.post(
        "/api/v1/chat/conversations",
        json={"title": "Detail Test"},
        headers=auth_headers,
    )
    conv_id = create_resp.json()["id"]
    resp = await chat_client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Test"
    assert "messages" in data


async def test_update_conversation(chat_client, auth_headers):
    create_resp = await chat_client.post(
        "/api/v1/chat/conversations",
        json={"title": "Old Title"},
        headers=auth_headers,
    )
    conv_id = create_resp.json()["id"]
    resp = await chat_client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        json={"title": "New Title"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


async def test_delete_conversation(chat_client, auth_headers):
    create_resp = await chat_client.post(
        "/api/v1/chat/conversations",
        json={},
        headers=auth_headers,
    )
    conv_id = create_resp.json()["id"]
    resp = await chat_client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204


async def test_get_nonexistent_conversation(chat_client, auth_headers):
    resp = await chat_client.get(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_requires_auth(chat_client):
    resp = await chat_client.get("/api/v1/chat/conversations")
    assert resp.status_code == 401
