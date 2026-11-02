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
| Backend API | **Cloud Run** | Runs the existing Dockerfile unchanged, can scale to zero when idle (no minimum instance), HTTPS by default. |
| Container images | **Artifact Registry** | Where Cloud Build pushes images for Cloud Run. |
| Build | **Cloud Build** | Builds the backend image from the repo on each push to `main`. |
| Database | **MongoDB Atlas on GCP** (Melbourne/Sydney region) | GCP has no native MongoDB; Atlas runs it inside Google's network, near users. |
| Secrets | **Secret Manager** | MongoDB URI injected into Cloud Run as an env var; never in the repo. (Vertex AI needs no API key.) |
| AI | **Gemini on Vertex AI** | Same cloud, regional processing, service-account auth; see below. |
| Logs / alerts | **Cloud Logging + Cloud Monitoring** | Cloud Run logs by default; alert on 5xx rate and on failed-summary log lines. |
| Spend guard | **Cloud Billing budget alert** | Email at 50% / 90% of a monthly budget. |

## Gemini: billing and data handling are separate from hosting

Hosting on GCP doesn't by itself decide how candidate data is handled by the model.

- **Local development** uses a Gemini API key from Google AI Studio. It's billed under the Gemini
  API's own pricing (free tier or pay-as-you-go), not as Cloud Run usage. Under Google's terms at
  the time of writing, free-tier prompts may be used to improve Google's products, so **no real
  candidate data should go through a free-tier key**.
- **Production** should call Gemini through **Vertex AI** in an Australian region instead: billed
  to the GCP project, authenticated with Cloud Run's service account (no API key to leak), covered
  by Google Cloud's data terms (customer data not used for training), and processed in-region.
  The code change is confined to `backend/app/ai/gemini.py`, since the SDK supports both.
- Resumes contain personal information, so prompts and responses aren't written to logs; only
  failure reasons are.

## Things that change for a public deployment

- **No authentication is in scope**, so a public URL means anyone could read candidate data
  and trigger Gemini calls. Before real use: put it behind **Identity-Aware Proxy** (Google
  sign-in for staff only), which needs no code changes.
- **Rate-limit the AI.** Cap Gemini usage with an API quota in the project, and a Cloud Run
  max-instances limit (e.g. 3) so traffic spikes can't run up the bill.
- **CORS:** set `CORS_ORIGINS` to the Firebase Hosting domain only.
- **Data residency:** Australian regions for Cloud Run and Atlas, since candidate data is
  personal information.

## Estimated monthly cost

**These are indicative AUD estimates, not a quote.** They're built from USD list prices on the
providers' pricing pages (checked 2 Nov 2026) at an assumed **1 USD ≈ 1.50 AUD**, and will vary with
region, exchange rate, actual usage, and any later price changes.

Assumptions: Australian regions; ~1,500 input and ~500 output tokens per summary; ~200 ms of CPU per
API request; Cloud Run with no minimum instance unless stated; prices before tax.

### Unit prices used (Australian regions)

| Service | List price | Free allowance |
|---|---|---|
| Gemini 3.5 Flash on Vertex AI, regional endpoint | $1.65 per 1M input tokens, $9.90 per 1M output tokens (output includes reasoning tokens; global endpoint is $1.50 / $9.00) | none |
| Cloud Run, Sydney/Melbourne (Tier 2), request-based | $0.0000336 per vCPU-second and $0.0000035 per GiB-second while handling requests; idle min-instance $0.0000035 per vCPU-s and per GiB-s; $0.40 per 1M requests | 180,000 vCPU-s, 360,000 GiB-s, 2M requests per month (valued at Tier 1 prices, so ~128,000 vCPU-s in Tier 2) |
| MongoDB Atlas | M0: free, 512 MB. M10: $0.08 per hour ("starts at $56.94/month") | M0 |
| Firebase Hosting, Secret Manager, Artifact Registry, Cloud Build, Logging | cents at this scale | mostly covered by free tiers |

### The AI cost per summary

A typical resume plus the system instruction is about **1,500 input tokens**; the JSON summary
plus brief reasoning is about **500 output tokens**:

- 1,500 × $1.65 / 1M = $0.0025
- 500 × $9.90 / 1M = $0.0050
- **≈ $0.0074 per summary (about 1 cent AUD)**

Worst case, a resume at the 20,000-character cap (~5,000 tokens) with the 2,048-token output cap:
5,000 × $1.65/1M + 2,048 × $9.90/1M ≈ **$0.029**. The input and output caps bound any single call.

### Monthly totals

| Item | Demo (100 summaries) | Small team (~10 recruiters, 1,000 summaries) |
|---|---|---|
| Gemini on Vertex AI | 100 × $0.0074 ≈ **$0.74** | 1,000 × $0.0074 ≈ **$7.40** |
| Cloud Run, scale to zero | **$0**: ~200 ms per request, so even 60,000 requests ≈ 12,000 vCPU-s, inside the free allowance | **$0 to $5** |
| MongoDB Atlas | **$0** (M0) | **~$57 to $58** (M10, $0.08/h × ~730 h); backups extra |
| Firebase Hosting, secrets, registry, builds, logs | **under $1** | **$1 to $3** |
| **Total (USD)** | **about $1 to $2** | **about $66 to $74** |
| **Total (AUD)** | **about $2 to $3** | **about $100 to $110** |

**Optional:** one always-warm Cloud Run instance (no cold starts), billed at the idle min-instance
rate while not serving: 1 vCPU × 2,592,000 s × $0.0000035 ≈ $9.07, plus 0.5 GiB × 2,592,000 s ×
$0.0000035 ≈ $4.54, so about **+$14 USD (≈ +$21 AUD) a month**. Cheap enough to turn on if cold
starts bother recruiters.

**What drives the cost:** the dedicated database, not the AI. Even 10,000 summaries a month is about
$74 USD of Gemini. A budget alert at 50% and 90% of $150 AUD/month catches surprises.

Atlas's M10 price is its headline rate: the Sydney region may be slightly higher (not confirmed),
and cloud backups and data transfer are billed on top. With a minimum Cloud Run instance, the
service is billed for idle time too, not only while handling requests (the optional row above).
