# MaTaLmod — Project Context
> מה תלמד? | AI-Powered Degree Discovery Platform for Israel

---

## What this project is

MaTaLmod ("מה תלמד?" — "What will you study?") is a web-based platform that helps
post-army Israelis discover which university degree programs they are eligible for,
understand what they would study, and evaluate career outcomes — all in one place.

The product is built on a fully automated scraping pipeline: nightly scrapers pull
admission thresholds, syllabi, and program metadata from Israeli university websites
and public government sources (data.gov.il). An AI advisor layer (Claude) provides
personalized, conversational guidance in Hebrew and English.

**Target user:** Israeli young adults (age 21–24) who just finished military service
and are deciding what and where to study.

---

## Architecture — DO NOT DEVIATE FROM THIS

```
Frontend       Next.js 14 + TypeScript + Tailwind CSS (RTL Hebrew default)
Backend API    Python 3.12 + FastAPI + SQLAlchemy 2.0 (async)
Database       PostgreSQL 16 (via Supabase in production)
Cache / Queue  Redis 7 + Celery (scraper jobs) + Celery Beat (scheduler)
Scraping       Playwright (Python) + BeautifulSoup4 + httpx
AI Advisor     Anthropic API — model: claude-sonnet-4-6
Infra (local)  Docker Compose (7 services)
Infra (prod)   Vercel (frontend) + Railway (API + workers)
```

### Folder structure

```
mataLmod/
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py     Pydantic v2 Settings
│   │   │   ├── database.py   Async SQLAlchemy engine + session
│   │   │   └── constants.py  FIELDS vocabulary, INSTITUTIONS map
│   │   ├── models/           SQLAlchemy ORM models
│   │   ├── schemas/          Pydantic v2 request/response schemas
│   │   ├── routers/          FastAPI route handlers
│   │   ├── services/         Business logic (sekem.py, advisor.py)
│   │   └── dependencies.py   Shared FastAPI dependencies
│   ├── alembic/              Database migrations
│   ├── scripts/              seed_institutions.py, etc.
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/                 Next.js application
│   ├── src/
│   │   ├── app/              App Router pages
│   │   │   ├── [locale]/
│   │   │   │   ├── page.tsx            Landing page
│   │   │   │   ├── intake/page.tsx     Intake form wizard
│   │   │   │   ├── results/page.tsx    Eligibility results
│   │   │   │   ├── program/[id]/       Program detail
│   │   │   │   ├── compare/page.tsx    Side-by-side comparison
│   │   │   │   └── account/page.tsx    User profile (protected)
│   │   ├── components/
│   │   ├── store/            Zustand stores
│   │   └── lib/              API client, utils
│   ├── messages/
│   │   ├── he.json           Hebrew strings (ALL UI text lives here)
│   │   └── en.json           English strings
│   ├── public/
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── scraper/                  Data pipeline
│   ├── scrapers/
│   │   ├── base.py           ScrapeResult schema + abstract BaseScraper
│   │   ├── tau.py            Tel Aviv University
│   │   ├── huji.py           Hebrew University
│   │   ├── technion.py       Technion
│   │   ├── bgu.py            Ben-Gurion University
│   │   ├── biu.py            Bar-Ilan University
│   │   ├── haifa.py          University of Haifa
│   │   └── ariel.py          Ariel University
│   ├── tasks/
│   │   ├── scrape_dispatch.py   Celery tasks + Beat schedule
│   │   └── summarize.py         AI syllabus summarizer task
│   ├── pipeline/
│   │   ├── validator.py      Anomaly detection + diff checking
│   │   └── publisher.py      Staging -> live DB promotion
│   ├── celery_app.py
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── CLAUDE.md                 ← you are here
```

---

## Coding rules — enforce these always

### Python (backend + scraper)
- Type hints on every function signature — no bare `dict`, use Pydantic models
- `async`/`await` throughout — no sync DB calls in FastAPI routes
- Pydantic v2 for all request/response schemas and settings
- SQLAlchemy 2.0 style: `select()` not `query()`, `async with session` not `db.session`
- Never hardcode credentials — always `settings.DATABASE_URL` from `core/config.py`
- Every scraper module implements `BaseScraper` and returns `list[ScrapeResult]`
- Use `structlog` for all logging — JSON format, no bare `print()`
- Test coverage target: 90%+ on services/, 80%+ overall

### TypeScript (frontend)
- `strict: true` in tsconfig — no `any`, no `@ts-ignore`
- Functional React components only — no class components
- All server state via React Query (`@tanstack/react-query`)
- All client state via Zustand stores in `src/store/`
- No inline styles — Tailwind classes only
- All UI text via `next-intl` `useTranslations()` — never hardcode Hebrew/English strings
- All API calls through `src/lib/api.ts` client — never call `fetch()` directly in components

### General
- Never commit `.env` files — only `.env.example`
- Every PR must pass: `pytest`, `jest`, `tsc --noEmit`, `eslint`
- Git commits follow Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`

---

## Database schema (summary)

| Table | Purpose |
|---|---|
| `institutions` | The 7 universities (TAU, HUJI, TECHNION, BGU, BIU, HAIFA, ARIEL) |
| `programs` | Every accredited degree program per institution |
| `sekem_formulas` | Weighted admission formula + threshold per program per year |
| `syllabi` | Raw HTML + AI-generated plain-language summaries |
| `career_data` | Job titles, salary ranges, demand trend per program |
| `scrape_runs` | Full audit trail of every scraper run |
| `users` | Optional accounts (anonymous use is the default) |
| `saved_programs` | User bookmarks |

**Key rule:** `sekem_formulas` rows are never deleted, only appended (versioned by `year`).
Always query `WHERE year = (SELECT MAX(year) FROM sekem_formulas WHERE program_id = ...)`.

---

## Sekem calculation logic

Sekem is the weighted Israeli university admission composite score.

```python
# Weighted bagrut average: 5-unit subjects get a 25% bonus multiplier
bagrut_avg = weighted_average(grades, five_unit_bonus=1.25)

# Sekem composite (weights differ per university + program)
sekem = (bagrut_avg * formula.bagrut_weight) + (psychometric * formula.psychometric_weight)

# Add subject bonuses (e.g. +X points for 5-unit math at Technion CS)
for bonus in formula.subject_bonuses:
    if user_qualifies(profile, bonus):
        sekem += bonus.bonus_points

# Eligibility thresholds
eligible   = sekem >= formula.threshold_sekem
borderline = (formula.threshold_sekem - 30) <= sekem < formula.threshold_sekem
```

---

## AI Advisor — system prompt rules

The advisor is powered by `claude-sonnet-4-6`. These rules are non-negotiable:

1. **Never fabricate data.** Only cite thresholds and course names present in `DB_CONTEXT`.
2. **Always cite the data year** when mentioning Sekem thresholds.
3. **Always append** `בדוק תמיד באתר הרשמי` after every threshold reference.
4. **Language detection:** respond in Hebrew unless the user writes in English.
5. **Tools available:** `get_program_details(program_id)` and `search_programs(query, filters)`.
6. **Max context:** truncate `conversation_history` to stay under 4,000 input tokens per turn.
7. **Rate limit:** 10 requests/minute per IP on `/api/v1/advisor/chat`.

---

## Data sources

| Source | What we get | Method |
|---|---|---|
| University websites (7) | Programs, thresholds, Sekem formulas, syllabi, tuition | Playwright scraper per institution |
| data.gov.il (VATAT/CHE) | Accredited program registry, institution list | CKAN REST API |
| CBS (Lamas) / data.gov.il | Salary by profession, employment rates | REST API |
| AllJobs / Drushim | Job posting frequency by title (demand signal only) | HTTP scrape (counts only) |

**Scraper resilience rules:**
- Rate limit: 1 request per 2 seconds per institution
- Retry: 3 attempts with exponential backoff
- Checksum: if page structure changes >30%, fire alert and mark as `STALE` — never overwrite good data with broken parse
- Failed scrapers never affect user-facing app — last good DB record is served with a staleness flag

---

## V1 institution scope

| ID | Hebrew Name | English Name | City |
|---|---|---|---|
| TAU | אוניברסיטת תל אביב | Tel Aviv University | Tel Aviv |
| HUJI | האוניברסיטה העברית | Hebrew University of Jerusalem | Jerusalem |
| TECHNION | הטכניון | Technion — Israel Institute of Technology | Haifa |
| BGU | אוניברסיטת בן גוריון | Ben-Gurion University of the Negev | Be'er Sheva |
| BIU | אוניברסיטת בר אילן | Bar-Ilan University | Ramat Gan |
| HAIFA | אוניברסיטת חיפה | University of Haifa | Haifa |
| ARIEL | אוניברסיטת אריאל | Ariel University | Ariel |

---

## Field taxonomy (controlled vocabulary)

```python
FIELDS = [
    "computer_science",        # מדעי המחשב והנדסת תוכנה
    "electrical_engineering",  # הנדסת חשמל ואלקטרוניקה
    "mechanical_engineering",  # הנדסה מכנית ותעשייתית
    "civil_engineering",       # הנדסה אזרחית וסביבתית
    "biomedical",              # הנדסה ביו-רפואית ומדעי החיים
    "mathematics",             # מתמטיקה וסטטיסטיקה
    "physics_chemistry",       # פיזיקה וכימיה
    "medicine",                # רפואה ובריאות
    "law",                     # משפטים
    "business",                # מינהל עסקים וכלכלה
    "psychology",              # פסיכולוגיה ומדעי החברה
    "education",               # חינוך והוראה
    "humanities",              # מדעי הרוח
    "arts_design",             # אמנות, עיצוב ואדריכלות
    "communication",           # תקשורת ומדיה
    "agriculture",             # חקלאות ומדעי המזון
    "other",                   # אחר / בין-תחומי
]
```

---

## Environment variables required

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mataLmod
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=<random 32 bytes>
ENVIRONMENT=development  # development | staging | production
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<random 32 bytes>

# Scraper (inherits DATABASE_URL and REDIS_URL from backend)
SCRAPER_RATE_LIMIT_SECONDS=2
SCRAPER_MAX_RETRIES=3
ANOMALY_CHECKSUM_THRESHOLD=0.30
```

---

## Docker services (local dev)

```yaml
api:          FastAPI backend        → localhost:8000
frontend:     Next.js dev server     → localhost:3000
db:           PostgreSQL 16          → localhost:5432
redis:        Redis 7                → localhost:6379
celery:       Celery worker          (no exposed port)
celery-beat:  Celery Beat scheduler  (no exposed port)
flower:       Celery monitoring UI   → localhost:5555
```

Health check: `GET http://localhost:8000/health` → `{"status": "ok"}`

---

## Out of scope — v1

- Graduate programs (MA, MBA, PhD)
- Mechina (preparatory program) guidance
- Direct application submission to universities
- Scholarship matching
- Native iOS / Android apps
- Olim-specific tracks (foreign degree recognition)
- Open University (no Sekem system)

---

## Key product decisions (do not relitigate these)

| Decision | Choice | Reason |
|---|---|---|
| UX model | Hybrid: structured form intake + AI advisor | Best of precision + depth |
| User accounts | Optional — anonymous first, login to save | Reduce friction at entry |
| Data freshness | Cached DB primary, live scrape fallback | Performance + resilience |
| AI model | claude-sonnet-4-6 | Best Hebrew quality + tool use |
| Scraping approach | Per-institution modules, nightly batch | Maintainability + resilience |
| Language default | Hebrew (RTL) primary, English secondary | Target audience is Hebrew-native |

---

*Last updated: April 2026 — MaTaLmod v1.0*
