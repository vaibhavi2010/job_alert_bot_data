# Endpoint: https://api.ashbyhq.com/posting-api/job-board/{slug}
# slug is visible in the company's jobs.ashbyhq.com/{slug} URL.
# Verified response shape (2026-07): {"jobs": [{"id", "title", "location",
# "jobUrl", "publishedAt", ...}]}
import requests

from .base import HEADERS, Job


def normalize(raw: dict, company: str) -> Job:
    # publishedAt is the original publication date and doesn't update if a
    # company reposts/refreshes the same listing (verified against Ashby's
    # own docs) -- same issue as Lever's createdAt. Gating is_recent() on it
    # would permanently exclude a job that's still actively open once it
    # crosses MAX_POSTING_AGE_DAYS, with no way back in. Leave posted_date
    # unset, as lever.py does, so state-based dedup is the only freshness
    # control that applies to these jobs.
    return Job(
        job_id=f"ashby_{raw['id']}",
        title=raw["title"],
        company=company,
        url=raw["jobUrl"],
        location=raw.get("location"),
        posted_date=None,
        description=raw.get("descriptionPlain"),
    )


def fetch(params: dict) -> list[Job]:
    slug = params["slug"]
    company = params.get("name", slug)
    r = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    return [normalize(j, company) for j in r.json().get("jobs", [])]
