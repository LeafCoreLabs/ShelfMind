# Deploy ShelfMind Backend (Free)

Use this guide when your **frontend is already live** and you only need the API + background jobs on a free tier.

## What you get (free)

| Feature | Free deploy |
|---------|-------------|
| Auth, store suite, admin portal | Yes |
| Prophet forecasts (on-demand + scheduled) | Yes (embedded Celery) |
| Weather / signals / NL queries / chat | Yes (with Groq key) |
| CSV import | Yes |
| Report export | Yes (inline download; no MinIO needed) |
| Admin job triggers | Yes |

## Recommended stack: Render (free)

The repo includes `render-backend.yaml` — API + Postgres + Redis only (no frontend service).

### Step 1 — Push to GitHub

Ensure your code is on GitHub (fork or push this repo).

### Step 2 — Create Blueprint on Render

1. Go to [render.com](https://render.com) → **New → Blueprint**.
2. Connect the repo.
3. When asked for the blueprint file, use **`render-backend.yaml`** (or copy its contents into `render.yaml` if Render only reads the default name).
4. Set **`GROQ_API_KEY`** when prompted ([console.groq.com](https://console.groq.com) — free tier).
5. Click **Apply**. First build takes ~10–15 min (Prophet/ML deps).

### Step 3 — Verify backend

After deploy succeeds:

```text
https://<your-service>.onrender.com/api/health        → {"status":"ok",...}
https://<your-service>.onrender.com/api/docs        → Swagger UI
```

Demo login after seed runs on first boot:

- Store owner: `owner@shelfmind.com` / `user123`
- Admin: `admin@shelfmind.com` / `admin123`

### Step 4 — Point your frontend at the API

The frontend reads the API URL at **build time**:

```bash
# In frontend/, create .env.production (or set in your host's env)
VITE_API_URL=https://<your-service>.onrender.com
```

Then **rebuild and redeploy** the frontend. Without this, login and all API calls will fail.

**Render static site:** set `VITE_API_URL` in the service env vars and trigger a new deploy.

**Vercel / Netlify:** add `VITE_API_URL` in project settings → Environment Variables → redeploy.

### Step 5 — Smoke test

1. Open your frontend → log in as store owner.
2. Dashboard KPIs and heatmap load.
3. **Demand Planner** → forecasts visible.
4. **Store Assistant** → ask *"What to stock this week?"*
5. **Reports → Generate export** → CSV downloads.
6. Admin → **System Health** → Postgres, Redis, Celery should show healthy.

---

## How free-tier background jobs work

Render does **not** offer free [background workers](https://render.com/docs/deploy-celery). This project runs Celery **inside the API container** when `EMBED_CELERY=true` (set in `render-backend.yaml`):

- Celery worker + beat run in the background on the same free web service.
- Scheduled tasks: signals (every 6h), forecasts (2am IST), benchmarks, alerts, etc.
- Admin **Jobs** buttons queue tasks the same way as Docker Compose locally.

**Trade-off:** free web services **sleep after ~15 min idle** (~1 min cold start). While asleep, scheduled Celery jobs do not run until something wakes the service (e.g. you open the app).

---

## Environment variables

| Variable | Required | Notes |
|----------|----------|-------|
| `GROQ_API_KEY` | Recommended | Powers NL queries, chat agent, admin copilot. Without it, demo fallbacks apply. |
| `SECRET_KEY` | Auto on Render | JWT signing |
| `EMBED_CELERY` | `true` | Embedded worker + beat (free tier) |
| `S3_ENABLED` | `false` | Report exports use inline CSV download |
| `DATABASE_URL` | Auto | From Render Postgres |
| `REDIS_URL` | Auto | From Render Key Value |

### Optional: Cloudflare R2 for S3 report storage (free)

1. Create an R2 bucket at [dash.cloudflare.com](https://dash.cloudflare.com).
2. Create API token with Object Read & Write.
3. On Render, set:

```text
S3_ENABLED=true
S3_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY=<r2_access_key_id>
S3_SECRET_KEY=<r2_secret_access_key>
S3_BUCKET=shelfmind-reports
```

---

## Postgres free tier expiry

Render free Postgres **expires after 90 days**. Before expiry:

1. Export data, or
2. Migrate to [Neon](https://neon.tech) / [Supabase](https://supabase.com) free Postgres and set `DATABASE_URL` + `DATABASE_URL_SYNC` on the API service.

---

## Alternative free hosts

| Host | API | Postgres | Redis | Celery | Notes |
|------|-----|----------|-------|--------|-------|
| **Render** | Free web | Free 90d | Free Key Value | Embedded in API | Easiest; repo ready |
| **Fly.io** | Free allowance | Neon external | Upstash free | Same embed pattern | More setup |
| **Railway** | Trial credits | Included | Included | Paid worker or embed | Not permanently free |

---

## Troubleshooting

**502 / cold start** — Wait ~60s after first request; free tier wakes from sleep.

**Login works locally but not production** — Frontend `VITE_API_URL` must match backend URL exactly (no trailing slash), then redeploy frontend.

**Celery shows 0 workers in System Health** — Confirm `EMBED_CELERY=true` on the API service and check deploy logs for `Starting embedded Celery worker`.

**Report export fails** — With `S3_ENABLED=false`, exports return a data URL; ensure the browser allows downloads from your frontend origin.

**Build OOM on Render** — Free tier has 512MB RAM; Dockerfile already uses `-w 1` worker. If build fails, retry or use a paid Starter instance for the API only.

---

## Full stack (frontend + backend)

If you want both on Render, use root **`render.yaml`** instead — it deploys `shelfmind-web` + `shelfmind-api` together with `VITE_API_URL` wired automatically.

See also [DEPLOY_RENDER.md](./DEPLOY_RENDER.md).
