# Deploy ShelfMind on Render

## One-time setup (Dashboard)

1. Push this repo to [GitHub](https://github.com/LeafCoreLabs/ShelfMind).
2. Sign in at [render.com](https://render.com) and connect your GitHub account.
3. Click **New → Blueprint**.
4. Select the **LeafCoreLabs/ShelfMind** repository (branch `main`).
5. Render reads `render.yaml` and shows:
   - **shelfmind-api** — FastAPI backend (Docker)
   - **shelfmind-web** — React frontend (static)
   - **shelfmind-db** — PostgreSQL (free, 30-day trial)
   - **shelfmind-redis** — Key Value / Redis
6. When prompted, enter **`GROQ_API_KEY`** (from [console.groq.com](https://console.groq.com)).
7. Click **Apply** / **Deploy Blueprint**.

First deploy takes ~10–15 minutes (Docker build includes Prophet/ML deps).

## URLs after deploy

| Service | URL |
|---------|-----|
| Frontend | `https://shelfmind-web.onrender.com` |
| Backend API | `https://shelfmind-api.onrender.com` |
| API docs | `https://shelfmind-api.onrender.com/api/docs` |
| Health | `https://shelfmind-api.onrender.com/api/health` |

Demo login: `owner@shelfmind.com` / `user123`

## CLI (optional)

Install: [Render CLI docs](https://render.com/docs/cli)

```bash
brew install render          # macOS
render login
render blueprints validate render.yaml
render deploys create <SERVICE_ID>   # trigger redeploy
```

Set `RENDER_API_KEY` for CI/CD (GitHub Actions example in Render docs).

## Free tier limits

- API sleeps after ~15 min idle (~1 min cold start)
- Postgres free DB expires after 90 days
- Celery runs **inside** the API container (`EMBED_CELERY=true`) — no paid background worker needed
- Report export uses inline CSV when `S3_ENABLED=false` (optional Cloudflare R2 for S3 storage)

For **backend-only** deploy when frontend is already live, see [DEPLOY_BACKEND_FREE.md](./DEPLOY_BACKEND_FREE.md) and `render-backend.yaml`.

## Redeploy

Push to `main` — Render auto-deploys if enabled on the Blueprint.
