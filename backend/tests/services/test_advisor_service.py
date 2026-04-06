"""
Unit tests for app.services.advisor.

Strategy
--------
* Pure helpers (truncate_history, build_system_prompt) are tested directly.
* DB-dependent helpers (build_context, _execute_tool) use mock sessions.
* chat_stream() mocks the anthropic.AsyncAnthropic client.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.advisor import AdvisorChatRequest, AdvisorMessage, UserProfileCompact
from app.schemas.sekem import BagrutGrade
from app.services.advisor import (
    _MAX_HISTORY_CHARS,
    build_context,
    build_system_prompt,
    chat_stream,
    truncate_history,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_BAGRUT = [
    BagrutGrade(subject_code="math", units=5, grade=90),
    BagrutGrade(subject_code="english", units=5, grade=85),
]


def _make_formula(**kw) -> SimpleNamespace:
    defaults = dict(
        program_id=uuid.uuid4(),
        year=2025,
        bagrut_weight=0.5,
        psychometric_weight=0.5,
        threshold_sekem=700.0,
        subject_bonuses=[],
        bagrut_requirements=[],
    )
    return SimpleNamespace(**{**defaults, **kw})


def _make_institution(**kw) -> SimpleNamespace:
    d = dict(id="TAU", name_he="אוניברסיטת תל אביב", name_en="Tel Aviv University")
    return SimpleNamespace(**{**d, **kw})


def _make_program(**kw) -> SimpleNamespace:
    pid = uuid.uuid4()
    d = dict(
        id=pid,
        name_he="מדעי המחשב",
        name_en="Computer Science",
        field="computer_science",
        degree_type="BSc",
        duration_years=3,
        location="תל אביב",
        tuition_annual_ils=12000,
        official_url="https://tau.ac.il/cs",
        is_active=True,
        institution=_make_institution(),
        sekem_formulas=[_make_formula(program_id=pid)],
        syllabi=[],
        career_data=[],
    )
    return SimpleNamespace(**{**d, **kw})


def _mock_db_with_programs(programs: list) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = programs
    session = AsyncMock()
    session.execute.return_value = mock_result
    return session


# ── truncate_history ──────────────────────────────────────────────────────────


class TestTruncateHistory:
    def test_empty_history_returns_empty(self):
        assert truncate_history([]) == []

    def test_short_history_unchanged(self):
        msgs = [
            AdvisorMessage(role="user", content="שלום"),
            AdvisorMessage(role="assistant", content="שלום! אני יועץ."),
        ]
        assert truncate_history(msgs, max_chars=10_000) == msgs

    def test_drops_oldest_when_over_limit(self):
        # Create 3 messages where first two together exceed max_chars
        msgs = [
            AdvisorMessage(role="user",      content="A" * 100),
            AdvisorMessage(role="assistant", content="B" * 100),
            AdvisorMessage(role="user",      content="C" * 50),
        ]
        result = truncate_history(msgs, max_chars=120)
        # First message (100 chars) should be dropped; last two total 150 — still over
        # Keep dropping from front until within budget
        assert all(m in result for m in msgs[1:])  # at most keeps last 2
        total = sum(len(m.content) for m in result)
        assert total <= 120 or len(result) == 1  # at worst keeps only the last one

    def test_returns_most_recent_messages(self):
        msgs = [AdvisorMessage(role="user", content="old " * 1000)]
        msgs += [AdvisorMessage(role="user", content="new")]
        result = truncate_history(msgs, max_chars=10)
        assert result[-1].content == "new"

    def test_exactly_at_limit_unchanged(self):
        msgs = [AdvisorMessage(role="user", content="abc")]
        assert truncate_history(msgs, max_chars=3) == msgs


# ── build_system_prompt ────────────────────────────────────────────────────────


class TestBuildSystemPrompt:
    def test_contains_db_context(self):
        ctx = "ממוצע בגרות: 90.0"
        prompt = build_system_prompt(ctx)
        assert ctx in prompt

    def test_contains_rule_about_fabrication(self):
        prompt = build_system_prompt("")
        assert "לעולם אל תמציא" in prompt

    def test_contains_rule_about_data_year(self):
        prompt = build_system_prompt("")
        assert "שנת הנתון" in prompt

    def test_contains_official_site_rule(self):
        prompt = build_system_prompt("")
        assert "בדוק תמיד באתר הרשמי" in prompt

    def test_contains_hebrew_language_rule(self):
        prompt = build_system_prompt("")
        assert "עברית" in prompt

    def test_mentions_available_tools(self):
        prompt = build_system_prompt("")
        assert "get_program_details" in prompt
        assert "search_programs" in prompt


# ── build_context ──────────────────────────────────────────────────────────────


class TestBuildContext:
    @pytest.mark.asyncio
    async def test_no_grades_returns_no_data_message(self):
        db = AsyncMock()
        result = await build_context([], None, None, db)
        assert "לא הוזן" in result

    @pytest.mark.asyncio
    async def test_eligible_program_appears_in_context(self):
        # Program with threshold 680, user sekem ≈ (90*5*1.25 + 85*5*1.25)/total * 0.5 + 750 * 0.5
        # Let's use threshold 400 so the program is definitely eligible
        pid = uuid.uuid4()
        prog = _make_program(
            id=pid,
            name_he="מדעי המחשב",
            sekem_formulas=[_make_formula(program_id=pid, threshold_sekem=400.0)],
        )
        db = _mock_db_with_programs([prog])
        result = await build_context(_BAGRUT, 750, None, db)
        assert "מדעי המחשב" in result

    @pytest.mark.asyncio
    async def test_includes_psychometric_in_context(self):
        db = _mock_db_with_programs([])
        result = await build_context(_BAGRUT, 750, None, db)
        assert "750" in result

    @pytest.mark.asyncio
    async def test_psychometric_none_shows_not_taken(self):
        db = _mock_db_with_programs([])
        result = await build_context(_BAGRUT, None, None, db)
        assert "לא נבחן" in result

    @pytest.mark.asyncio
    async def test_db_error_handled_gracefully(self):
        db = AsyncMock()
        db.execute.side_effect = Exception("DB offline")
        # build_context catches errors at the caller level; if db fails before
        # the initial query, the exception bubbles up — test that graceful degradation
        # works in chat_stream (which wraps it in try/except)
        # Here we just verify that the error propagates correctly.
        with pytest.raises(Exception, match="DB offline"):
            await build_context(_BAGRUT, 750, None, db)

    @pytest.mark.asyncio
    async def test_includes_bagrut_average(self):
        db = _mock_db_with_programs([])
        result = await build_context(_BAGRUT, None, None, db)
        # weighted avg for 5-unit 90 and 5-unit 85 = (90+85)/2 = 87.5
        assert "87.5" in result


# ── chat_stream ───────────────────────────────────────────────────────────────

def _make_chat_request(**kw) -> AdvisorChatRequest:
    defaults = dict(
        message="מה הסיכויים שלי?",
        user_profile=UserProfileCompact(bagrut_grades=_BAGRUT, psychometric=750),
        current_program_id=None,
        conversation_history=[],
    )
    return AdvisorChatRequest(**{**defaults, **kw})


def _make_final_message(stop_reason: str = "end_turn", text: str = "שלום") -> MagicMock:
    msg = MagicMock()
    msg.stop_reason = stop_reason
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    msg.content = [text_block]
    return msg


async def _aiter(*items):
    """Async generator helper."""
    for item in items:
        yield item


class TestChatStream:
    @pytest.mark.asyncio
    async def test_yields_text_chunks(self):
        db = _mock_db_with_programs([])

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.text_stream = _aiter("שלום", " עולם")
        mock_stream.get_final_message = AsyncMock(
            return_value=_make_final_message(stop_reason="end_turn")
        )

        with patch("app.services.advisor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.stream.return_value = mock_stream

            chunks = []
            async for chunk in chat_stream(_make_chat_request(), db):
                chunks.append(chunk)

        assert any("שלום" in c for c in chunks)
        assert any("[DONE]" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_done_sentinel_always_emitted(self):
        db = _mock_db_with_programs([])

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.text_stream = _aiter("ok")
        mock_stream.get_final_message = AsyncMock(
            return_value=_make_final_message(stop_reason="end_turn")
        )

        with patch("app.services.advisor.anthropic.AsyncAnthropic") as mock_cls:
            mock_cls.return_value.messages.stream.return_value = mock_stream
            chunks = [c async for c in chat_stream(_make_chat_request(), db)]

        assert "data: [DONE]\n\n" in chunks

    @pytest.mark.asyncio
    async def test_tool_use_emits_signals(self):
        """When stop_reason=tool_use, TOOL_USE and TOOL_DONE signals are yielded."""
        db = _mock_db_with_programs([])
        db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)

        # First stream: tool use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "toolu_abc"
        tool_block.name = "get_program_details"
        tool_block.input = {"program_id": str(uuid.uuid4())}
        tool_block.model_dump.return_value = {
            "type": "tool_use",
            "id": "toolu_abc",
            "name": "get_program_details",
            "input": tool_block.input,
        }

        final_tool = MagicMock()
        final_tool.stop_reason = "tool_use"
        final_tool.content = [tool_block]

        # Second stream: normal end
        final_text = _make_final_message(stop_reason="end_turn", text="הנה התשובה")

        stream1 = AsyncMock()
        stream1.__aenter__ = AsyncMock(return_value=stream1)
        stream1.__aexit__ = AsyncMock(return_value=False)
        stream1.text_stream = _aiter()
        stream1.get_final_message = AsyncMock(return_value=final_tool)

        stream2 = AsyncMock()
        stream2.__aenter__ = AsyncMock(return_value=stream2)
        stream2.__aexit__ = AsyncMock(return_value=False)
        stream2.text_stream = _aiter("הנה התשובה")
        stream2.get_final_message = AsyncMock(return_value=final_text)

        # Also mock _tool_get_program_details to avoid real DB call
        with patch("app.services.advisor.anthropic.AsyncAnthropic") as mock_cls, \
             patch("app.services.advisor._tool_get_program_details",
                   AsyncMock(return_value=json.dumps({"name_he": "מדעי המחשב"}))):
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.stream.side_effect = [stream1, stream2]

            chunks = [c async for c in chat_stream(_make_chat_request(), db)]

        assert "data: [TOOL_USE]\n\n" in chunks
        assert "data: [TOOL_DONE]\n\n" in chunks
        assert "data: [DONE]\n\n" in chunks

    @pytest.mark.asyncio
    async def test_context_build_failure_is_handled(self):
        """If build_context fails, chat_stream should still proceed (graceful fallback)."""
        db = AsyncMock()
        db.execute.side_effect = Exception("DB error")

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.text_stream = _aiter("נסה שוב")
        mock_stream.get_final_message = AsyncMock(
            return_value=_make_final_message(stop_reason="end_turn")
        )

        with patch("app.services.advisor.anthropic.AsyncAnthropic") as mock_cls:
            mock_cls.return_value.messages.stream.return_value = mock_stream
            # Should not raise; context error is swallowed in chat_stream
            chunks = [c async for c in chat_stream(_make_chat_request(), db)]

        assert "data: [DONE]\n\n" in chunks

    @pytest.mark.asyncio
    async def test_sse_format_correct(self):
        """Every data chunk starts with 'data: ' and ends with '\n\n'."""
        db = _mock_db_with_programs([])

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.text_stream = _aiter("chunk1", "chunk2")
        mock_stream.get_final_message = AsyncMock(
            return_value=_make_final_message(stop_reason="end_turn")
        )

        with patch("app.services.advisor.anthropic.AsyncAnthropic") as mock_cls:
            mock_cls.return_value.messages.stream.return_value = mock_stream
            chunks = [c async for c in chat_stream(_make_chat_request(), db)]

        for chunk in chunks:
            assert chunk.startswith("data: "), f"Bad SSE format: {chunk!r}"
            assert chunk.endswith("\n\n"), f"Bad SSE terminator: {chunk!r}"
