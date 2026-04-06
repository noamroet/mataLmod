# MaTaLmod — Production Deployment Guide

> Target stack: **Vercel** (frontend) + **Railway** (API, Celery worker, Celery Beat) + **Supabase** (PostgreSQL) + **Upstash** (Redis)

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Node.js | ≥ 20 | Frontend build |
| Python | 3.12 | Backend |
| Railway CLI | latest | Deploy backend services |
| Vercel CLI | latest | Deploy frontend |
| psql | any | DB migrations (optional) |

Install CLIs:
```bash
npm install -g @railway/cli vercel
```

---

## 1. Provision Infrastructure

### 1.1 Supabase (PostgreSQL)

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string (URI)**
3. Copy the **asyncpg** connection string:
   ```
   postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
   ```
4. Save as `DATABASE_URL` in your secrets manager

> **Important**: Use the **direct** (non-pooled) connection for Alembic migrations.
> Use the **pooler** connection (port 6543 with `?pgbouncer=true`) for the live API if needed.

### 1.2 Upstash Redis

1. Create a Redis database at [upstash.com](https://upstash.com)
2. Copy the **TLS connection URL** (`rediss://...`)
3. Save as `REDIS_URL`

---

## 2. Set Up Secrets

Copy `.env.production.example` to `.env.production` and fill in all values:

```bash
cp .env.production.example .env.production
# Edit .env.production with real values — never commit this file
```

Generate cryptographic secrets:
```bash
# SECRET_KEY, ADMIN_API_KEY, NEXTAUTH_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Run Database Migrations

From the `backend/` directory:

```bash
cd backend
pip install -e .

# Set DATABASE_URL to the DIRECT (non-pooled) Supabase connection
export DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"

# Apply all migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, add field index and roadmap_progress
```

### Seed institutions

```bash
python scripts/seed_institutions.py
```

---

## 4. Deploy Backend to Railway

### 4.1 Create Railway project

```bash
railway login
railway init   # creates a new project
```

### 4.2 Create three services

In the Railway dashboard, create three services from this repo:

| Service name | Root directory | Start command |
|---|---|---|
| `api` | `backend/` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2` |
| `celery-worker` | `scraper/` | `celery -A scraper.celery_app worker -Q scrapers -c 2 -l info` |
| `celery-beat` | `scraper/` | `celery -A scraper.celery_app beat -l info --scheduler celery.beat.PersistentScheduler` |

> The scraper services need `backend/` on `PYTHONPATH` to import `app.*`.
> Add `PYTHONPATH=/app/backend` as an environment variable for those services.

### 4.3 Set environment variables

In Railway → each service → **Variables**, add all variables from `.env.production`:

**All three services need:**
```
DATABASE_URL=...
REDIS_URL=...
ANTHROPIC_API_KEY=...
SECRET_KEY=...
ENVIRONMENT=production
SENTRY_DSN=...        # optional
```

**API service additionally needs:**
```
ADMIN_API_KEY=...
CORS_ORIGINS=https://matalmod.co.il,https://matalmod.vercel.app
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Scraper services additionally need:**
```
PYTHONPATH=/app/backend
SCRAPER_RATE_LIMIT_SECONDS=2
SCRAPER_MAX_RETRIES=3
ANOMALY_CHECKSUM_THRESHOLD=0.30
```

### 4.4 Deploy

```bash
# From the repo root
railway up --service api
```

Or trigger deploys from the Railway dashboard after pushing to `main`.

### 4.5 Verify API health

```bash
curl https://YOUR_API_DOMAIN.railway.app/health
# Expected: {"status":"ok"}
```

---

## 5. Deploy Frontend to Vercel

### 5.1 Install frontend dependencies (including Sentry)

```bash
cd frontend
npm ci
npm install @sentry/nextjs
```

### 5.2 Set Vercel environment variables

```bash
cd frontend
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://YOUR_API_DOMAIN.railway.app

vercel env add NEXTAUTH_URL production
# Enter: https://matalmod.co.il

vercel env add NEXTAUTH_SECRET production
# Enter: (your generated secret)

vercel env add NEXT_PUBLIC_SENTRY_DSN production
# Enter: (your Sentry DSN, or leave empty to skip)
```

> Alternatively, add them in the Vercel dashboard under **Settings → Environment Variables**.
> The variable names in `vercel.json` use `@matalmod_*` references which must match
> the secrets you create in Vercel's UI.

### 5.3 Deploy

```bash
cd frontend
vercel --prod
```

Or connect your GitHub repo in the Vercel dashboard for automatic deployments on push to `main`.

### 5.4 Verify

```bash
curl https://matalmod.vercel.app/
# Should return the Next.js HTML
```

---

## 6. Post-Deployment Checklist

### Smoke tests

```bash
# Health check
curl https://YOUR_API.railway.app/health

# Institutions list
curl https://YOUR_API.railway.app/api/v1/institutions

# Programs list
curl https://YOUR_API.railway.app/api/v1/programs?limit=5

# Admin status (replace with your ADMIN_API_KEY)
curl -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  https://YOUR_API.railway.app/api/v1/admin/scraper-status
```

### Verify rate limiting

```bash
# Run 65 requests in quick succession — requests 61+ should return 429
for i in $(seq 1 65); do
  curl -s -o /dev/null -w "%{http_code}\n" https://YOUR_API.railway.app/api/v1/institutions
done
```

### Trigger first scrape (optional)

```bash
curl -X POST \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  https://YOUR_API.railway.app/api/v1/admin/scraper-trigger/TAU
# Expected: {"status":"queued","institution_id":"TAU"}
```

---

## 7. Monitoring & Observability

### Logs

- **API / Celery**: Railway dashboard → service → **Logs** tab
- All logs are structured JSON via `structlog`
- Filter by event: `event=http.request`, `event=scrape.success`, etc.

### Sentry

- Install Sentry CLI: `npm install -g @sentry/cli`
- Source maps are uploaded automatically by `@sentry/nextjs` on build
- Backend errors captured by `sentry-sdk[fastapi]`
- Dashboard: [sentry.io](https://sentry.io)

### Request IDs

Every API response includes `X-Request-ID` header. Use it to correlate logs:
```bash
curl -v https://YOUR_API.railway.app/api/v1/programs 2>&1 | grep X-Request-ID
```

---

## 8. Running Tests Before Deployment

### Backend (pytest)

```bash
cd backend
pip install -e ".[dev]"

# Unit + integration tests
pytest --cov=app --cov-report=term-missing -x

# Expected: 0 failures, coverage > 80%
```

### Frontend (Jest)

```bash
cd frontend
npm ci
npm run type-check   # tsc --noEmit
npm run lint         # eslint
npm run test:ci      # jest --ci --coverage

# Expected: 0 failures
```

### End-to-end (Playwright)

```bash
cd frontend
npx playwright install --with-deps chromium

# Run against local dev stack (docker compose up first)
npx playwright test

# Or against production:
PLAYWRIGHT_BASE_URL=https://matalmod.vercel.app npx playwright test
```

---

## 9. Rollback Procedure

### Backend rollback (Railway)

1. Railway dashboard → service → **Deployments**
2. Click the last-known-good deploy → **Redeploy**

### Database rollback

```bash
cd backend
# Roll back the last migration
alembic downgrade -1

# Roll back to initial state (destructive — use only in dev)
alembic downgrade base
```

### Frontend rollback (Vercel)

1. Vercel dashboard → project → **Deployments**
2. Find the previous deployment → **...** → **Promote to Production**

---

## 10. Environment Variables Reference

| Variable | Required | Service | Notes |
|---|---|---|---|
| `DATABASE_URL` | ✅ | API, Workers | asyncpg connection string |
| `REDIS_URL` | ✅ | API, Workers | Celery broker + cache |
| `ANTHROPIC_API_KEY` | ✅ | API | claude-sonnet-4-6 |
| `SECRET_KEY` | ✅ | API | JWT signing key |
| `ADMIN_API_KEY` | ✅ | API | `/admin/*` auth |
| `ENVIRONMENT` | ✅ | API | `production` |
| `CORS_ORIGINS` | ✅ | API | Comma-separated frontend origins |
| `SENTRY_DSN` | ☑️ | API | Error tracking |
| `SENTRY_TRACES_SAMPLE_RATE` | ☑️ | API | Default `0.1` |
| `NEXT_PUBLIC_API_URL` | ✅ | Frontend | API base URL |
| `NEXTAUTH_URL` | ✅ | Frontend | Frontend URL |
| `NEXTAUTH_SECRET` | ✅ | Frontend | NextAuth signing key |
| `NEXT_PUBLIC_SENTRY_DSN` | ☑️ | Frontend | Browser error tracking |
| `SCRAPER_RATE_LIMIT_SECONDS` | ☑️ | Workers | Default `2` |
| `PYTHONPATH` | ✅ | Workers | Must include `backend/` path |

✅ = required in production  ☑️ = optional but recommended

---

*MaTaLmod v1.0 — Last updated 2026-04-05*
