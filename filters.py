import re

from connectors.base import Job

ANDROID_KEYWORDS = ["android", "kotlin", "jetpack compose", "mobile developer"]
SWE_KEYWORDS = [
    "software engineer", "software developer", "backend engineer",
    "backend developer", "full stack engineer", "full stack developer",
    "frontend engineer", "frontend developer", "software development engineer",
]

US_PHRASES = ["united states", "usa", "u.s."]
US_STATE_CODES = ["ca", "ny", "tx", "wa", "il", "ma", "az"]
CANADA_PHRASES = ["canada"]
CANADIAN_PROVINCE_CODES = ["on", "bc", "qc", "ab", "mb", "sk", "ns", "nb", "pe", "nl", "yt", "nt", "nu"]

# state codes must be their own word (bounded by non-letters) so ", ca" doesn't
# match inside "Toronto, Canada" — a real false positive seen against live Greenhouse data.
_STATE_CODE_RE = re.compile(
    r"\b(" + "|".join(US_STATE_CODES) + r")\b"
)

# Greenhouse formats Canadian listings as "City, Province, CA" where CA is
# Canada's ISO country code, not California — e.g. "Toronto, ON, CA". Detect
# a Canadian province code immediately followed by ", CA" and treat that as
# Canada, overriding the coincidental California state-code match.
_CANADA_PROVINCE_CA_RE = re.compile(
    r"\b(" + "|".join(CANADIAN_PROVINCE_CODES) + r")\s*,\s*ca\b"
)

# titles implying more experience than targeted (roughly 0-4 years). "Senior" is
# deliberately not excluded — those postings can still fall within a 2-4 year band.
# "intern" is handled as intern(ship)? since a trailing \b after "intern" alone
# doesn't match "Internship" (word boundary fails mid-word) — a real miss seen
# against live data ("Software Engineer Internship, Android" slipped through).
SENIORITY_EXCLUDE_TERMS = [
    "staff", "principal", "distinguished",
    "lead", "manager", "director", "head", "vp",
]
_SENIORITY_RE = re.compile(
    r"\b(intern(ship)?|" + "|".join(SENIORITY_EXCLUDE_TERMS) + r")\b", re.IGNORECASE
)


def job_category(job: Job) -> str | None:
    """Returns 'android', 'swe', or None. Android takes priority over the
    broader SWE keyword set so a title like "Software Engineer, Android"
    routes only to the Android channel, not both."""
    text = job.title.lower()
    if any(k in text for k in ANDROID_KEYWORDS):
        return "android"
    if any(k in text for k in SWE_KEYWORDS):
        return "swe"
    return None


def is_within_experience_range(job: Job) -> bool:
    return not _SENIORITY_RE.search(job.title)


def is_us_location(job: Job) -> bool:
    if not job.location:
        return False  # exclude if location is missing/unclear — safer default than including
    loc = job.location.lower()
    if any(phrase in loc for phrase in CANADA_PHRASES) or _CANADA_PROVINCE_CA_RE.search(loc):
        return False
    if any(phrase in loc for phrase in US_PHRASES):
        return True
    return bool(_STATE_CODE_RE.search(loc))
