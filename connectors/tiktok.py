# Endpoint: https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts
# TikTok/ByteDance's own careers site (lifeattiktok.com) backend -- path is
# literally under "/public/", and confirmed to require no auth, only a
# handful of plain headers matching what the site itself sends. Found by
# hooking window.fetch while running a search in a real browser session.
# Verified live (2026-07): city_info nests city -> state -> country as
# en_name fields; description/requirement are both plain text, no per-job
# follow-up request needed. No posted-date field is exposed, so posted_date
# is left unset (same as Google's connector) and dedup via state is the
# only freshness control.
import requests

from .base import Job

API_URL = "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts"
PAGE_SIZE = 50
MAX_RESULTS = 300  # safety cap across pagination, mirrors workday.py

HEADERS = {
    "Content-Type": "application/json",
    "accept-language": "en-US",
    "origin": "https://lifeattiktok.com",
    "website-path": "tiktok",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _location_str(raw: dict) -> str | None:
    city = raw.get("city_info") or {}
    state = city.get("parent") or {}
    country = state.get("parent") or {}
    parts = [city.get("en_name"), state.get("en_name"), country.get("en_name")]
    return ", ".join(p for p in parts if p) or None


def _description(raw: dict) -> str | None:
    parts = [raw.get("description"), raw.get("requirement")]
    combined = "\n".join(p for p in parts if p)
    return combined or None


def normalize(raw: dict) -> Job:
    return Job(
        job_id=f"tiktok_{raw['id']}",
        title=raw["title"],
        company="TikTok",
        url=f"https://lifeattiktok.com/search/{raw['id']}",
        location=_location_str(raw),
        posted_date=None,
        description=_description(raw),
    )


def fetch(params: dict) -> list[Job]:
    query = params.get("query", "data")
    jobs = []
    offset = 0
    while offset < MAX_RESULTS:
        body = {
            "recruitment_id_list": [],
            "job_category_id_list": [],
            "subject_id_list": [],
            "location_code_list": [],
            "keyword": query,
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        r = requests.post(API_URL, json=body, headers=HEADERS, timeout=15)
        r.raise_for_status()
        payload = r.json()
        if payload.get("code") != 0:
            break
        posts = (payload.get("data") or {}).get("job_post_list") or []
        if not posts:
            break
        jobs.extend(normalize(p) for p in posts)
        offset += PAGE_SIZE
    return jobs
