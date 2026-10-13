# Endpoint: POST https://www-api.ibm.com/search/api/v2
# The Elasticsearch-style search backend behind careers.ibm.com (public,
# unauthenticated). Found by running a search in a browser and inspecting the
# network request. Filtered server-side to United States postings whose title
# matches the query, newest first.
# Verified live (2026-10): hits.hits[]._source exposes title/url
# (careers.ibm.com/careers/JobDetail?jobId=N)/dcdate (YYYY-MM-DD)/
# field_keyword_19 (city, e.g. "Dallas, US", "Multiple Cities")/description
# (truncated snippet). The API rejects wildcard _source ("*"), so the fields
# are listed explicitly.
import re

import requests

from .base import HEADERS, Job

API_URL = "https://www-api.ibm.com/search/api/v2"
PAGE_SIZE = 100
MAX_RESULTS = 300  # safety cap across pagination, mirrors workday.py

_SOURCE_FIELDS = ["title", "url", "dcdate", "description", "field_keyword_05", "field_keyword_19"]
_JOB_ID_RE = re.compile(r"jobId=(\d+)")


def _location_str(src: dict) -> str | None:
    city = (src.get("field_keyword_19") or "").strip()
    if not city:
        return src.get("field_keyword_05")
    # "Dallas, US" already ends in the country; "Multiple Cities" doesn't.
    return city if city.upper().endswith(", US") else f"{city}, US"


def _posted_date(raw_date: str | None) -> str | None:
    # dcdate is a bare "YYYY-MM-DD"; make it a tz-aware ISO timestamp so
    # filters.py can compare it against the current time.
    return f"{raw_date}T00:00:00+00:00" if raw_date else None


def normalize(src: dict) -> Job | None:
    m = _JOB_ID_RE.search(src.get("url") or "")
    if not m:
        return None
    return Job(
        job_id=f"ibm_{m.group(1)}",
        title=src["title"],
        company="IBM",
        url=src["url"],
        location=_location_str(src),
        posted_date=_posted_date(src.get("dcdate")),
        description=src.get("description"),
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "data")

    jobs = []
    offset = 0
    total = None
    while total is None or offset < min(total, MAX_RESULTS):
        r = requests.post(
            API_URL,
            json={
                "appId": "careers",
                "scopes": ["careers2"],
                "query": {"bool": {"must": [
                    {"term": {"field_keyword_05": "United States"}},
                    {"match": {"title": query}},
                ]}},
                "size": PAGE_SIZE,
                "from": offset,
                "sort": [{"dcdate": "desc"}],
                "lang": "zz",
                "localeSelector": {},
                "_source": _SOURCE_FIELDS,
            },
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        hits = r.json().get("hits", {})
        total = (hits.get("total") or {}).get("value", 0)
        batch = hits.get("hits") or []
        if not batch:
            break
        jobs.extend(j for j in (normalize(h["_source"]) for h in batch) if j)
        offset += PAGE_SIZE
    return jobs
