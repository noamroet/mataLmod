"""
BaseScraper + ScrapeResult — the contract every scraper must implement.

Every scraper module:
  1. Subclasses BaseScraper and sets INSTITUTION_ID
  2. Implements async scrape() -> list[ScrapeResult]
  3. Returns a ScrapeResult per program (including failed records)

Resilience guarantees built into BaseScraper:
  - Rate limiting: ≥ RATE_LIMIT_SECONDS between requests
  - Retry: up to MAX_RETRIES attempts with 2^n exponential back-off
  - Page structure integrity check: Jaccard similarity vs expected selectors
  - All exceptions caught and surfaced as scrape_ok=False records, never crashes
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar

import httpx
import structlog
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Shared constants (mirrored from backend — avoids cross-package import on PYTHONPATH-free envs)
FIELDS: list[str] = [
    "computer_science", "electrical_engineering", "mechanical_engineering",
    "civil_engineering", "biomedical", "mathematics", "physics_chemistry",
    "medicine", "law", "business", "psychology", "education", "humanities",
    "arts_design", "communication", "agriculture", "other",
]
DEGREE_TYPES: list[str] = ["BA", "BSc", "BEd", "BArch", "BFA", "LLB"]

ANOMALY_THRESHOLD: float = 0.30  # flag if structure similarity drops below (1 - 0.30) = 0.70


# ── ScrapeResult ──────────────────────────────────────────────────────────────

class ScrapeResult(BaseModel):
    """
    One program's worth of scraped data.

    Populate-DB contract:
      institution_id + name_he + degree_type → programs (natural key for upsert)
      sekem_year → sekem_formulas (append, never delete)
      raw_html   → syllabi (replace on each run)
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # ── Program fields ────────────────────────────────────────────────────────
    institution_id: str
    name_he: str
    name_en: str | None = None
    field: str = "other"
    degree_type: str = "BA"
    duration_years: int = 3
    location: str = "תל אביב"
    tuition_annual_ils: int | None = None
    official_url: str

    # ── Sekem formula fields ──────────────────────────────────────────────────
    sekem_year: int = Field(default_factory=lambda: datetime.now(timezone.utc).year)
    bagrut_weight: float = 0.5
    psychometric_weight: float = 0.5
    threshold_sekem: float = 0.0
    # list[{subject_code, units, bonus_points}]
    subject_bonuses: list[dict[str, Any]] = Field(default_factory=list)
    # list[{subject_code, min_units, min_grade, mandatory}]
    bagrut_requirements: list[dict[str, Any]] = Field(default_factory=list)
    formula_source_url: str = ""

    # ── Syllabus ──────────────────────────────────────────────────────────────
    raw_html: str = ""

    # ── Scrape metadata ───────────────────────────────────────────────────────
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    page_checksum: str = ""
    scrape_ok: bool = True
    error_message: str | None = None

    @field_validator("field")
    @classmethod
    def _validate_field(cls, v: str) -> str:
        return v if v in FIELDS else "other"

    @field_validator("degree_type")
    @classmethod
    def _validate_degree_type(cls, v: str) -> str:
        return v if v in DEGREE_TYPES else "BA"

    @field_validator("bagrut_weight", "psychometric_weight")
    @classmethod
    def _validate_weight(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Weight must be in [0, 1], got {v}")
        return v


# ── Structural integrity helpers ──────────────────────────────────────────────

def _structural_features(html: str) -> dict[str, int]:
    """Count occurrences of each unique (tag + first CSS class) pair in the DOM."""
    soup = BeautifulSoup(html, "html.parser")
    counter: dict[str, int] = {}
    for el in soup.find_all(True):
        classes = el.get("class") or [""]
        key = f"{el.name}.{classes[0]}"
        counter[key] = counter.get(key, 0) + 1
    return counter


def page_checksum(html: str) -> str:
    """SHA-256 of the serialised structural-feature count map."""
    features = _structural_features(html)
    return hashlib.sha256(json.dumps(features, sort_keys=True).encode()).hexdigest()


def structural_similarity(html_current: str, html_baseline: str) -> float:
    """
    Jaccard similarity of the structural-feature key sets (0.0 – 1.0).
    Returns 1.0 when baseline is empty (first run — no comparison possible).
    """
    current = set(_structural_features(html_current).keys())
    baseline = set(_structural_features(html_baseline).keys())
    if not baseline:
        return 1.0
    union = current | baseline
    if not union:
        return 1.0
    return len(current & baseline) / len(union)


def check_structure_integrity(html: str, expected_selectors: list[str]) -> float:
    """
    Return the fraction of expected CSS selectors that are present in *html*.

    Used by scrapers to detect when the page layout has changed significantly.
    A value below (1 - ANOMALY_THRESHOLD) should trigger an anomaly flag.
    """
    if not expected_selectors:
        return 1.0
    soup = BeautifulSoup(html, "html.parser")
    found = sum(1 for sel in expected_selectors if soup.select_one(sel))
    return found / len(expected_selectors)


# ── BaseScraper ───────────────────────────────────────────────────────────────

class BaseScraper(ABC):
    INSTITUTION_ID: ClassVar[str]
    RATE_LIMIT_SECONDS: ClassVar[float] = 2.0
    MAX_RETRIES: ClassVar[int] = 3

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "MaTaLmod-Scraper/1.0 (+https://mataLmod.co.il)"},
            follow_redirects=True,
        )
        self._last_request_ts: float = 0.0
        self._log = structlog.get_logger(self.__class__.__name__)

    async def __aenter__(self) -> "BaseScraper":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    # ── Rate limiting ─────────────────────────────────────────────────────────

    async def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.RATE_LIMIT_SECONDS:
            await asyncio.sleep(self.RATE_LIMIT_SECONDS - elapsed)
        self._last_request_ts = time.monotonic()

    # ── Static fetch (httpx) ──────────────────────────────────────────────────

    async def fetch_static(self, url: str) -> str:
        """HTTP GET with rate limiting and exponential-backoff retry."""
        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                await self._rate_limit()
                resp = await self._http.get(url)
                resp.raise_for_status()
                return resp.text
            except Exception as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES:
                    delay = 2.0 ** attempt
                    self._log.warning(
                        "fetch_static.retry",
                        url=url, attempt=attempt, delay=delay, error=str(exc),
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    # ── Dynamic fetch (Playwright) ────────────────────────────────────────────

    async def fetch_dynamic(self, url: str) -> str:
        """Navigate with Playwright (headless Chromium), wait for JS, return HTML."""
        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                await self._rate_limit()
                async with async_playwright() as pw:
                    browser = await pw.chromium.launch(headless=True)
                    try:
                        ctx = await browser.new_context(
                            user_agent=(
                                "Mozilla/5.0 (X11; Linux x86_64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0.0.0 Safari/537.36"
                            ),
                            locale="he-IL",
                        )
                        page = await ctx.new_page()
                        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                        # Give JS frameworks extra time to render after DOMContentLoaded
                        await page.wait_for_timeout(3_000)
                        return await page.content()
                    finally:
                        await browser.close()
            except Exception as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES:
                    delay = 2.0 ** attempt
                    self._log.warning(
                        "fetch_dynamic.retry",
                        url=url, attempt=attempt, delay=delay, error=str(exc),
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> list[ScrapeResult]:
        """
        Scrape this institution.

        Must catch all per-program exceptions and include a
        ScrapeResult(scrape_ok=False, error_message=...) for each failure.
        Never raises — return an empty list on total failure.
        """
