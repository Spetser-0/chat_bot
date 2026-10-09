"""
tests/integration/test_conversations_api.py
──────────────────────────────────────────
Phase 9, Lesson 9.4 — conversation CRUD for the chat sidebar.

Covers: list, detail+messages, rename, archive toggle, hard delete,
ownership enforcement, auth required, validation errors.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
)


async def _make_user(db) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"conv_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Conv Tester",
        password_hash=hash_password("pass12345"),
        role="student",
        status="active",
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


def _client(app: FastAPI, user: Student) -> AsyncClient:
    token = create_session_token(user.id, user.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    )


async def _make_conversation(db, user: Student, *, title="محادثة تجريبية",
                             archived=False) -> Conversation:
    conv = Conversation(
        id=uuid.uuid4(),
        user_id=user.id,
        title=title,
        is_archived=archived,
    )
    db.add(conv)
    await db.flush()
    for text, role in [("مرحباً", MessageRole.USER), ("أهلاً!", MessageRole.ASSISTANT)]:
        db.add(Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=role,
            content=text,
        ))
    await db.commit()
    await db.refresh(conv)
    return conv


class TestConversationCRUD:
    @pytest.mark.asyncio
    async def test_requires_auth(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            assert (await c.get("/api/v1/conversations")).status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty_then_populated(self, app, db):
        user = await _make_user(db)
        async with _client(app, user) as c:
            assert (await c.get("/api/v1/conversations")).json() == []
            await _make_conversation(db, user)
            resp = await c.get("/api/v1/conversations")
            assert resp.status_code == 200
            items = resp.json()
            assert len(items) == 1
            assert items[0]["title"] == "محادثة تجريبية"

    @pytest.mark.asyncio
    async def test_list_excludes_archived_by_default(self, app, db):
        user = await _make_user(db)
        await _make_conversation(db, user, title="visible")
        await _make_conversation(db, user, title="hidden", archived=True)
        async with _client(app, user) as c:
            items = (await c.get("/api/v1/conversations")).json()
            assert [i["title"] for i in items] == ["visible"]
            items = (await c.get("/api/v1/conversations",
                                 params={"include_archived": True})).json()
            assert len(items) == 2

    @pytest.mark.asyncio
    async def test_detail_includes_messages_chronological(self, app, db):
        user = await _make_user(db)
        conv = await _make_conversation(db, user)
        async with _client(app, user) as c:
            resp = await c.get(f"/api/v1/conversations/{conv.id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(conv.id)
            assert [m["role"] for m in data["messages"]] == ["user", "assistant"]
            assert data["messages"][0]["content"] == "مرحباً"

    @pytest.mark.asyncio
    async def test_ownership_enforced(self, app, db):
        owner = await _make_user(db)
        other = await _make_user(db)
        conv = await _make_conversation(db, owner)
        async with _client(app, other) as c:
            assert (await c.get(f"/api/v1/conversations/{conv.id}")).status_code == 403
            assert (await c.patch(
                f"/api/v1/conversations/{conv.id}", json={"title": "x"}
            )).status_code == 403
            assert (await c.delete(
                f"/api/v1/conversations/{conv.id}"
            )).status_code == 403

    @pytest.mark.asyncio
    async def test_not_found(self, app, db):
        user = await _make_user(db)
        async with _client(app, user) as c:
            missing = str(uuid.uuid4())
            assert (await c.get(f"/api/v1/conversations/{missing}")).status_code == 404

    @pytest.mark.asyncio
    async def test_rename(self, app, db):
        user = await _make_user(db)
        conv = await _make_conversation(db, user)
        async with _client(app, user) as c:
            resp = await c.patch(
                f"/api/v1/conversations/{conv.id}", json={"title": "عنوان جديد"}
            )
            assert resp.status_code == 200
            assert resp.json()["title"] == "عنوان جديد"

    @pytest.mark.asyncio
    async def test_archive_toggle(self, app, db):
        user = await _make_user(db)
        conv = await _make_conversation(db, user)
        async with _client(app, user) as c:
            resp = await c.patch(
                f"/api/v1/conversations/{conv.id}", json={"is_archived": True}
            )
            assert resp.json()["is_archived"] is True
            # Hidden from default list now.
            assert (await c.get("/api/v1/conversations")).json() == []

    @pytest.mark.asyncio
    async def test_update_requires_at_least_one_field(self, app, db):
        user = await _make_user(db)
        conv = await _make_conversation(db, user)
        async with _client(app, user) as c:
            resp = await c.patch(f"/api/v1/conversations/{conv.id}", json={})
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rename_blank_rejected(self, app, db):
        user = await _make_user(db)
        conv = await _make_conversation(db, user)
        async with _client(app, user) as c:
            resp = await c.patch(
                f"/api/v1/conversations/{conv.id}", json={"title": "   "}
            )
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_removes_conversation_and_messages(self, app, db):
        user = await _make_user(db)
        conv = await _make_conversation(db, user)
        async with _client(app, user) as c:
            resp = await c.delete(f"/api/v1/conversations/{conv.id}")
            assert resp.status_code == 200
            assert resp.json() == {
                "deleted": True, "conversation_id": str(conv.id),
            }
        # Verify gone from DB.
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv.id)
        )
        assert result.scalar_one_or_none() is None
        result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        assert result.scalars().all() == []
