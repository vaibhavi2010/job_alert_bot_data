# Endpoint: https://api.smartrecruiters.com/v1/companies/{slug}/postings
# SmartRecruiters' public Posting API (no auth). slug is visible in the
# company's jobs.smartrecruiters.com/{slug} URL (Renesas: RenesasElectronics).
# Verified live (2026-10): content[] with id/name/releasedDate (ISO)/
# location{city, region, country (lowercase ISO code), fullLocation}, and
# top-level totalFound. Filtered server-side to US postings via country=us.
import requests

from .base import HEADERS, Job

PAGE_SIZE = 100
MAX_RESULTS = 300  # safety cap across pagination, mirrors workday.py


def _location_str(raw: dict) -> str | None:
    loc = raw.get("location") or {}
    parts = [loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()]
    return ", ".join(p for p in parts if p) or loc.get("fullLocation")


def normalize(raw: dict, company: str, slug: str) -> Job:
    return Job(
        job_id=f"sr_{slug}_{raw['id']}",
        title=raw["name"],
        company=company,
        url=f"https://jobs.smartrecruiters.com/{slug}/{raw['id']}",
        location=_location_str(raw),
        posted_date=raw.get("releasedDate"),
    )


def fetch(params: dict) -> list[Job]:
    slug = params["slug"]
    company = params.get("name", slug)
    query = params.get("query", "data")

    jobs = []
    offset = 0
    total = None
    while total is None or offset < min(total, MAX_RESULTS):
        r = requests.get(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
            params={"q": query, "country": "us", "limit": PAGE_SIZE, "offset": offset},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        total = data.get("totalFound", 0)
        postings = data.get("content") or []
        if not postings:
            break
        jobs.extend(normalize(p, company, slug) for p in postings)
        offset += PAGE_SIZE
    return jobs
