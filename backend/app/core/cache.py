"""
Redis-backed JSON cache.

All public functions are fire-and-forget safe: on Redis error they log a
warning and return None / no-op, so the application continues serving
from the database.

Usage in routers (import the module, not individual names):
    from app.core import cache
    cached = await cache.cache_get(key)
    await cache.cache_set(key, value, ttl=cache.PROGRAMS_TTL)

Invalidation (called by scraper pipeline after promoting new data):
    await cache.invalidate_programs()
    await cache.invalidate_institutions()
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

log = logging.getLogger(__name__)

# TTL constants (seconds)
PROGRAMS_TTL: int = 3600       # 1 hour
INSTITUTIONS_TTL: int = 3600   # 1 hour

# Cache key prefixes
_PROGRAMS_PREFIX = "programs:"
_INSTITUTIONS_PREFIX = "institutions:"

_redis: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis:
    """Return (and lazily create) the shared async Redis client."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis


async def cache_get(key: str) -> Any | None:
    """Return the cached value for *key*, or ``None`` on miss / error."""
    try:
        raw = await _get_client().get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("cache_get failed key=%s err=%s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Serialise *value* as JSON and store it with the given *ttl* in seconds."""
    try:
        await _get_client().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:  # noqa: BLE001
        log.warning("cache_set failed key=%s err=%s", key, exc)


async def cache_delete(key: str) -> None:
    """Delete a single cache entry."""
    try:
        await _get_client().delete(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("cache_delete failed key=%s err=%s", key, exc)


async def _scan_delete(pattern: str) -> None:
    """SCAN + DELETE all keys matching *pattern* (avoids blocking KEYS command)."""
    try:
        client = _get_client()
        async for key in client.scan_iter(match=pattern, count=100):
            await client.delete(key)
    except Exception as exc:  # noqa: BLE001
        log.warning("cache scan_delete failed pattern=%s err=%s", pattern, exc)


# ── Invalidation helpers (called by scraper/pipeline/publisher.py) ────────────

async def invalidate_programs() -> None:
    """Bust all cached program list responses after a scraper run."""
    await _scan_delete(f"{_PROGRAMS_PREFIX}*")


async def invalidate_institutions() -> None:
    """Bust the cached institutions list."""
    await _scan_delete(f"{_INSTITUTIONS_PREFIX}*")
