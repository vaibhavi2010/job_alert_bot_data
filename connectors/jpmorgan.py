# Endpoint: https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions
# JPMorgan Chase runs on Oracle Fusion Cloud Recruiting ("Candidate
# Experience"), not Workday or Greenhouse -- a distinct proprietary ATS.
# Found by inspecting network requests on careers.jpmorgan.com's search page;
# public, unauthenticated, GET-based. Verified live (2026-07): PostedDate,
# PrimaryLocation ("City, ST, Country"), and Title fields all present and stable.
from datetime import datetime, timezone

import requests

from .base import HEADERS, Job, strip_html

API_URL = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
SITE_NUMBER = "CX_1001"
PAGE_SIZE = 25
MAX_RESULTS = 200  # safety cap across pagination, mirrors workday.py


def _description(raw: dict) -> str | None:
    parts = [raw.get("ShortDescriptionStr"), raw.get("ExternalResponsibilitiesStr"), raw.get("ExternalQualificationsStr")]
    combined = " ".join(p for p in parts if p)
    return strip_html(combined) if combined else None


def _posted_date(raw: str | None) -> str | None:
    # PostedDate is a bare "YYYY-MM-DD" with no time/timezone component --
    # filters.is_recent() compares against a timezone-aware datetime, so a
    # naive datetime here raises TypeError. Anchor it to midnight UTC.
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def normalize(raw: dict) -> Job:
    return Job(
        job_id=f"jpmc_{raw['Id']}",
        title=raw["Title"],
        company="JPMorgan Chase",
        url=f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{SITE_NUMBER}/job/{raw['Id']}",
        location=raw.get("PrimaryLocation"),
        posted_date=_posted_date(raw.get("PostedDate")),
        description=_description(raw),
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "data")
    jobs = []
    offset = 0
    while offset < MAX_RESULTS:
        finder = (
            f"findReqs;siteNumber={SITE_NUMBER},facetsList=LOCATIONS,"
            f'limit={PAGE_SIZE},keyword="{query}",sortBy=POSTING_DATES_DESC,offset={offset}'
        )
        r = requests.get(
            API_URL,
            params={
                "onlyData": "true",
                "expand": "requisitionList.workLocation",
                "finder": finder,
            },
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        reqs = items[0].get("requisitionList", []) if items else []
        if not reqs:
            break
        jobs.extend(normalize(j) for j in reqs)
        offset += PAGE_SIZE
    return jobs
