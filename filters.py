import re

from connectors.base import Job

KEYWORDS = ["android", "kotlin", "jetpack compose", "mobile developer"]

US_PHRASES = ["united states", "usa", "u.s."]
US_STATE_CODES = ["ca", "ny", "tx", "wa", "il", "ma", "az"]

# state codes must be their own word (bounded by non-letters) so ", ca" doesn't
# match inside "Toronto, Canada" — a real false positive seen against live Greenhouse data.
_STATE_CODE_RE = re.compile(
    r"\b(" + "|".join(US_STATE_CODES) + r")\b"
)

# titles implying more experience than targeted (roughly 0-4 years). "Senior" is
# deliberately not excluded — those postings can still fall within a 2-4 year band.
SENIORITY_EXCLUDE_TERMS = [
    "intern", "staff", "principal", "distinguished",
    "lead", "manager", "director", "head", "vp",
]
_SENIORITY_RE = re.compile(
    r"\b(" + "|".join(SENIORITY_EXCLUDE_TERMS) + r")\b", re.IGNORECASE
)


def is_relevant(job: Job) -> bool:
    text = job.title.lower()
    return any(k in text for k in KEYWORDS)


def is_within_experience_range(job: Job) -> bool:
    return not _SENIORITY_RE.search(job.title)


def is_us_location(job: Job) -> bool:
    if not job.location:
        return False  # exclude if location is missing/unclear — safer default than including
    loc = job.location.lower()
    if any(phrase in loc for phrase in US_PHRASES):
        return True
    return bool(_STATE_CODE_RE.search(loc))
