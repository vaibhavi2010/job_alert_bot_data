# Endpoint: https://api-higher.gs.com/gateway/api/v1/graphql (POST)
# Public, unauthenticated GraphQL gateway behind Goldman Sachs' own careers
# site (higher.gs.com) -- found by hooking window.fetch while running a
# search in a real browser session; no cookies or auth headers required.
# Verified live (2026-07): roleSearch.items exposes roleId/jobTitle/
# corporateTitle/jobFunction/locations/externalSource.sourceId. No posted-
# date field is exposed by this query, so posted_date is left unset (same
# as Google's connector) and dedup via state is the only freshness control.
import requests

from .base import Job

API_URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
PAGE_SIZE = 100
MAX_RESULTS = 500  # safety cap across pagination, mirrors workday.py

_QUERY = """query GetRoles($searchQueryInput: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $searchQueryInput) {
    totalCount
    items {
      roleId
      corporateTitle
      jobTitle
      jobFunction
      locations { primary state country city __typename }
      status
      division
      __typename
    }
    __typename
  }
}"""


def _location_str(job: dict) -> str | None:
    locs = job.get("locations") or []
    primary = next((l for l in locs if l.get("primary")), locs[0] if locs else None)
    if not primary:
        return None
    parts = [primary.get("city"), primary.get("state"), primary.get("country")]
    return ", ".join(p for p in parts if p) or None


def normalize(raw: dict) -> Job:
    # roleId is "<sourceId>_GS_<TRACK>" (e.g. "149322_GS_MID_CAREER"); the
    # public role page is keyed on the bare sourceId, confirmed against live data.
    source_id = raw["roleId"].split("_")[0]
    return Job(
        job_id=f"gs_{raw['roleId']}",
        title=raw["jobTitle"],
        company="Goldman Sachs",
        url=f"https://higher.gs.com/roles/{source_id}",
        location=_location_str(raw),
        posted_date=None,
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "data")
    jobs = []
    page = 0
    total = None
    while total is None or page * PAGE_SIZE < min(total, MAX_RESULTS):
        body = {
            "operationName": "GetRoles",
            "variables": {
                "searchQueryInput": {
                    "page": {"pageSize": PAGE_SIZE, "pageNumber": page},
                    "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                    "filters": [],
                    "experiences": ["EARLY_CAREER", "PROFESSIONAL"],
                    "searchTerm": query,
                }
            },
            "query": _QUERY,
        }
        r = requests.post(
            API_URL, json=body,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()["data"]["roleSearch"]
        total = result["totalCount"]
        items = result.get("items", [])
        if not items:
            break
        jobs.extend(normalize(it) for it in items)
        page += 1
    return jobs
