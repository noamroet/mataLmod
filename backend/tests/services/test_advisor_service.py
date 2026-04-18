"""
Unit tests for app.services.advisor.

Strategy
--------
* Pure helpers (build_system_prompt, build_context) are tested directly.
* DB-dependent helpers use mock sessions.
* chat_stream() mocks the anthropic.AsyncAnthropic client.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.advisor import AdvisorChatRequest, UserProfileCompact, WizardStep
from app.schemas.sekem import BagrutGrade
from app.services.advisor import (
    build_context,
    build_system_prompt,
    chat_stream,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_BAGRUT = [
    BagrutGrade(subject_code="math", units=5, grade=90),
    BagrutGrade(subject_code="english", units=5, grade=85),
]

_WIZARD_PATH = [
    WizardStep(question="היי! על מה הכי חשוב לך שנדבר?", answer="איך אני מגיע לסף הקבלה?")
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

    def test_wizard_path_injected_when_provided(self):
        prompt = build_system_prompt("ctx", wizard_path_text="שאלה: X\nתשובה: Y")
        assert "WIZARD_PATH" in prompt
        assert "שאלה: X" in prompt

    def test_no_wizard_section_when_empty(self):
        prompt = build_system_prompt("ctx", wizard_path_text="")
        assert "WIZARD_PATH" not in prompt


# ── build_context ──────────────────────────────────────────────────────────────


class TestBuildContext:
    @pytest.mark.asyncio
    async def test_no_grades_returns_no_data_message(self):
        db = AsyncMock()
        result = await build_context([], None, None, db)
        assert "לא הוזן" in result

    @pytest.mark.asyncio
    async def test_eligible_program_appears_in_context(self):
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
    async def test_db_error_propagates(self):
        db = AsyncMock()
        db.execute.side_effect = Exception("DB offline")
        with pytest.raises(Exception, match="DB offline"):
            await build_context(_BAGRUT, 750, None, db)

    @pytest.mark.asyncio
    async def test_includes_bagrut_average(self):
        db = _mock_db_with_programs([])
        result = await build_context(_BAGRUT, None, None, db)
        assert "87.5" in result


# ── chat_stream ───────────────────────────────────────────────────────────────


def _make_chat_request(**kw) -> AdvisorChatRequest:
    defaults = dict(
        wizard_path=_WIZARD_PATH,
        user_profile=UserProfileCompact(bagrut_grades=_BAGRUT, psychometric=750),
        current_program_id=None,
        target_node_id="gap",
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
    async def test_wizard_path_included_in_system_prompt(self):
        """The wizard path should appear in the system prompt sent to Claude."""
        db = _mock_db_with_programs([])

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.text_stream = _aiter("ok")
        mock_stream.get_final_message = AsyncMock(
            return_value=_make_final_message(stop_reason="end_turn")
        )

        captured_calls = []

        with patch("app.services.advisor.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            def capture_stream(**kwargs):
                captured_calls.append(kwargs)
                return mock_stream
            mock_client.messages.stream.side_effect = capture_stream

            chunks = [c async for c in chat_stream(_make_chat_request(), db)]

        assert captured_calls, "No API call was made"
        system_prompt = captured_calls[0]["system"]
        assert "איך אני מגיע לסף הקבלה?" in system_prompt

    @pytest.mark.asyncio
    async def test_tool_use_emits_signals(self):
        db = _mock_db_with_programs([])
        db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "toolu_abc"
        tool_block.name = "get_program_details"
        tool_block.input = {"program_id": str(uuid.uuid4())}
        tool_block.model_dump.return_value = {
            "type": "tool_use", "id": "toolu_abc",
            "name": "get_program_details", "input": tool_block.input,
        }

        final_tool = MagicMock()
        final_tool.stop_reason = "tool_use"
        final_tool.content = [tool_block]
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
            chunks = [c async for c in chat_stream(_make_chat_request(), db)]

        assert "data: [DONE]\n\n" in chunks

    @pytest.mark.asyncio
    async def test_sse_format_correct(self):
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
