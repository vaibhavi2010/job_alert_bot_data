import re
from dataclasses import dataclass


@dataclass
class Job:
    job_id: str          # unique, prefixed per company e.g. "google_123456"
    title: str
    company: str
    url: str
    location: str | None
    posted_date: str | None
    description: str | None = None  # plain text; None where a connector can't get it cheaply


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(raw: str | None) -> str | None:
    """HTML -> plain text, for connectors whose description field is HTML
    (Greenhouse's content, Amazon's description/qualifications fields)."""
    if not raw:
        return None
    return _TAG_RE.sub(" ", raw).strip() or None
