"""
Celery application for the MaTaLmod scraper pipeline.

Workers are started with:
    celery -A scraper.celery_app worker --loglevel=info

Beat scheduler (nightly runs):
    celery -A scraper.celery_app beat --loglevel=info
"""

import logging
import os

import structlog
from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    worker_ready,
    worker_shutdown,
)

# ── Structlog configuration ───────────────────────────────────────────────────
# Use JSON renderer in production; coloured console in development.

_is_prod = os.environ.get("ENVIRONMENT", "development") == "production"

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        (
            structlog.processors.JSONRenderer()
            if _is_prod
            else structlog.dev.ConsoleRenderer()
        ),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Forward stdlib logging to structlog (captures Celery's own log messages)
logging.basicConfig(format="%(message)s", level=logging.INFO)

log = structlog.get_logger("celery_app")

# ── Celery app ────────────────────────────────────────────────────────────────

# Read broker URL from the same env var used by the backend
_REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

app = Celery(
    "mataLmod_scraper",
    broker=_REDIS_URL,
    backend=_REDIS_URL.replace("/0", "/1"),  # separate DB for task results
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,      # one task at a time per worker
    task_acks_late=True,               # re-queue on worker crash
    task_reject_on_worker_lost=True,
    # Emit structured task events for observability
    task_track_started=True,
    task_send_sent_event=True,
)

# ── Structured task lifecycle signals ────────────────────────────────────────


@worker_ready.connect
def on_worker_ready(sender, **_kwargs):  # type: ignore[no-untyped-def]
    log.info("celery.worker_ready", worker=str(sender))


@worker_shutdown.connect
def on_worker_shutdown(sender, **_kwargs):  # type: ignore[no-untyped-def]
    log.info("celery.worker_shutdown", worker=str(sender))


@task_prerun.connect
def on_task_prerun(task_id, task, args, kwargs, **_):  # type: ignore[no-untyped-def]
    structlog.contextvars.bind_contextvars(task_id=task_id, task_name=task.name)
    log.info(
        "celery.task_started",
        task_id=task_id,
        task_name=task.name,
        args=args,
    )


@task_postrun.connect
def on_task_postrun(task_id, task, args, state, retval, **_):  # type: ignore[no-untyped-def]
    log.info(
        "celery.task_finished",
        task_id=task_id,
        task_name=task.name,
        state=state,
        args=args,
    )
    structlog.contextvars.unbind_contextvars("task_id", "task_name")


@task_failure.connect
def on_task_failure(task_id, exception, traceback, einfo, **_):  # type: ignore[no-untyped-def]
    log.error(
        "celery.task_failed",
        task_id=task_id,
        error=str(exception),
        exc_info=einfo,
    )

# Autodiscover tasks in the tasks/ package
app.conf.imports = ["scraper.tasks.scrape_dispatch"]

# ── Nightly Beat schedule ─────────────────────────────────────────────────────
# Israel time is UTC+3 (IDT summer) / UTC+2 (IST winter).
# 02:00 IDT = 23:00 UTC (previous day).  We schedule at 23:00 UTC year-round.

app.conf.beat_schedule = {
    "scrape-TAU-nightly": {
        "task": "scraper.tasks.scrape_dispatch.scrape_institution",
        "schedule": crontab(hour=23, minute=0),
        "args": ["TAU"],
        "options": {"queue": "scrapers"},
    },
}
