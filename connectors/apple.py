# Endpoint: https://jobs.apple.com/en-us/search (GET, HTML)
# Apple's careers site server-renders search results directly into the page
# -- no separate XHR/API call exists, so this scrapes the embedded React
# Router hydration blob (window.__staticRouterHydrationData), which is a
# JSON-escaped JSON string (hence the double json.loads). Plain unauthenticated
# GET, no bot-detection challenge encountered (unlike Tesla's Akamai-gated
# careers site, which was investigated and skipped for exactly that reason).
# Verified live (2026-08): loaderData.search.searchResults exposes id/
# positionId/postingTitle/postDateInGMT (ISO)/locations/jobSummary/
# transformedPostingTitle/team.teamCode, all stable.
import json
import re

import requests

from .base import HEADERS, Job

SEARCH_URL = "https://jobs.apple.com/en-us/search"
PAGE_SIZE = 20
MAX_RESULTS = 200  # safety cap across pagination, mirrors workday.py

_HYDRATION_RE = re.compile(
    r"window\.__staticRouterHydrationData = JSON\.parse\((\".*?\")\);", re.DOTALL
)


def _location_str(raw: dict) -> str | None:
    locs = raw.get("locations") or []
    if not locs:
        return None
    primary = locs[0]
    parts = [primary.get("name") or primary.get("city"), primary.get("stateProvince"), primary.get("countryName")]
    return ", ".join(p for p in parts if p) or None


def normalize(raw: dict) -> Job:
    team_code = (raw.get("team") or {}).get("teamCode", "")
    return Job(
        job_id=f"apple_{raw['id']}",
        title=raw["postingTitle"],
        company="Apple",
        url=f"https://jobs.apple.com/en-us/details/{raw['id']}/{raw['transformedPostingTitle']}?team={team_code}",
        location=_location_str(raw),
        posted_date=raw.get("postDateInGMT"),
        description=raw.get("jobSummary"),
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "data")
    jobs = []
    page = 1
    while (page - 1) * PAGE_SIZE < MAX_RESULTS:
        r = requests.get(
            SEARCH_URL,
            params={"search": query, "location": "united-states-USA", "page": page},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        m = _HYDRATION_RE.search(r.text)
        if not m:
            break
        data = json.loads(json.loads(m.group(1)))
        results = data.get("loaderData", {}).get("search", {}).get("searchResults", [])
        if not results:
            break
        jobs.extend(normalize(j) for j in results)
        page += 1
    return jobs
