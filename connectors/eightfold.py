# Endpoint: https://{host}/api/pcsx/search?domain={domain}&query=...&start=N
# Eightfold's "PCSX" career-site search -- the same public, unauthenticated
# backend Microsoft's careers site uses (see microsoft.py). Used here for
# Qualcomm, whose branded careers.qualcomm.com host drops scripted
# connections, so the underlying qualcomm.eightfold.ai host is queried.
# Verified live (2026-10): data.positions[] with id/name/standardizedLocations
# ("City, ST, US")/postedTs (unix seconds)/positionUrl all present.
import time
from datetime import datetime, timezone

import requests

from .base import HEADERS, Job

MAX_RESULTS = 200  # safety cap across pagination, mirrors workday.py
MAX_RETRIES = 5
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _get_with_retry(url: str, params: dict) -> requests.Response:
    # The Eightfold host intermittently resets the TLS connection (observed
    # live against qualcomm.eightfold.ai, ~1 in 3 requests), so retry with
    # backoff; 429/5xx get the same treatment.
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        except requests.ConnectionError:
            if attempt == MAX_RETRIES - 1:
                raise
        else:
            if r.status_code not in RETRYABLE_STATUSES or attempt == MAX_RETRIES - 1:
                return r
        time.sleep(2**attempt)


def _location_str(raw: dict) -> str | None:
    locs = raw.get("standardizedLocations") or raw.get("locations") or []
    return locs[0] if locs else None


def _posted_date(posted_ts) -> str | None:
    if not posted_ts:
        return None
    return datetime.fromtimestamp(posted_ts, tz=timezone.utc).isoformat()


def normalize(raw: dict, company: str, id_prefix: str, base_url: str) -> Job:
    return Job(
        job_id=f"{id_prefix}_{raw['id']}",
        title=raw["name"],
        company=company,
        url=f"{base_url}{raw['positionUrl']}",
        location=_location_str(raw),
        posted_date=_posted_date(raw.get("postedTs")),
    )


def fetch(params: dict) -> list[Job]:
    host = params["host"]
    domain = params["domain"]
    company = params.get("name", domain)
    id_prefix = params.get("id_prefix", domain.split(".")[0])
    base_url = params.get("base_url", f"https://{host}")
    query = params.get("query", "data")

    jobs = []
    start = 0
    while start < MAX_RESULTS:
        r = _get_with_retry(
            f"https://{host}/api/pcsx/search",
            {"domain": domain, "query": query, "location": "", "start": start},
        )
        r.raise_for_status()
        positions = r.json().get("data", {}).get("positions", [])
        if not positions:
            break
        jobs.extend(normalize(p, company, id_prefix, base_url) for p in positions)
        start += len(positions)
    return jobs
