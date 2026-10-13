# Endpoint: https://{subdomain}.icims.com/jobs/search?ss=1&in_iframe=1&pr=N
# iCIMS career portals server-render the job list as HTML (no JSON API for
# the public search), so this scrapes the job cards. subdomain is the
# portal host's first label (MaxLinear: careersus-maxlinear). Fetches the
# full job list rather than a keyword search -- small portals only; the
# DA/DE/DS/SWE title filters do the narrowing downstream.
# Verified live (2026-10): <li class="iCIMS_JobCardItem"> cards each carry the
# job link (/jobs/{id}/{slug}/job), an <h3> title, a location like
# "US-CA-San Jose", and a description snippet. No posting date is exposed on
# the list, so posted_date is left unset (state-based dedup is the only
# freshness control, as with Lever and Google).
import html
import re

import requests

from .base import HEADERS, Job, strip_html

MAX_PAGES = 10  # safety cap across pagination

_CARD_RE = re.compile(r'<li class="iCIMS_JobCardItem">(.*?)</li>', re.DOTALL)
_LINK_RE = re.compile(r'href="(https://[^"]+/jobs/(\d+)/[^"]*?/job)[^"]*"')
_TITLE_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.DOTALL)
_LOCATION_RE = re.compile(r'Job Locations</span>\s*<span[^>]*>(.*?)</span>', re.DOTALL)
_DESC_RE = re.compile(r'<div class="col-xs-12 description">(.*?)</div>', re.DOTALL)


def _location_str(raw: str | None) -> str | None:
    # iCIMS format is "CC-ST-City" (e.g. "US-CA-San Jose") -> "San Jose, CA, US".
    if not raw:
        return None
    raw = html.unescape(raw).strip()
    parts = raw.split("-", 2)
    if len(parts) == 3:
        country, state, city = parts
        return ", ".join(p.strip() for p in (city, state, country) if p.strip())
    return raw


def _text(raw: str) -> str:
    return html.unescape(strip_html(raw) or "").strip()


def normalize(card: str, company: str, subdomain: str) -> Job | None:
    link = _LINK_RE.search(card)
    title = _TITLE_RE.search(card)
    if not link or not title:
        return None
    location = _LOCATION_RE.search(card)
    desc = _DESC_RE.search(card)
    return Job(
        job_id=f"icims_{subdomain}_{link.group(2)}",
        title=_text(title.group(1)),
        company=company,
        url=link.group(1),
        location=_location_str(_text(location.group(1))) if location else None,
        posted_date=None,
        description=_text(desc.group(1)) if desc else None,
    )


def fetch(params: dict) -> list[Job]:
    subdomain = params["subdomain"]
    company = params.get("name", subdomain)

    jobs: dict[str, Job] = {}
    for page in range(MAX_PAGES):
        r = requests.get(
            f"https://{subdomain}.icims.com/jobs/search",
            params={"ss": 1, "in_iframe": 1, "pr": page},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        cards = _CARD_RE.findall(r.text)
        new = 0
        for card in cards:
            job = normalize(card, company, subdomain)
            if job and job.job_id not in jobs:
                jobs[job.job_id] = job
                new += 1
        if new == 0:  # empty page, or iCIMS echoing the last page past the end
            break
    return list(jobs.values())
