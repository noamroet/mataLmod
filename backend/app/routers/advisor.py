"""
POST /api/v1/advisor/chat — AI Advisor SSE endpoint.

Rate limit: 10 requests per minute per IP (in-memory sliding window).
Turn cap:   20 conversation turns (40 messages) per request.
Response:   text/event-stream (Server-Sent Events).

SSE event format:
  data: <text chunk>    — partial response text
  data: [TOOL_USE]      — model is calling a tool
  data: [TOOL_DONE]     — tool result returned to model
  data: [DONE]          — stream finished
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.advisor import AdvisorChatRequest
from app.services.advisor import chat_stream

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/advisor",
    tags=["advisor"],
)

# ── Rate limiting (in-memory sliding window) ──────────────────────────────────

_RATE_WINDOW_SECONDS: int = 60
_RATE_MAX_REQUESTS:   int = 10

# ip → deque of request timestamps (float, monotonic)
_rate_store: dict[str, deque[float]] = defaultdict(deque)

# Maximum conversation turns allowed per request
_MAX_TURNS: int = 20


def _check_rate_limit(ip: str) -> bool:
    """
    Sliding-window rate check for the given IP.

    Returns True if the request is allowed, False if the limit is exceeded.
    Side-effect: records this request's timestamp when allowed.
    """
    now = time.monotonic()
    window_start = now - _RATE_WINDOW_SECONDS
    dq = _rate_store[ip]

    # Evict timestamps that are older than the window
    while dq and dq[0] < window_start:
        dq.popleft()

    if len(dq) >= _RATE_MAX_REQUESTS:
        return False

    dq.append(now)
    return True


# ── SSE adapter ───────────────────────────────────────────────────────────────


async def _encode(gen: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
    """Encode string chunks to UTF-8 bytes for StreamingResponse."""
    async for chunk in gen:
        yield chunk.encode("utf-8")


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.post(
    "/chat",
    summary="AI Advisor chat (SSE streaming)",
    description=(
        "Streams a personalised advisory response in Hebrew (or English if the "
        "user writes in English). Responses are streamed as Server-Sent Events. "
        "Rate-limited to 10 requests per minute per IP."
    ),
    response_class=StreamingResponse,
)
async def advisor_chat(
    request_body: AdvisorChatRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    # ── Rate limit ────────────────────────────────────────────────────────────
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    if not _check_rate_limit(client_ip):
        log.warning("advisor.rate_limited", ip=client_ip)
        raise HTTPException(
            status_code=429,
            detail="יותר מדי בקשות. אנא המתן דקה ונסה שוב.",
        )

    # ── Turn cap ──────────────────────────────────────────────────────────────
    if len(request_body.conversation_history) > _MAX_TURNS * 2:
        log.info("advisor.turn_cap_exceeded", ip=client_ip)
        raise HTTPException(
            status_code=400,
            detail=f"שיחה ארוכה מדי. מותר עד {_MAX_TURNS} תורות בשיחה אחת.",
        )

    log.info(
        "advisor.chat_start",
        ip=client_ip,
        history_len=len(request_body.conversation_history),
        has_program=request_body.current_program_id is not None,
    )

    generator = chat_stream(request_body, db)

    return StreamingResponse(
        _encode(generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
            "Connection": "keep-alive",
        },
    )
