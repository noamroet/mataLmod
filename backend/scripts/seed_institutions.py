#!/usr/bin/env python3
"""
Seed script — inserts the 7 v1 universities into the institutions table.

Usage (from the /backend directory):
    python scripts/seed_institutions.py

Or via Docker:
    docker compose exec api python scripts/seed_institutions.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure the /backend directory is on sys.path so `app` is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog  # noqa: E402

from app.core.constants import INSTITUTIONS  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.institution import Institution  # noqa: E402

log = structlog.get_logger(__name__)


async def seed() -> None:
    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for inst_id, data in INSTITUTIONS.items():
            existing = await session.get(Institution, inst_id)
            if existing is not None:
                log.info("seed.skip", institution_id=inst_id, reason="already exists")
                skipped += 1
                continue

            institution = Institution(id=inst_id, **data)
            session.add(institution)
            log.info(
                "seed.insert",
                institution_id=inst_id,
                name_he=data["name_he"],
                city=data["city"],
            )
            inserted += 1

        await session.commit()

    log.info("seed.done", inserted=inserted, skipped=skipped)


if __name__ == "__main__":
    asyncio.run(seed())
