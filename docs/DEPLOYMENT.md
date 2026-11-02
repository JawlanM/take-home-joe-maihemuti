# Deployment Design (Google Cloud)

The app runs locally with Docker Compose. This is how I'd deploy it on Google Cloud. GCP fits
because the AI provider (Gemini) is Google's too: one bill, one set of credentials, and the
API key stays inside the project's Secret Manager.

## Architecture

```
 Browser
   │  HTTPS
   ▼
 Firebase Hosting ── static React build (CDN)
   │  HTTPS /api/*
   ▼
 Cloud Run: candidate-tracker-api ──── Gemini API (gemini-3.5-flash)
   │  (container from backend/Dockerfile)     ▲
   │                                          │ GEMINI_API_KEY from Secret Manager
   ▼
 MongoDB Atlas (hosted on GCP, australia-southeast1)
```

| Component | Service | Why |
|---|---|---|
| Frontend | **Firebase Hosting** | Static files on a global CDN with HTTPS; free tier covers this. |
| Backend API | **Cloud Run** | Runs the existing Dockerfile unchanged, scales to zero when idle, HTTPS by default. |
| Container images | **Artifact Registry** | Where Cloud Build pushes images for Cloud Run. |
| Build | **Cloud Build** | Builds the backend image from the repo on each push to `main`. |
| Database | **MongoDB Atlas on GCP** (Melbourne/Sydney region) | GCP has no native MongoDB; Atlas runs it inside Google's network, near users. |
| Secrets | **Secret Manager** | Gemini key and MongoDB URI injected into Cloud Run as env vars; never in the repo. |
| AI | **Gemini API** | Same provider as the hosting; billed to the same project. |
| Logs / alerts | **Cloud Logging + Cloud Monitoring** | Cloud Run logs by default; alert on 5xx rate and on failed-summary log lines. |
| Spend guard | **Cloud Billing budget alert** | Email at 50% / 90% of a monthly budget. |

## Things that change for a public deployment

- **No authentication is in scope**, so a public URL means anyone could read candidate data
  and trigger Gemini calls. Before real use: put it behind **Identity-Aware Proxy** (Google
  sign-in for staff only), which needs no code changes.
- **Rate-limit the AI.** Cap Gemini usage with an API quota in the project, and a Cloud Run
  max-instances limit (e.g. 3) so traffic spikes can't run up the bill.
- **CORS:** set `CORS_ORIGINS` to the Firebase Hosting domain only.
- **Data residency:** Australian regions for Cloud Run and Atlas, since candidate data is
  personal information.

## Rough monthly cost (AUD)

| Item | Demo / low traffic | Small team in real use |
|---|---|---|
| Cloud Run (scale to zero / 1 min instance, 1 vCPU, 512 MB) | $0 (free tier) | $15 to $40 |
| MongoDB Atlas | $0 (M0 free cluster) | ~$90 (M10 dedicated, backups) |
| Firebase Hosting | $0 | $0 to $5 |
| Gemini Flash (~1k summaries/month, ~2k tokens each) | $0 (free tier) | under $5 |
| Secret Manager, Artifact Registry, Logging | under $1 | $2 to $5 |
| **Total** | **about $0 to $5** | **about $110 to $150** |

The real-use column is dominated by the dedicated database; everything else stays small
because Cloud Run only bills while handling requests. Figures are estimates from public
list prices, not a quote.
