import structlog
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import accounts, admin, advisor, eligibility, institutions, programs

logger = structlog.get_logger(__name__)

# ── Sentry ────────────────────────────────────────────────────────────────────
# Initialise before the app is created so all errors are captured.
# No-op when SENTRY_DSN is empty.

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # Don't send PII — no user emails in error reports
        send_default_pii=False,
    )
    logger.info("sentry.initialised", environment=settings.ENVIRONMENT)

# ── Rate limiter (slowapi) ────────────────────────────────────────────────────
# Global default: 60 requests / minute per IP across all /api/v1/* routes.
# The advisor router enforces a tighter 10 req/min limit independently.

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    # Don't rate-limit the health endpoint
    enabled=not settings.is_development,
)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MaTaLmod API",
    description="מה תלמד? — AI-powered degree discovery for post-army Israelis",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ── Middleware (applied in LIFO order — last added = outermost) ───────────────

# 1. CORS — must be first/outermost to handle pre-flight correctly
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 2. Rate limiting (SlowAPIMiddleware applies `default_limits` globally)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 3. Request logging (structured JSON, skips /health)
app.add_middleware(RequestLoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

_API_PREFIX = "/api/v1"

app.include_router(institutions.router, prefix=_API_PREFIX)
app.include_router(programs.router,     prefix=_API_PREFIX)
app.include_router(eligibility.router,  prefix=_API_PREFIX)
app.include_router(advisor.router,      prefix=_API_PREFIX)
app.include_router(accounts.router,     prefix=_API_PREFIX)
app.include_router(admin.router,        prefix=_API_PREFIX)

# ── Ops ───────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["ops"], include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ── Global error handler (ensures Sentry captures unhandled exceptions) ───────


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "http.unhandled_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
