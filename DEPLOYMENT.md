# Production Deployment

This repository deploys as three connected resources:

- FastAPI backend and model inference on Render
- Managed PostgreSQL on Render
- Next.js frontend on Vercel

The production seed is idempotent: it creates 240 synthetic demo transactions only when the database is empty. It never retrains the model during deployment.

## 1. Deploy the backend and database on Render

1. Sign in to Render and choose **New > Blueprint**.
2. Connect the GitHub repository `Adarsh-ynwa/risk`.
3. Render detects the root `render.yaml` and creates:
   - `ai-risk-manager-api`
   - `ai-risk-manager-db`
4. When prompted for environment variables, enter:
   - `CORS_ORIGINS`: temporarily use `http://localhost:3000`
   - `GROQ_API_KEY`: your Groq key, or leave it empty to use deterministic fallback
5. Apply the Blueprint and wait for the API health check to pass.
6. Copy the backend URL, for example `https://ai-risk-manager-api.onrender.com`.
7. Verify `https://YOUR-BACKEND.onrender.com/health`.

Expected health fields:

```json
{
  "status": "ok",
  "model_loaded": true,
  "database_connected": true,
  "groq_configured": true
}
```

`groq_configured` is `false` when fallback investigation mode is used.

## 2. Deploy the frontend on Vercel

1. Import the same GitHub repository in Vercel.
2. Set **Root Directory** to `frontend`.
3. Keep the detected Next.js build settings.
4. Add this Production environment variable:

```text
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND.onrender.com
```

5. Deploy and copy the resulting Vercel URL.

## 3. Complete CORS configuration

1. Return to the Render web service.
2. Replace `CORS_ORIGINS` with the exact Vercel production origin, without a trailing slash:

```text
https://YOUR-FRONTEND.vercel.app
```

3. Trigger a backend redeploy.
4. Trigger a Vercel redeploy if `NEXT_PUBLIC_API_URL` was added after its first build.

For multiple exact frontend origins, separate them with commas.

## 4. Production smoke test

Test in this order:

1. Backend `/health`
2. Frontend Dashboard
3. Evaluation page
4. Alert Queue
5. Add Transaction
6. AI Investigation
7. OTP verification simulation
8. Human block approval
9. Unblock review
10. Refresh and verify that PostgreSQL retained all status changes

## Environment variables

### Render backend

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supplied automatically by the Render Blueprint database reference |
| `SEED_DEMO_DATA` | `true` for an empty demo deployment |
| `CORS_ORIGINS` | Comma-separated exact frontend origins |
| `GROQ_API_KEY` | Optional Groq key; deterministic fallback works without it |

### Vercel frontend

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Public HTTPS URL of the Render backend |

Never commit real secrets or production database URLs to Git.
