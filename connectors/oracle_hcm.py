# Endpoint: https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
# Oracle Cloud (HCM) Recruiting's public candidate-experience REST API, used
# by the career-site frontend (Texas Instruments: host edbz.fa.us2.oraclecloud.com,
# site CX). host/site are visible in the careers page's own network calls.
# Verified live (2026-10): items[0].requisitionList[] with Id/Title/PostedDate
# (YYYY-MM-DD)/PrimaryLocation ("Dallas, TX, United States"), and
# items[0].TotalJobsCount on every page.
import requests

from .base import HEADERS, Job

PAGE_SIZE = 25
MAX_RESULTS = 200  # safety cap across pagination, mirrors workday.py


def _posted_date(raw_date: str | None) -> str | None:
    # PostedDate is a bare "YYYY-MM-DD"; make it a tz-aware ISO timestamp so
    # filters.py can compare it against the current time.
    return f"{raw_date}T00:00:00+00:00" if raw_date else None


def normalize(raw: dict, company: str, id_prefix: str, job_url_tmpl: str) -> Job:
    return Job(
        job_id=f"{id_prefix}_{raw['Id']}",
        title=raw["Title"],
        company=company,
        url=job_url_tmpl.format(id=raw["Id"]),
        location=raw.get("PrimaryLocation"),
        posted_date=_posted_date(raw.get("PostedDate")),
    )


def fetch(params: dict) -> list[Job]:
    host = params["host"]
    site = params["site"]
    company = params.get("name", site)
    id_prefix = params.get("id_prefix", host.split(".")[0])
    # Branded careers hosts (careers.ti.com) front the same Oracle site; fall
    # back to Oracle's own candidate-experience URL if none is configured.
    job_url_tmpl = params.get(
        "job_url",
        f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{{id}}",
    )
    query = params.get("query", "data")
    api_url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

    jobs = []
    offset = 0
    total = None
    while total is None or offset < min(total, MAX_RESULTS):
        r = requests.get(
            api_url,
            params={
                "onlyData": "true",
                "expand": "requisitionList.secondaryLocations",
                "finder": (
                    f"findReqs;siteNumber={site},limit={PAGE_SIZE},offset={offset},"
                    f"keyword={query},sortBy=POSTING_DATES_DESC"
                ),
            },
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("items") or []
        if not items:
            break
        if total is None:
            total = items[0].get("TotalJobsCount", 0)
        postings = items[0].get("requisitionList") or []
        if not postings:
            break
        jobs.extend(normalize(p, company, id_prefix, job_url_tmpl) for p in postings)
        offset += PAGE_SIZE
    return jobs
