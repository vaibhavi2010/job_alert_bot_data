# Endpoint: https://www.amazon.jobs/en/search.json
# Public, unauthenticated, documented-by-behavior search API used by the
# amazon.jobs site itself. result_limit=100 returns all hits in one request
# (48 hits seen for base_query=android as of 2026-07 -- well under 100).
# Verified live (2026-07): fields id_icims, job_path, title, normalized_location,
# posted_date all present and stable.
import requests

from .base import HEADERS, Job

SEARCH_URL = "https://www.amazon.jobs/en/search.json"
BASE_URL = "https://www.amazon.jobs"


def normalize(raw: dict) -> Job:
    return Job(
        job_id=f"amazon_{raw['id_icims']}",
        title=raw["title"],
        company="Amazon",
        url=f"{BASE_URL}{raw['job_path']}",
        location=raw.get("normalized_location"),
        posted_date=raw.get("posted_date"),
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "android")
    r = requests.get(
        SEARCH_URL,
        params={
            "base_query": query,
            "normalized_country_code[]": "USA",
            "category[]": "software-development",
            "result_limit": 100,
        },
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    return [normalize(j) for j in r.json().get("jobs", [])]
