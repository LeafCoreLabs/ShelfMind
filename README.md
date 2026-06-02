# ShelfMind

**Your next week's bestseller, predicted today.**

ShelfMind is a hyperlocal demand prediction platform for retail and D2C store owners. It fuses transaction history, local events, weather, salary cycles, and social trends to deliver SKU-level stocking recommendations — not category averages.

Built by **Team Toxicos.exe**.

## Features

- **Role-based auth** — Admin and store owner login with JWT
- **Split-screen login** — SelfMind branding + glassmorphic role cards
- **Admin portal** — User/store management, job triggers, store-owner onboarding wizard
- **Natural-language queries** — SKU-level predictions with rationale and confidence scores
- **Buying-trend heatmap** — Animated peak purchase windows by product category
- **Prophet forecasting** — 7-day demand predictions per SKU
- **CSV POS import** — Upload existing point-of-sale exports
- **Report export** — Forecast CSV reports stored in MinIO

## Demo Credentials

| Role | Email | Password | Landing page |
|------|-------|----------|--------------|
| Admin | admin@shelfmind.com | admin123 | `/admin` |
| Store Owner | owner@shelfmind.com | user123 | `/dashboard` |

## Quick Start

```bash
cd SelfMind
cp .env.example .env
docker compose up --build
```

Open **http://localhost/login**

### Demo walkthrough

1. Sign in as **Store Owner** → glass KPI dashboard, heatmap, AI query
2. Ask *"What to stock this week?"* for umbrella/beverages/noodles recommendations
3. Sign out → Sign in as **Admin** → platform KPIs, user/store management
4. Go to **Onboard** → complete 5-step wizard to create a new store owner

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React, TypeScript, Vite, Recharts, Framer Motion, GSAP, React Router |
| Backend | Python, FastAPI, Gunicorn, JWT (python-jose), bcrypt |
| Jobs | Celery + Redis |
| Database | PostgreSQL + PgBouncer |
| Storage | MinIO |
| Proxy | Nginx |

## API Endpoints

### Auth (public)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login → JWT token |
| GET | `/api/auth/me` | Current user (Bearer token) |

### Dashboard (authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard/summary` | Store KPIs |
| GET | `/api/dashboard/heatmap` | Purchase heatmap |
| GET | `/api/dashboard/forecasts` | SKU forecasts |
| POST | `/api/dashboard/query` | NL inventory query |
| POST | `/api/dashboard/import/csv` | POS CSV upload |
| POST | `/api/dashboard/reports/export` | Export to MinIO |

### Admin (admin role only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/stats` | Platform KPIs |
| GET | `/api/admin/users` | List users |
| POST | `/api/admin/users` | Create user |
| GET/PATCH/DELETE | `/api/admin/users/{id}` | Manage user |
| GET/POST/PATCH/DELETE | `/api/admin/stores` | Manage stores |
| POST | `/api/admin/onboarding/start` | Start onboarding draft |
| PUT | `/api/admin/onboarding/{id}/step/{n}` | Save wizard step |
| POST | `/api/admin/onboarding/{id}/complete` | Create store + owner |
| POST | `/api/admin/jobs/{forecasts,signals,benchmarks}` | Trigger Celery jobs |

## Environment Variables

See [`.env.example`](.env.example). Key additions:

- `SECRET_KEY` — Used for JWT signing (set a strong value in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — Optional, defaults to 480

## License

CONFIDENTIAL — Team Toxicos.exe | All rights reserved
