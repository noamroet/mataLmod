"""
Anomaly detection for scraper results.

Rules (any one triggers anomaly):
  1. Empty result set
  2. >50% of records have scrape_ok=False
  3. All threshold_sekem values are zero (parser silently broke)
  4. Page structure changed on >30% of pages (measured via page_checksum
     comparison is done per-page inside the scraper; here we only check
     data-level invariants)
"""

from __future__ import annotations

import structlog

from scrapers.base import ScrapeResult

log = structlog.get_logger(__name__)


def detect_anomaly(results: list[ScrapeResult], institution_id: str) -> bool:
    """
    Return True if the result set looks anomalous and should NOT be published.

    Parameters
    ----------
    results         : full list returned by scraper.scrape()
    institution_id  : used only for structured log output
    """
    if not results:
        log.warning("validator.anomaly", reason="empty_result_set", institution=institution_id)
        return True

    total = len(results)
    failed = sum(1 for r in results if not r.scrape_ok)
    failure_rate = failed / total

    if failure_rate > 0.50:
        log.warning(
            "validator.anomaly",
            reason="high_failure_rate",
            institution=institution_id,
            failure_rate=f"{failure_rate:.0%}",
        )
        return True

    # Check that at least some programs have a non-zero threshold
    ok_results = [r for r in results if r.scrape_ok]
    nonzero_thresholds = [r for r in ok_results if r.threshold_sekem > 0]
    if ok_results and not nonzero_thresholds:
        log.warning(
            "validator.anomaly",
            reason="all_thresholds_zero",
            institution=institution_id,
        )
        return True

    log.info(
        "validator.ok",
        institution=institution_id,
        total=total,
        failed=failed,
        ok=total - failed,
    )
    return False
