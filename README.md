# Job Alert Bot

Polls company career pages for new Android/Kotlin jobs, posts to Discord, logs to Google Sheets. See [docs/job-alert-bot-implementation-doc.md](docs/job-alert-bot-implementation-doc.md) for full architecture.

## Local setup

```
pip install -r requirements.txt
cp .env.example .env   # fill in values, see below
python main.py
```

## One-time account setup

### 1. GitHub repo (public)
Create a **public** repo (e.g. `job-alert-bot`) and push this code to it. Public = unlimited free GitHub Actions minutes.

### 2. Secret Gist (state store)
1. Go to https://gist.github.com/, create a **secret** gist named `state.json` with content `{}`.
2. Copy the gist ID from its URL (`https://gist.github.com/<user>/<GIST_ID>`).
3. Create a **Personal Access Token**: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained token, scope: `gist` (read/write).
4. Save as `GIST_TOKEN` and `GIST_ID`.

### 3. Discord bot
1. https://discord.com/developers/applications → New Application → Bot tab → Add Bot.
2. Under **Privileged Gateway Intents**, none are required for this bot (it only posts messages and reads poll results/reactions via REST — no gateway connection).
3. Copy the bot token → `DISCORD_BOT_TOKEN`.
4. OAuth2 → URL Generator → scope `bot`, permissions: `Send Messages`, `Read Message History`, `Add Reactions`. Open the generated URL to invite the bot to your server. (Note: bots can create polls and read poll results, but cannot vote on polls via the API — voting is a human-only client action, which is exactly what this is for.)
5. Create three text channels: `#job-alerts` (Android/Kotlin postings), `#dev-jobs` (generic software engineer/developer postings), and `#bot-errors`.
6. Enable Developer Mode in Discord (User Settings → Advanced), right-click each channel → Copy Channel ID → `DISCORD_CHANNEL_ID`, `DEV_JOBS_CHANNEL_ID`, and `BOT_ERRORS_CHANNEL_ID`.

### 4. Google Sheets
1. Google Cloud Console → new project → enable **Google Sheets API**.
2. IAM & Admin → Service Accounts → Create → generate a JSON key → this whole JSON (as one line/string) is `GOOGLE_SHEETS_CREDENTIALS`.
3. Create a Google Sheet, add header row: `Job ID | Title | Company | URL | Date Found | Status | Notes`.
4. Share the sheet with the service account's `client_email` (Editor access).
5. Copy the sheet ID from its URL → `GOOGLE_SHEET_ID`.

### 5. GitHub Actions secrets
Repo → Settings → Secrets and variables → Actions → add each of: `GIST_TOKEN`, `GIST_ID`, `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `DEV_JOBS_CHANNEL_ID`, `BOT_ERRORS_CHANNEL_ID`, `GOOGLE_SHEETS_CREDENTIALS`, `GOOGLE_SHEET_ID`.

Once secrets are set, trigger the workflow manually from the Actions tab (`workflow_dispatch`) to verify it runs end-to-end.

### 6. External cron trigger (cron-job.org)
The workflow only listens for `workflow_dispatch` — there's no `schedule:` trigger in [job-watch.yml](.github/workflows/job-watch.yml). GitHub's own scheduled-cron event is deprioritized/delayed under load (observed delays of 30-60+ minutes in practice), so an external service pings the dispatch API on a fixed interval instead:

1. Create a **fine-grained PAT** (Settings → Developer settings → Personal access tokens → Fine-grained tokens) scoped to only this repo, with **Actions: Read and write** permission.
2. Sign up free at https://cron-job.org/, create a cronjob:
   - **URL**: `https://api.github.com/repos/<user>/<repo>/actions/workflows/job-watch.yml/dispatches`
   - **Request method**: `POST`
   - **Headers**: `Authorization: Bearer <PAT>`, `Accept: application/vnd.github+json`, `Content-Type: application/json`
   - **Request body**: `{"ref":"main"}`
   - **Schedule**: whatever interval you want (e.g. every 5-15 minutes)

Do **not** re-add a `schedule:` trigger to the workflow alongside this — two trigger sources firing concurrently can race on the same Gist state (one run's newly-discovered job can get silently dropped if a second run reads/writes state at the same time).

## Filtering & channel routing
Four filters combine in `main.py` — a job must pass all four to get posted (see [filters.py](filters.py)):
- **Keyword/category** (`job_category()`): title must contain an Android keyword (`android`, `kotlin`, `jetpack compose`, `mobile developer`) — routed to `#job-alerts` — or a generic SWE keyword (`software engineer`, `software developer`, `backend engineer`, etc.) — routed to `#dev-jobs`. Android takes priority, so a title like "Software Engineer, Android" only posts once, to `#job-alerts`, not both channels.
- **Location**: must resolve to a US location (phrase match like "United States", or a bounded 2-letter state code — extend `US_STATE_CODES` as you see real-data gaps)
- **Experience range**: titles signaling more senior scope are excluded — `Intern`, `Staff`, `Principal`, `Distinguished`, `Lead`, `Manager`, `Director`, `Head`, `VP`. `Senior` is deliberately *not* excluded since those roles can still fall in a 2-4 year band.
- **Freshness** (`is_recent()`): postings older than `MAX_POSTING_AGE_DAYS` (3) are discarded, so an old backlog can't crowd out fresh postings under the per-run cap (see below). Jobs with no parseable `posted_date` — currently only Google's connector, which has no date field to scrape — skip this check entirely and rely on dedup alone.

Per-company `discord_channel_id` (in `companies.json`) overrides category-based routing if set.

## Status tracking (Discord polls)
Each posted job includes a native Discord poll — `Applied` / `Skipped` / `Viewed`, single-select, open for 3 days. Voting is a human-only client action; bots can create polls and read results but cannot vote via the API. Status sync (`notifier.get_job_status`) auto-detects per message: reads poll results if the message has one, otherwise falls back to a legacy emoji-reaction check (👀/✅/❌) for messages posted before polls were introduced — both formats keep working indefinitely, no migration needed.

## Per-run posting cap
`MAX_NEW_JOBS_PER_CATEGORY_PER_RUN` (20, in `main.py`) is a circuit breaker: if a single run finds more new jobs than this in one category — e.g. a newly-added company's entire backlog matching on its first run — only the first N post, and the rest stay untracked so they drip in over subsequent runs instead of flooding a channel. Combined with the freshness filter, backlog jobs are unlikely to ever reach this cap in the first place.

## Adding companies
`companies.json` ships pre-seeded with 32 companies across Greenhouse and Ashby.
- **Greenhouse/Ashby company**: add one entry with `connector` set to `"greenhouse"` or `"ashby"` and the right `slug` (visible in the company's `boards.greenhouse.io/<slug>` or `jobs.ashbyhq.com/<slug>` URL) — no code needed. Validate a slug works before adding it, e.g. `curl https://boards-api.greenhouse.io/v1/boards/<slug>/jobs`.
- **Custom career site** (e.g. Google, Amazon): write a new `connectors/<name>.py` with a `fetch(params) -> list[Job]` function, register it in `connectors/__init__.py`'s `CONNECTORS` dict, add an entry to `companies.json`.
- This is inherently a **known-company allowlist**, not a discovery engine — it will never surface a company you haven't added. There's no free way to search "android" across every employer at once without a paid aggregator API (Adzuna's free tier is the closest option if that's ever wanted).
