"""
AI Advisor service.

Orchestrates claude-sonnet-4-6 for personalised Israeli degree-program guidance.

Key responsibilities:
  1. Build a DB context of the user's top eligible + borderline programs.
  2. Inject context into a Hebrew-first system prompt.
  3. Truncate conversation history to stay under ~4 000 input tokens.
  4. Stream the model response, handling up to _MAX_TOOL_TURNS rounds of tool use.

SSE output tokens:
  data: <text chunk>          — partial text delta
  data: [TOOL_USE]            — Claude is calling a tool
  data: [TOOL_DONE]           — tool result returned to Claude
  data: [DONE]                — stream finished

Rate limiting and the 20-turn cap are enforced by the router.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

import anthropic
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import settings
from app.models.institution import Institution
from app.models.program import Program
from app.models.sekem_formula import SekemFormula
from app.schemas.advisor import AdvisorChatRequest, AdvisorMessage
from app.schemas.sekem import BagrutGrade, SekemFormula as SekemFormulaSchema, SubjectBonus, UserProfile
from app.services.sekem import calculate_sekem, weighted_bagrut_average

log = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_MODEL = "claude-sonnet-4-6"

# Rough conversion for truncation: 3 chars ≈ 1 token (Hebrew/English mix)
_CHARS_PER_TOKEN: int = 3
_MAX_HISTORY_CHARS: int = 4_000 * _CHARS_PER_TOKEN  # ≈ 4 000 token budget for history

# Cap for context queries
_CONTEXT_DB_LIMIT: int = 30     # programs fetched from DB for context
_CONTEXT_ELIGIBLE: int = 5      # eligible programs shown in system prompt
_CONTEXT_BORDERLINE: int = 3    # borderline programs shown

# Max tool-use rounds per request (prevents runaway loops)
_MAX_TOOL_TURNS: int = 2

# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOLS: list[dict] = [
    {
        "name": "get_program_details",
        "description": (
            "Retrieve full details for a specific academic program: "
            "name, institution, Sekem threshold (with data year), syllabus summary, "
            "career job titles, and salary range."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "program_id": {
                    "type": "string",
                    "description": "UUID of the program.",
                }
            },
            "required": ["program_id"],
        },
    },
    {
        "name": "search_programs",
        "description": (
            "Search for academic programs by keyword, field code, or institution. "
            "Returns up to 10 matching programs with names and Sekem thresholds."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text search across program name (Hebrew or English).",
                },
                "field": {
                    "type": "string",
                    "description": "Field code filter (e.g. 'computer_science', 'law').",
                },
                "institution_id": {
                    "type": "string",
                    "description": "Institution ID filter (e.g. 'TAU', 'HUJI', 'TECHNION').",
                },
            },
            "required": [],
        },
    },
]

# ── History truncation ────────────────────────────────────────────────────────


def truncate_history(
    history: list[AdvisorMessage],
    max_chars: int = _MAX_HISTORY_CHARS,
) -> list[AdvisorMessage]:
    """
    Drop the OLDEST messages until the total character count fits within max_chars.
    Always preserves the most recent messages.
    """
    total = sum(len(m.content) for m in history)
    result = list(history)
    while total > max_chars and result:
        removed = result.pop(0)
        total -= len(removed.content)
    return result


# ── DB context builder ────────────────────────────────────────────────────────


def _formula_to_schema(sf: SekemFormula, program_id: uuid.UUID) -> SekemFormulaSchema:
    bonuses = [
        SubjectBonus(
            subject_code=b["subject_code"],
            units=b["units"],
            bonus_points=b["bonus_points"],
        )
        for b in (sf.subject_bonuses or [])
    ]
    return SekemFormulaSchema(
        program_id=program_id,
        bagrut_weight=sf.bagrut_weight,
        psychometric_weight=sf.psychometric_weight,
        threshold_sekem=sf.threshold_sekem,
        subject_bonuses=bonuses,
    )


async def build_context(
    bagrut_grades: list[BagrutGrade],
    psychometric: int | None,
    current_program_id: uuid.UUID | None,
    db: AsyncSession,
) -> str:
    """
    Build a concise Hebrew-language context string for the system prompt.

    Fetches programs from the DB, calculates sekem for the user profile, and
    returns a formatted summary of top eligible + borderline programs.
    """
    lines: list[str] = []

    # ── User profile summary ─────────────────────────────────────────────────
    if bagrut_grades:
        avg = weighted_bagrut_average(bagrut_grades)
        lines.append(f"ממוצע בגרות משוקלל: {avg:.1f}")
    else:
        lines.append("ממוצע בגרות: לא הוזן")

    lines.append(
        f"ציון פסיכומטרי: {psychometric}" if psychometric else "פסיכומטרי: לא נבחן"
    )

    if not bagrut_grades:
        return "\n".join(lines)

    # ── Fetch programs with latest sekem formula ─────────────────────────────
    stmt = (
        select(Program)
        .options(
            joinedload(Program.institution),
            selectinload(Program.sekem_formulas),
        )
        .where(Program.is_active.is_(True))
        .order_by(Program.name_he)
        .limit(_CONTEXT_DB_LIMIT)
    )
    result = await db.execute(stmt)
    programs: list[Program] = list(result.scalars().unique().all())

    profile = UserProfile(bagrut_grades=bagrut_grades, psychometric=psychometric)

    scored: list[tuple[Program, object]] = []
    for prog in programs:
        if not prog.sekem_formulas:
            continue
        latest_formula = max(prog.sekem_formulas, key=lambda f: f.year)
        formula_schema = _formula_to_schema(latest_formula, prog.id)
        sekem_result = calculate_sekem(profile, formula_schema)
        scored.append((prog, sekem_result, latest_formula.year))  # type: ignore[arg-type]

    # Sort: eligible → borderline → below, then by margin descending
    def _sort_key(item: tuple) -> tuple[int, float]:
        _, r, _ = item
        if r.eligible:
            return (0, -r.margin)
        if r.borderline:
            return (1, -r.margin)
        return (2, -r.margin)

    scored.sort(key=_sort_key)

    # ── Eligible programs ────────────────────────────────────────────────────
    eligible = [(p, r, y) for p, r, y in scored if r.eligible][:_CONTEXT_ELIGIBLE]
    if eligible:
        lines.append("\nתוכניות שהמשתמש זכאי אליהן (הסקם שלו עומד בדרישות):")
        for prog, r, year in eligible:
            lines.append(
                f"  • {prog.name_he} — {prog.institution.name_he}"
                f" | סף {year}: {r.threshold:.0f}"
                f" | הסקם שלך: {r.sekem:.0f} (+{r.margin:.0f})"
                " | בדוק תמיד באתר הרשמי"
            )

    # ── Borderline programs ──────────────────────────────────────────────────
    borderline = [(p, r, y) for p, r, y in scored if r.borderline][:_CONTEXT_BORDERLINE]
    if borderline:
        lines.append("\nתוכניות גבוליות (הסקם קרוב לסף — פחות מ-30 נקודות):")
        for prog, r, year in borderline:
            lines.append(
                f"  • {prog.name_he} — {prog.institution.name_he}"
                f" | סף {year}: {r.threshold:.0f}"
                f" | הסקם שלך: {r.sekem:.0f} ({r.margin:.0f})"
                " | בדוק תמיד באתר הרשמי"
            )

    # ── Current program context ──────────────────────────────────────────────
    if current_program_id:
        current = next(
            (p for p, _, _ in scored if p.id == current_program_id), None
        )
        if current:
            cur_result = next(r for p, r, _ in scored if p.id == current_program_id)
            lines.append(
                f"\nהתוכנית שהמשתמש צופה בה כרגע: {current.name_he}"
                f" — {current.institution.name_he}"
                f" | הסקם שלו: {cur_result.sekem:.0f}"
                f" | סף: {cur_result.threshold:.0f}"
            )

    return "\n".join(lines)


# ── System prompt ─────────────────────────────────────────────────────────────


def build_system_prompt(db_context: str) -> str:
    return f"""אתה יועץ אקדמי מומחה של "מה תלמד?" — פלטפורמת גילוי תארים לישראלים לאחר שירות צבאי.
תפקידך לעזור לצעירים ישראלים (גיל 21–24) לבחור תואר אקדמי — לפי הנתונים שלהם, העדפותיהם, ואפשרויות הקריירה.

== נתוני המשתמש מהמסד ==
{db_context}

== כללים שאין לחרוג מהם ==
1. לעולם אל תמציא נתונים. ציין רק סף כניסה ושמות קורסים שמופיעים ב-DB_CONTEXT לעיל.
2. בכל אזכור של סף סקם — ציין את שנת הנתון: "סף [שנה]: [מספר]".
3. לאחר כל אזכור של סף קבלה — הוסף: "בדוק תמיד באתר הרשמי".
4. השב בעברית אלא אם המשתמש כותב באנגלית — במקרה כזה השב באנגלית.
5. שמור על תשובות ממוקדות ופרקטיות — הזמן של המשתמש יקר.
6. אם אינך יודע פרט ספציפי — אמור זאת במפורש ואל תנחש.

כלים זמינים לך: get_program_details (מידע מלא על תוכנית), search_programs (חיפוש תוכניות).
השתמש בהם כשהמשתמש שואל שאלות ספציפיות על תוכניות שאינן בהקשר לעיל."""


# ── Tool execution ────────────────────────────────────────────────────────────


async def _tool_get_program_details(
    program_id_str: str,
    db: AsyncSession,
) -> str:
    try:
        program_id = uuid.UUID(program_id_str)
    except ValueError:
        return json.dumps({"error": "invalid program_id"})

    stmt = (
        select(Program)
        .options(
            joinedload(Program.institution),
            selectinload(Program.sekem_formulas),
            selectinload(Program.syllabi),
            selectinload(Program.career_data),
        )
        .where(Program.id == program_id)
    )
    result = await db.execute(stmt)
    prog = result.scalar_one_or_none()

    if prog is None:
        return json.dumps({"error": "program not found"})

    latest_formula = max(prog.sekem_formulas, key=lambda f: f.year, default=None)
    latest_career  = max(prog.career_data, key=lambda c: c.updated_at, default=None)
    latest_syllabus = max(prog.syllabi, key=lambda s: s.scraped_at, default=None)

    data: dict = {
        "id": str(prog.id),
        "name_he": prog.name_he,
        "name_en": prog.name_en,
        "institution": prog.institution.name_he,
        "field": prog.field,
        "degree_type": prog.degree_type,
        "duration_years": prog.duration_years,
        "location": prog.location,
        "tuition_annual_ils": prog.tuition_annual_ils,
        "official_url": prog.official_url,
    }

    if latest_formula:
        data["sekem_formula"] = {
            "year": latest_formula.year,
            "threshold_sekem": latest_formula.threshold_sekem,
            "bagrut_weight": latest_formula.bagrut_weight,
            "psychometric_weight": latest_formula.psychometric_weight,
        }
        data["sekem_note"] = "בדוק תמיד באתר הרשמי"

    if latest_syllabus:
        data["syllabus"] = {
            "year_1": latest_syllabus.year_1_summary_he,
            "year_2": latest_syllabus.year_2_summary_he,
            "year_3": latest_syllabus.year_3_summary_he,
            "core_courses": latest_syllabus.core_courses,
            "elective_tracks": latest_syllabus.elective_tracks,
        }

    if latest_career:
        data["career"] = {
            "job_titles": latest_career.job_titles,
            "avg_salary_min_ils": latest_career.avg_salary_min_ils,
            "avg_salary_max_ils": latest_career.avg_salary_max_ils,
            "demand_trend": latest_career.demand_trend.value
                if hasattr(latest_career.demand_trend, "value")
                else str(latest_career.demand_trend),
        }

    return json.dumps(data, ensure_ascii=False)


async def _tool_search_programs(
    query: str | None,
    field: str | None,
    institution_id: str | None,
    db: AsyncSession,
) -> str:
    stmt = (
        select(Program)
        .options(
            joinedload(Program.institution),
            selectinload(Program.sekem_formulas),
        )
        .where(Program.is_active.is_(True))
    )

    if field:
        stmt = stmt.where(Program.field == field)
    if institution_id:
        stmt = stmt.where(Program.institution_id == institution_id)
    if query:
        q = f"%{query}%"
        stmt = stmt.where(
            Program.name_he.ilike(q) | Program.name_en.ilike(q)
        )

    stmt = stmt.order_by(Program.name_he).limit(10)
    result = await db.execute(stmt)
    programs: list[Program] = list(result.scalars().unique().all())

    items = []
    for prog in programs:
        latest = max(prog.sekem_formulas, key=lambda f: f.year, default=None)
        items.append(
            {
                "id": str(prog.id),
                "name_he": prog.name_he,
                "institution": prog.institution.name_he,
                "field": prog.field,
                "threshold_sekem": latest.threshold_sekem if latest else None,
                "threshold_year": latest.year if latest else None,
                "sekem_note": "בדוק תמיד באתר הרשמי" if latest else None,
            }
        )

    return json.dumps({"programs": items, "count": len(items)}, ensure_ascii=False)


async def _execute_tool(
    tool_name: str,
    tool_input: dict,
    db: AsyncSession,
) -> str:
    log.info("advisor.tool_call", tool=tool_name, input=tool_input)

    if tool_name == "get_program_details":
        return await _tool_get_program_details(
            str(tool_input.get("program_id", "")), db
        )
    if tool_name == "search_programs":
        return await _tool_search_programs(
            query=tool_input.get("query"),
            field=tool_input.get("field"),
            institution_id=tool_input.get("institution_id"),
            db=db,
        )

    log.warning("advisor.unknown_tool", tool=tool_name)
    return json.dumps({"error": f"unknown tool: {tool_name}"})


# ── Main streaming generator ──────────────────────────────────────────────────


async def chat_stream(
    request: AdvisorChatRequest,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE data lines for the advisor endpoint.

    Each yielded string is already formatted as ``data: ...\n\n``.
    The final event is always ``data: [DONE]\n\n``.
    """

    # 1. Build DB context (fetches programs, computes sekem)
    try:
        db_context = await build_context(
            bagrut_grades=request.user_profile.bagrut_grades,
            psychometric=request.user_profile.psychometric,
            current_program_id=request.current_program_id,
            db=db,
        )
    except Exception:
        log.exception("advisor.context_build_failed")
        db_context = "שגיאה בטעינת נתוני ההקשר."

    # 2. System prompt
    system_prompt = build_system_prompt(db_context)

    # 3. Truncated history → messages list
    truncated = truncate_history(request.conversation_history)
    messages: list[dict] = [
        {"role": m.role, "content": m.content} for m in truncated
    ]
    messages.append({"role": "user", "content": request.message})

    # 4. Stream (with up to _MAX_TOOL_TURNS rounds of tool use)
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    for turn in range(_MAX_TOOL_TURNS + 1):
        async with client.messages.stream(
            model=_MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=_TOOLS,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                # Replace newlines to keep each SSE event on one logical line
                safe = text.replace("\n", " ")
                yield f"data: {safe}\n\n"

            final = await stream.get_final_message()

        if final.stop_reason != "tool_use":
            break

        if turn >= _MAX_TOOL_TURNS:
            log.warning("advisor.tool_turn_limit_reached")
            break

        # Execute all requested tools
        yield "data: [TOOL_USE]\n\n"

        tool_results = []
        for block in final.content:
            if block.type == "tool_use":
                result_str = await _execute_tool(
                    tool_name=block.name,
                    tool_input=block.input,
                    db=db,
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                )

        yield "data: [TOOL_DONE]\n\n"

        # Append assistant turn + tool results for next iteration
        assistant_content = [
            b.model_dump() if hasattr(b, "model_dump") else dict(b)
            for b in final.content
        ]
        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

    log.info(
        "advisor.stream_complete",
        message_preview=request.message[:60],
        turns=turn + 1,
    )
    yield "data: [DONE]\n\n"
