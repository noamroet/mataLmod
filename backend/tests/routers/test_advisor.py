"""
Integration tests for POST /api/v1/advisor/chat.

Strategy
--------
* mock_session and disable_cache fixtures are inherited from conftest.py (autouse).
* app.services.advisor.chat_stream is patched so no Anthropic API call is made.
* Rate-limit store is reset between tests via monkeypatch.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from unittest.mock import AsyncMock, patch

import pytest

import app.routers.advisor as advisor_router
from app.schemas.sekem import BagrutGrade

_URL = "/api/v1/advisor/chat"

# ── Shared request bodies ─────────────────────────────────────────────────────

_VALID_REQUEST = {
    "message": "מה הסיכויים שלי ללמוד מדעי המחשב?",
    "user_profile": {
        "bagrut_grades": [
            {"subject_code": "math",    "units": 5, "grade": 90},
            {"subject_code": "english", "units": 5, "grade": 85},
        ],
        "psychometric": 750,
    },
    "current_program_id": None,
    "conversation_history": [],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _simple_stream(*tokens: str):
    """Async generator that yields SSE lines for the given tokens."""
    for token in tokens:
        yield f"data: {token}\n\n"
    yield "data: [DONE]\n\n"


# ── Rate limit tests ──────────────────────────────────────────────────────────

class TestRateLimit:
    @pytest.fixture(autouse=True)
    def reset_rate_store(self, monkeypatch):
        """Reset the in-memory rate-limit store before each test."""
        monkeypatch.setattr(
            advisor_router, "_rate_store", defaultdict(deque)
        )

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, client):
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            response = await client.post(_URL, json=_VALID_REQUEST)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(self, client, monkeypatch):
        """Saturate the window, then verify 429 is returned."""
        monkeypatch.setattr(advisor_router, "_RATE_MAX_REQUESTS", 2)

        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            for _ in range(2):
                await client.post(_URL, json=_VALID_REQUEST)

        # Third request should be rate-limited
        response = await client.post(_URL, json=_VALID_REQUEST)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_message_is_hebrew(self, client, monkeypatch):
        monkeypatch.setattr(advisor_router, "_RATE_MAX_REQUESTS", 0)
        response = await client.post(_URL, json=_VALID_REQUEST)
        assert response.status_code == 429
        body = response.json()
        assert "detail" in body


# ── Turn cap tests ────────────────────────────────────────────────────────────

class TestTurnCap:
    @pytest.fixture(autouse=True)
    def reset_rate_store(self, monkeypatch):
        monkeypatch.setattr(advisor_router, "_rate_store", defaultdict(deque))

    @pytest.mark.asyncio
    async def test_exactly_at_turn_limit_is_allowed(self, client):
        # 20 turns = 40 messages
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(40)
        ]
        payload = {**_VALID_REQUEST, "conversation_history": history}
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            response = await client.post(_URL, json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_over_turn_limit_returns_400(self, client):
        # 41 messages > 20 turns * 2
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(41)
        ]
        payload = {**_VALID_REQUEST, "conversation_history": history}
        response = await client.post(_URL, json=payload)
        assert response.status_code == 400


# ── Streaming response tests ──────────────────────────────────────────────────

class TestAdvisorChat:
    @pytest.fixture(autouse=True)
    def reset_rate_store(self, monkeypatch):
        monkeypatch.setattr(advisor_router, "_rate_store", defaultdict(deque))

    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("שלום"),
        ):
            response = await client.post(_URL, json=_VALID_REQUEST)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_content_type_is_event_stream(self, client):
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            response = await client.post(_URL, json=_VALID_REQUEST)
        assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_streaming_body_contains_sse_data(self, client):
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("שלום", " עולם"),
        ):
            response = await client.post(_URL, json=_VALID_REQUEST)
        assert b"data: " in response.content

    @pytest.mark.asyncio
    async def test_streaming_body_contains_done_sentinel(self, client):
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("some text"),
        ):
            response = await client.post(_URL, json=_VALID_REQUEST)
        assert b"[DONE]" in response.content

    @pytest.mark.asyncio
    async def test_accepts_request_without_profile(self, client):
        payload = {
            "message": "שלום, תעזור לי",
            "user_profile": {"bagrut_grades": [], "psychometric": None},
            "current_program_id": None,
            "conversation_history": [],
        }
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            response = await client.post(_URL, json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_accepts_current_program_id(self, client):
        payload = {
            **_VALID_REQUEST,
            "current_program_id": str(uuid.uuid4()),
        }
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            response = await client.post(_URL, json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_message_returns_422(self, client):
        payload = {**_VALID_REQUEST, "message": ""}
        response = await client.post(_URL, json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_message_too_long_returns_422(self, client):
        payload = {**_VALID_REQUEST, "message": "x" * 2001}
        response = await client.post(_URL, json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_psychometric_returns_422(self, client):
        payload = {
            **_VALID_REQUEST,
            "user_profile": {"bagrut_grades": [], "psychometric": 900},  # > 800
        }
        response = await client.post(_URL, json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_with_conversation_history(self, client):
        payload = {
            **_VALID_REQUEST,
            "conversation_history": [
                {"role": "user",      "content": "שלום"},
                {"role": "assistant", "content": "שלום! כיצד אוכל לעזור?"},
            ],
        }
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("follow-up response"),
        ):
            response = await client.post(_URL, json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cache_control_header_set(self, client):
        with patch(
            "app.routers.advisor.chat_stream",
            return_value=_simple_stream("ok"),
        ):
            response = await client.post(_URL, json=_VALID_REQUEST)
        assert response.headers.get("cache-control") == "no-cache"
