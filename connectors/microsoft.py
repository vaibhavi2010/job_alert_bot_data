# Endpoint: https://apply.careers.microsoft.com/api/pcsx/search
# Microsoft's actual careers/application backend lives on a separate
# "apply.careers.microsoft.com" host (a Phenom-based ATS), distinct from the
# careers.microsoft.com marketing shell. Found by running a search in a real
# browser and inspecting network requests; public and unauthenticated for
# read-only search (the reCAPTCHA on the page only guards the apply flow).
# Verified live (2026-07): standardizedLocations ("City, ST, US" / "US"),
# postedTs (unix seconds), and positionUrl fields all present and stable.
# No description field is exposed by the list endpoint (a separate per-job
# position_details call would be needed), so description is left unset.
from datetime import datetime, timezone

import requests

from .base import HEADERS, Job

API_URL = "https://apply.careers.microsoft.com/api/pcsx/search"
PAGE_SIZE = 10
MAX_RESULTS = 200  # safety cap across pagination, mirrors workday.py


def _location_str(raw: dict) -> str | None:
    locs = raw.get("standardizedLocations") or raw.get("locations") or []
    return locs[0] if locs else None


def _posted_date(posted_ts) -> str | None:
    if not posted_ts:
        return None
    return datetime.fromtimestamp(posted_ts, tz=timezone.utc).isoformat()


def normalize(raw: dict) -> Job:
    return Job(
        job_id=f"msft_{raw['id']}",
        title=raw["name"],
        company="Microsoft",
        url=f"https://apply.careers.microsoft.com{raw['positionUrl']}",
        location=_location_str(raw),
        posted_date=_posted_date(raw.get("postedTs")),
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "data")
    jobs = []
    start = 0
    while start < MAX_RESULTS:
        r = requests.get(
            API_URL,
            params={"domain": "microsoft.com", "query": query, "location": "", "start": start},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        positions = r.json().get("data", {}).get("positions", [])
        if not positions:
            break
        jobs.extend(normalize(p) for p in positions)
        start += PAGE_SIZE
    return jobs
