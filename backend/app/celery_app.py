from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "mataLmod",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Jerusalem",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Expose as module-level `app` so `celery -A app.celery_app` works
app = celery_app
