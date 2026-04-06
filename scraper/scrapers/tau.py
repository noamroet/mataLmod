"""
TauScraper — Tel Aviv University scraper.

Site structure (as of 2026):
  Faculty pages : https://go.tau.ac.il/he/{faculty_slug}
  Detail pages  : https://go.tau.ac.il/node/{id}

Each faculty page lists programs as div.program cards.
Each detail page contains the sekem threshold in span.acceptance#acceptanceThreshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import (
    ANOMALY_THRESHOLD,
    BaseScraper,
    ScrapeResult,
    check_structure_integrity,
    page_checksum,
)

# ── Constants ─────────────────────────────────────────────────────────────────

INSTITUTION_ID = "TAU"
BASE_URL = "https://go.tau.ac.il"
LOCATION_HE = "תל אביב"

# All undergraduate faculty pages (stable nav links from /he/undergraduate)
FACULTY_PATHS: list[tuple[str, str]] = [
    ("/he/AI",              "מדעי המחשב"),
    ("/he/exact",           "מתמטיקה ומדעים מדויקים"),
    ("/he/engineering",     "הנדסה"),
    ("/he/life",            "מדעי החיים"),
    ("/he/neuroscience",    "מדעי המוח"),
    ("/he/med",             "רפואה ובריאות"),
    ("/he/law",             "משפטים"),
    ("/he/management",      "ניהול וכלכלה"),
    ("/he/social-sciences", "מדעי החברה"),
    ("/he/humanities",      "מדעי הרוח"),
    ("/he/education",       "חינוך"),
    ("/he/art",             "אמנויות"),
    ("/he/social-work",     "עבודה סוציאלית"),
]

# Selectors used to detect page-structure anomalies
EXPECTED_LIST_SELECTORS: list[str] = [
    "div.program",
    "p.program-title",
]
EXPECTED_DETAIL_SELECTORS: list[str] = [
    "span.acceptance",
    "h1",
]


# ── Hebrew faculty → FIELDS vocabulary ───────────────────────────────────────

def _map_field(faculty: str, program_name: str = "") -> str:
    text = f"{faculty} {program_name}".strip()
    rules: list[tuple[list[str], str]] = [
        (["מדעי המחשב", "הנדסת תוכנה", "בינה מלאכותית", "AI", "נתונים"], "computer_science"),
        (["חשמל", "אלקטרוניקה"], "electrical_engineering"),
        (["הנדסה מכנית", "תעשייתית"], "mechanical_engineering"),
        (["הנדסה אזרחית", "סביבתית", "גיאו"], "civil_engineering"),
        (["ביו-רפואי", "ביוטכנולוגי", "מדעי החיים", "ביולוגי", "נוירו"], "biomedical"),
        (["מתמטיקה", "סטטיסטיקה", "מדעים מדויקים"], "mathematics"),
        (["פיזיקה", "כימיה", "מדעי הטבע"], "physics_chemistry"),
        (["רפואה", "סיעוד", "בריאות", "פרמקולוגיה"], "medicine"),
        (["משפטים", "משפטי"], "law"),
        (["ניהול", "כלכלה", "מינהל עסקים", "חשבונאות"], "business"),
        (["פסיכולוגיה", "מדעי החברה", "סוציולוגיה"], "psychology"),
        (["חינוך", "הוראה", "פדגוגיה"], "education"),
        (["מדעי הרוח", "ספרות", "היסטוריה", "פילוסופיה", "לשון"], "humanities"),
        (["אמנות", "עיצוב", "אדריכלות", "מוסיקה", "קולנוע", "תיאטרון"], "arts_design"),
        (["תקשורת", "עיתונאות", "מדיה"], "communication"),
        (["עבודה סוציאלית"], "psychology"),
    ]
    for keywords, field_name in rules:
        if any(kw in text for kw in keywords):
            return field_name
    return "other"


def _normalize_degree_type(program_name: str) -> str:
    s = program_name.lower()
    if re.search(r"ll\.?b|משפט", s):
        return "LLB"
    if re.search(r"b\.?arch|אדריכל", s):
        return "BArch"
    if re.search(r"b\.?ed|חינוך|הוראה", s):
        return "BEd"
    if re.search(r"b\.?f\.?a|אמנויות יפות", s):
        return "BFA"
    if re.search(r"b\.?sc|מדע|הנדסה|מדעים", s):
        return "BSc"
    return "BA"


def _parse_int(text: str) -> int | None:
    m = re.search(r"\d[\d,]*", text)
    if not m:
        return None
    try:
        return int(m.group().replace(",", ""))
    except ValueError:
        return None


# ── Intermediate dataclass ────────────────────────────────────────────────────

@dataclass
class _ProgramEntry:
    name_he: str
    faculty_hint: str   # from the faculty page slug
    detail_url: str     # absolute URL to node/XXXXX


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_faculty_page(html: str, faculty_hint: str) -> list[_ProgramEntry]:
    """Extract program entries from a faculty page."""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[_ProgramEntry] = []

    for card in soup.select("div.program"):
        title_el = card.select_one("p.program-title")
        link_el = card.select_one("a[href]")

        if not title_el or not link_el:
            continue

        name_he = title_el.get_text(strip=True)
        href = str(link_el.get("href", ""))
        if not href:
            continue

        # href is relative like "node/8276" or absolute
        if href.startswith("http"):
            detail_url = href
        elif href.startswith("/"):
            detail_url = BASE_URL + href
        else:
            detail_url = BASE_URL + "/" + href

        if not name_he:
            continue

        entries.append(_ProgramEntry(
            name_he=name_he,
            faculty_hint=faculty_hint,
            detail_url=detail_url,
        ))

    return entries


def parse_program_detail(html: str, entry: _ProgramEntry, scrape_year: int | None = None) -> ScrapeResult:
    """Extract full program data from a detail page."""
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now(timezone.utc)
    year = scrape_year or now.year

    # Program name from h1
    h1 = soup.select_one("h1")
    name_he = h1.get_text(strip=True) if h1 else entry.name_he

    # Sekem threshold from span.acceptance
    threshold = 0.0
    threshold_el = soup.select_one("#acceptanceThreshold")
    if threshold_el:
        t = _parse_int(threshold_el.get_text())
        if t is not None:
            threshold = float(t)

    # Field from faculty hint + program name
    program_field = _map_field(entry.faculty_hint, name_he)
    degree_type = _normalize_degree_type(name_he)

    return ScrapeResult(
        institution_id=INSTITUTION_ID,
        name_he=name_he,
        name_en=None,
        field=program_field,
        degree_type=degree_type,
        duration_years=3,
        location=LOCATION_HE,
        tuition_annual_ils=None,
        official_url=entry.detail_url,
        sekem_year=year,
        # TAU: 50/50 split. Weights are true multipliers so max sekem=800:
        #   bagrut_weight=4.0  → max contribution: 100×4=400
        #   psychometric_weight=0.5 → max contribution: 800×0.5=400
        bagrut_weight=4.0,
        psychometric_weight=0.5,
        threshold_sekem=threshold,
        subject_bonuses=[],
        bagrut_requirements=[],
        formula_source_url=entry.detail_url,
        raw_html="",
        scraped_at=now,
        page_checksum=page_checksum(html),
        scrape_ok=True,
    )


# ── TauScraper ────────────────────────────────────────────────────────────────

class TauScraper(BaseScraper):
    INSTITUTION_ID = INSTITUTION_ID

    async def scrape(self) -> list[ScrapeResult]:
        results: list[ScrapeResult] = []

        # ── Step 1: collect all program entries from faculty pages ────────────
        all_entries: list[_ProgramEntry] = []
        seen_urls: set[str] = set()

        for path, faculty_hint in FACULTY_PATHS:
            url = BASE_URL + path
            try:
                html = await self.fetch_dynamic(url)
            except Exception as exc:
                self._log.warning("tau.faculty_page_failed", path=path, error=str(exc))
                continue

            coverage = check_structure_integrity(html, EXPECTED_LIST_SELECTORS)
            if coverage < (1.0 - ANOMALY_THRESHOLD):
                self._log.warning(
                    "tau.faculty_structure_changed",
                    path=path,
                    coverage=f"{coverage:.0%}",
                )

            entries = parse_faculty_page(html, faculty_hint)
            new_entries = [e for e in entries if e.detail_url not in seen_urls]
            seen_urls.update(e.detail_url for e in new_entries)
            all_entries.extend(new_entries)
            self._log.info("tau.faculty_scraped", path=path, programs=len(new_entries))

        self._log.info("tau.total_programs", count=len(all_entries))

        # ── Step 2: fetch each program detail page ────────────────────────────
        for entry in all_entries:
            try:
                detail_html = await self.fetch_dynamic(entry.detail_url)

                coverage = check_structure_integrity(detail_html, EXPECTED_DETAIL_SELECTORS)
                if coverage < (1.0 - ANOMALY_THRESHOLD):
                    self._log.warning(
                        "tau.detail_structure_changed",
                        url=entry.detail_url,
                        coverage=f"{coverage:.0%}",
                    )

                result = parse_program_detail(detail_html, entry)
                results.append(result)
                self._log.debug("tau.program_scraped", name=entry.name_he, threshold=result.threshold_sekem)

            except Exception as exc:
                self._log.error(
                    "tau.program_detail_failed",
                    url=entry.detail_url,
                    name=entry.name_he,
                    error=str(exc),
                )
                results.append(ScrapeResult(
                    institution_id=INSTITUTION_ID,
                    name_he=entry.name_he,
                    field=_map_field(entry.faculty_hint, entry.name_he),
                    degree_type=_normalize_degree_type(entry.name_he),
                    official_url=entry.detail_url,
                    scrape_ok=False,
                    error_message=str(exc),
                ))

        ok = sum(1 for r in results if r.scrape_ok)
        self._log.info("tau.scrape_done", total=len(results), ok=ok, failed=len(results) - ok)
        return results
