"""
/api/v1/accounts — authenticated user account endpoints.

POST /api/v1/accounts/me/roadmap-progress
    Batch-upsert roadmap to-do progress items flushed from localStorage on login.
    Auth: Bearer JWT — sub claim must be a valid user UUID.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.roadmap_progress import RoadmapProgress
from app.schemas.accounts import RoadmapProgressBatch, RoadmapProgressResponse

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
)

_JWT_ALGORITHM = "HS256"


# ── Auth dependency ───────────────────────────────────────────────────────────

async def _get_current_user_id(
    authorization: str | None = Header(default=None),
) -> uuid.UUID:
    """
    Extract the authenticated user's UUID from a Bearer JWT.

    The JWT ``sub`` claim must be a valid UUID that exists in the users table.
    Returns 401 if the token is missing, malformed, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[_JWT_ALGORITHM]
        )
        sub: str | None = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token missing sub claim")
        return uuid.UUID(sub)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/me/roadmap-progress",
    response_model=RoadmapProgressResponse,
    summary="Sync roadmap to-do progress",
    description=(
        "Batch-upserts roadmap to-do progress items from the client's localStorage. "
        "Called once after the user logs in. "
        "Items are upserted (insert or update) on the unique "
        "(user_id, program_id, item_index) key. "
        "Requires a valid Bearer JWT."
    ),
)
async def sync_roadmap_progress(
    body: RoadmapProgressBatch,
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RoadmapProgressResponse:
    """
    PostgreSQL upsert via ON CONFLICT DO UPDATE.

    Each item in the batch is inserted or updated if a row with the same
    (user_id, program_id, item_index) already exists.
    """
    rows = [
        {
            "id":         uuid.uuid4(),
            "user_id":    user_id,
            "program_id": item.program_id,
            "item_index": item.item_index,
            "checked":    item.checked,
            "checked_at": item.checked_at,
            "updated_at": datetime.utcnow(),
        }
        for item in body.items
    ]

    stmt = pg_insert(RoadmapProgress).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_roadmap_progress_user_program_item",
        set_={
            "checked":    stmt.excluded.checked,
            "checked_at": stmt.excluded.checked_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await db.execute(stmt)
    await db.commit()

    log.info(
        "accounts.roadmap_progress.synced",
        user_id=str(user_id),
        count=len(rows),
    )
    return RoadmapProgressResponse(synced=len(rows))
