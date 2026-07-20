# Job Alert Bot

A $0/month job-alert pipeline that polls company career pages for new Android/Kotlin and general software-engineering postings, pushes instant Discord alerts with built-in application-status tracking, and logs everything to a Google Sheet.

The goal isn't just "get notified" — it's to notify **fast enough to be among the first applicants** on a fresh posting. Every architectural decision below (polling cadence, freshness filtering, recency-first ordering) exists in service of that.

See [docs/job-alert-bot-implementation-doc.md](docs/job-alert-bot-implementation-doc.md) for the original design doc.

---

## Architecture

```
                    ┌──────────────────┐        ┌──────────────────┐
                    │  cron-job.org    │        │  cron-job.org    │
                    │  every 5-15 min  │        │  once daily 9PM  │
                    └────────┬─────────┘        └────────┬─────────┘
                             │ workflow_dispatch          │ workflow_dispatch
                             ▼                            ▼
                    ┌──────────────────┐        ┌──────────────────┐
                    │ job-watch.yml    │        │ eod-summary.yml  │
                    │ (GitHub Actions) │        │ (GitHub Actions) │
                    └────────┬─────────┘        └────────┬─────────┘
                             ▼                            ▼
                        main.py                    eod_summary.py
                             │                            │
        ┌────────────────────┼────────────────────┐       │
        ▼                    ▼                     ▼       ▼
  connectors/*.py       filters.py           notifier.py  state.py
  (35 companies:        (category,           (Discord     (secret
  Greenhouse, Ashby,     location,            REST API:    Gist —
  Workday, custom        experience,          post/poll/   dedup +
  Google/Amazon)         freshness,           archive/     status
                         recency sort)         sync)        store)
                                                    │
                                              sheets.py
                                              (Google Sheets
                                               tracking log)
```

**Per-run flow (`main.py`, every 5-15 min):**
1. Fetch open jobs from every enabled company in `companies.json` via its connector
2. Filter each job: relevant category (Android or generic SWE) → US-located → within target experience range → posted within the last `MAX_POSTING_AGE_DAYS`
3. Drop anything already tracked (dedup against the Gist-backed `state`)
4. If a category found more new jobs than `MAX_NEW_JOBS_PER_CATEGORY_PER_RUN`, sort newest-first and post only the top N — the rest drip in over later runs instead of flooding a channel
5. Post each surviving job to Discord with a native poll (`Applied` / `Skipped` / `Viewed`), log it to the Sheet, record it in `state`
6. For every still-open job, sync its poll (or legacy reaction) status; auto-archive anything whose voting window has closed — deleting the original message and reposting it in `#archived-jobs`
7. Persist `state` back to the Gist, no matter what happened above

**Daily flow (`eod_summary.py`, once at 9 PM local time):**
Reads `state`, tallies how many jobs were posted and applied to today, broken down by category, and posts the summary to `#eod-updates`.

---

## Key features

- **Five ATS integrations**: generic connectors for Greenhouse, Ashby, and Workday (add a company with just a config entry, no code) plus custom connectors for Google (HTML scrape — no public API exists) and Amazon (public JSON API)
- **Two-channel routing**: Android-specific postings and generic SWE postings go to separate Discord channels, never double-posted
- **Native Discord polls** for status tracking (`Applied`/`Skipped`/`Viewed`), auto-detected alongside a legacy emoji-reaction fallback for older messages
- **Freshness + recency-first ordering**: stale postings are discarded outright, and when a per-run cap does trigger, the newest postings always win the available slots
- **Auto-archiving**: jobs whose voting window closes unanswered are moved out of the live channels into `#archived-jobs`, keeping the working channels showing only actionable postings
- **Daily End of Day summary**: per-category posted/applied counts, once a day
- **Hardened against real failure modes**: retry-with-backoff on every external API, rollback on partial failures, state always persisted via `try/finally`, a circuit breaker against cold-start floods — all reproduced and fixed against live incidents during development, not theoretical
- **$0/month**: public GitHub repo (unlimited free Actions minutes), free Discord bot, free Gist storage, free Google Sheets API, free cron-job.org triggers

---

## Repo structure

```
job-alert-bot/
├── main.py                  # orchestrator: fetch -> filter -> post -> sync -> archive
├── eod_summary.py           # daily posted/applied summary
├── config.py                # env vars + companies.json loader
├── companies.json           # tracked companies (35, across 5 connector types)
├── filters.py                # category/location/experience/freshness/sort logic
├── notifier.py               # Discord REST: post, poll, archive-move, status sync
├── sheets.py                  # Google Sheets logging
├── state.py                   # Gist-backed dedup + status store
├── connectors/
│   ├── base.py                # shared Job dataclass
│   ├── greenhouse.py          # generic, slug-based
│   ├── ashby.py                # generic, slug-based
│   ├── workday.py              # generic, tenant/dc/site-based
│   ├── google.py                # custom: HTML scrape
│   └── amazon.py                 # custom: public JSON API
└── .github/workflows/
    ├── job-watch.yml            # every-5-15-min poller
    └── eod-summary.yml           # once-daily summary
```

---

## Local setup

```
pip install -r requirements.txt
cp .env.example .env   # fill in values, see below
python main.py
```

## One-time account setup

### 1. GitHub repo (public)
Create a **public** repo and push this code to it. Public = unlimited free GitHub Actions minutes.

### 2. Secret Gist (state store)
1. Go to https://gist.github.com/, create a **secret** gist named `state.json` with content `{}`.
2. Copy the gist ID from its URL (`https://gist.github.com/<user>/<GIST_ID>`).
3. Create a **Personal Access Token**: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained token, scope: `gist` (read/write).
4. Save as `GIST_TOKEN` and `GIST_ID`.

### 3. Discord bot
1. https://discord.com/developers/applications → New Application → Bot tab → Add Bot.
2. Under **Privileged Gateway Intents**, none are required (this bot only posts messages and reads poll results/reactions via REST — no gateway connection).
3. Copy the bot token → `DISCORD_BOT_TOKEN`.
4. OAuth2 → URL Generator → scope `bot`, permissions: `Send Messages`, `Read Message History`, `Add Reactions`. Open the generated URL to invite the bot to your server. (Bots can create polls and read poll results, but cannot vote on polls via the API — voting is a human-only client action, which is exactly the point.)
5. Create five text channels: `#job-alerts` (Android/Kotlin postings), `#dev-jobs` (generic software engineer/developer postings), `#bot-errors`, `#archived-jobs` (unvoted jobs move here after expiry), and `#eod-updates` (daily summary).
6. Enable Developer Mode in Discord (User Settings → Advanced), right-click each channel → Copy Channel ID → `DISCORD_CHANNEL_ID`, `DEV_JOBS_CHANNEL_ID`, `BOT_ERRORS_CHANNEL_ID`, `ARCHIVED_JOBS_CHANNEL_ID`, `EOD_UPDATES_CHANNEL_ID`.

### 4. Google Sheets
1. Google Cloud Console → new project → enable **Google Sheets API**.
2. IAM & Admin → Service Accounts → Create → generate a JSON key → this whole JSON (as one line/string) is `GOOGLE_SHEETS_CREDENTIALS`.
3. Create a Google Sheet, add header row: `Job ID | Title | Company | URL | Date Found | Status | Notes`.
4. Share the sheet with the service account's `client_email` (Editor access).
5. Copy the sheet ID from its URL → `GOOGLE_SHEET_ID`.

### 5. GitHub Actions secrets
Repo → Settings → Secrets and variables → Actions → add each of: `GIST_TOKEN`, `GIST_ID`, `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `DEV_JOBS_CHANNEL_ID`, `ARCHIVED_JOBS_CHANNEL_ID`, `EOD_UPDATES_CHANNEL_ID`, `BOT_ERRORS_CHANNEL_ID`, `GOOGLE_SHEETS_CREDENTIALS`, `GOOGLE_SHEET_ID`.

Once secrets are set, trigger `job-watch.yml` manually from the Actions tab (`workflow_dispatch`) to verify it runs end-to-end.

### 6. External cron triggers (cron-job.org)
Neither workflow listens for a `schedule:` trigger — GitHub's own scheduled-cron event is deprioritized/delayed under load (observed delays of 30-60+ minutes in practice), so an external service pings each workflow's dispatch API on its own schedule instead. This means **two** separate cron-job.org entries, one per workflow:

1. Create a **fine-grained PAT** scoped to only this repo, with **Actions: Read and write** permission.
2. Sign up free at https://cron-job.org/, create two cronjobs (same PAT works for both):
   - **[job-watch.yml](.github/workflows/job-watch.yml)** — `https://api.github.com/repos/<user>/<repo>/actions/workflows/job-watch.yml/dispatches`, every 5-15 minutes
   - **[eod-summary.yml](.github/workflows/eod-summary.yml)** — `https://api.github.com/repos/<user>/<repo>/actions/workflows/eod-summary.yml/dispatches`, once daily at 9 PM in your local timezone
   - Both: **POST**, headers `Authorization: Bearer <PAT>`, `Accept: application/vnd.github+json`, `Content-Type: application/json`, body `{"ref":"main"}`

Do **not** re-add a `schedule:` trigger to `job-watch.yml` alongside this — two trigger sources firing concurrently can race on the same Gist state (one run's newly-discovered job can get silently dropped if a second run reads/writes state at the same time).

---

## How it works

### Connectors (`connectors/*.py`)
Every connector exposes one function, `fetch(params) -> list[Job]`, returning the shared `Job` dataclass (`base.py`). Three connector *types* exist:

| Type | Companies need | Example |
|---|---|---|
| Greenhouse (generic) | just a `slug` | `boards-api.greenhouse.io/v1/boards/<slug>/jobs` |
| Ashby (generic) | just a `slug` | `api.ashbyhq.com/posting-api/job-board/<slug>` |
| Workday (generic) | `tenant`, `dc`, `site` | `<tenant>.<dc>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs` |
| Custom | one Python file | Google (HTML scrape), Amazon (public JSON API) |

A per-company `try/except` in `main.py` means one connector failing (site redesign, API change) never breaks the whole run.

### Filtering (`filters.py`)
Four checks combine — a job must pass all four:
- **Category** (`job_category()`): Android keywords (`android`, `kotlin`, `jetpack compose`, `mobile developer`) route to `#job-alerts`; generic SWE keywords (`software engineer`, `backend engineer`, etc.) route to `#dev-jobs`. Android takes priority — a title matching both never double-posts.
- **Location** (`is_us_location()`): handles multiple real-world formats seen across connectors — `"City, ST"`, `"City, State, Country"`, `"State - City"` (Workday), and explicitly excludes Canadian locations even when they coincidentally match a US state-code pattern (`"Toronto, ON, CA"`).
- **Experience range** (`is_within_experience_range()`): excludes `Intern`, `Staff`, `Principal`, `Distinguished`, `Lead`, `Manager`, `Director`, `Head`, `VP`. `Senior` is deliberately kept.
- **Freshness** (`is_recent()`): discards postings older than `MAX_POSTING_AGE_DAYS` (3). Jobs with no parseable `posted_date` (only Google's connector lacks one) skip this check and rely on dedup alone.

`sort_by_recency()` orders newest-first before the per-run cap applies, so a 10-minute-old posting never loses a slot to a 2-day-old one.

### Notification + status tracking (`notifier.py`)
- `post_job()` posts the job with a native Discord poll (`Applied`/`Skipped`/`Viewed`, single-select, open for `POLL_DURATION_HOURS`).
- `get_job_status()` auto-detects per message: reads poll results if present, falls back to a legacy emoji-reaction check (👀/✅/❌) for messages posted before polls existed.
- `post_archived_notice()` posts a plain (no-poll) message to `#archived-jobs` once a job's voting window has closed and gone unanswered; the original is deleted from its live channel.

### State (`state.py`)
A single JSON object in a secret Gist, keyed by `job_id`. Each record tracks title/company/url/category/location, Discord message/channel, Sheet row, status, and timestamps. This is the single source of truth for dedup and status — everything else (Discord, the Sheet) is a view into it.

### Sheets (`sheets.py`)
A mirror of `state` for easy browsing outside Discord — append on new job, update the Status column on status change.

---

## Design decisions & known limitations

- **This is a known-company allowlist, not a discovery engine.** It will never surface a company you haven't added. There's no free way to search "android" across every employer at once without a paid aggregator API.
- **Being a Workday enterprise (HCM/Financial) customer doesn't mean a company's public job board runs on Workday's recruiting module.** Verify by checking the actual careers URL before adding a `workday` entry.
- **Per-run cap ordering is recency-based, not literally FIFO by discovery**, but ties within the same fetch aren't further disambiguated — acceptable given the cap rarely triggers once a company's initial backlog has drained.
- **Legacy reaction-based messages never expire** (only polls do) — the auto-archive logic only applies to poll-based entries.
- **The 4-hour poll window is a hard tradeoff**: short enough to keep sync workload bounded and archiving fast, but a job you don't get to within 4 hours archives with no further reminder.

---

## Cost

| Component | Cost |
|---|---|
| GitHub Actions (public repo) | $0, unlimited |
| GitHub Gist | $0 |
| Discord bot | $0 |
| Google Sheets API | $0 (personal-scale usage) |
| cron-job.org | $0 |
| Company job-board APIs | $0 (public, no auth) |
| **Total** | **$0/month** |
