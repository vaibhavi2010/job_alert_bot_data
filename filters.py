import re
from datetime import datetime, timedelta, timezone

from connectors.base import Job

MAX_POSTING_AGE_DAYS = 3

DATA_ENGINEER_KEYWORDS = [
    "data engineer", "data engineering", "analytics engineer",
    "etl engineer", "big data engineer",
]
DATA_ANALYST_KEYWORDS = [
    "data analyst", "analytics analyst", "business intelligence analyst",
    "bi analyst", "reporting analyst", "insights analyst",
]
DATA_SCIENTIST_KEYWORDS = ["data scientist", "data science"]

# generic-titled early-career postings (e.g. "Software Engineer, University
# Grad Program") don't name a track in the title -- the actual specialization
# only shows up in the description. Scoped narrowly to these new-grad signals
# so an ordinary SWE posting that happens to mention "data" in passing isn't
# swept in by a description-only match.
_NEW_GRAD_TITLE_RE = re.compile(
    r"\b(new grad|university grad|recent graduate|early career|rotational program|grad program)\b"
    r"|class of 20\d\d",
    re.IGNORECASE,
)

US_PHRASES = ["united states", "usa", "u.s."]
US_STATE_CODES = ["ca", "ny", "tx", "wa", "il", "ma", "az"]
# Workday returns full state names in "State - City" order (e.g. "California -
# San Francisco"), not the "City, ST" comma format Greenhouse/Ashby/Amazon use
# -- a real miss found testing the Workday connector against live Salesforce
# data. Known caveat: "Georgia" collides with the country of the same name;
# accepted as low-risk for US-focused tech job boards.
US_STATE_NAMES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
]
CANADA_PHRASES = ["canada"]
CANADIAN_PROVINCE_CODES = ["on", "bc", "qc", "ab", "mb", "sk", "ns", "nb", "pe", "nl", "yt", "nt", "nu"]

# state codes must be their own word (bounded by non-letters) so ", ca" doesn't
# match inside "Toronto, Canada" — a real false positive seen against live Greenhouse data.
_STATE_CODE_RE = re.compile(
    r"\b(" + "|".join(US_STATE_CODES) + r")\b"
)
_STATE_NAME_RE = re.compile(
    r"\b(" + "|".join(US_STATE_NAMES) + r")\b"
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

# same "roughly 0-4 years" target as the title check above, but applied to an
# actual years-of-experience figure pulled from the description -- catches a
# title like "Data Engineer" (no seniority keyword) whose qualifications
# section actually asks for 6+ years.
MAX_YEARS_REQUIRED = 5
_YEARS_WINDOW = 40  # chars to look for "experience" around a years-mention, so an
                     # unrelated number ("founded 10 years ago") doesn't false-match

_YEARS_NUM_RE = re.compile(
    r"(\d{1,2})\+?\s*(?:-|to|–)\s*\d{1,2}\+?\s*years?"  # "3-5 years" / "3 to 5 years" -- capture the lower bound
    r"|(\d{1,2})\+\s*years?"                                  # "5+ years"
    r"|(?:minimum(?:\s+of)?|at least)\s*(\d{1,2})\s*years?",  # "minimum of 3 years" / "at least 3 years"
    re.IGNORECASE,
)


def _min_years_required(description: str) -> int | None:
    """Best-effort extraction of the lowest years-of-experience figure
    mentioned near the word "experience" in a job description. Takes the
    minimum across all matches, not the first/max -- a JD listing "3+ years
    required, 5+ years preferred for senior candidates" should be judged
    on the 3, since that's the actual bar to be considered."""
    years = []
    for m in _YEARS_NUM_RE.finditer(description):
        n = next(g for g in m.groups() if g is not None)
        before = description[max(0, m.start() - _YEARS_WINDOW):m.start()].lower()
        after = description[m.end():m.end() + _YEARS_WINDOW].lower()
        if "experience" in before or "experience" in after:
            years.append(int(n))
    return min(years) if years else None


def _match_category(text: str) -> str | None:
    if any(k in text for k in DATA_ENGINEER_KEYWORDS):
        return "data_engineer"
    if any(k in text for k in DATA_ANALYST_KEYWORDS):
        return "data_analyst"
    if any(k in text for k in DATA_SCIENTIST_KEYWORDS):
        return "data_scientist"
    return None


def job_category(job: Job) -> str | None:
    """Returns 'data_engineer', 'data_analyst', 'data_scientist', or None.
    Checked in that priority order so a title matching more than one keyword
    set routes to only one category, not multiple.

    Falls back to the job description only for titles carrying a generic
    new-grad signal (see _NEW_GRAD_TITLE_RE) -- these programs often don't
    name a track in the title itself (e.g. "Software Engineer, University
    Grad Program" that's actually a data engineering rotation)."""
    category = _match_category(job.title.lower())
    if category is not None:
        return category
    if job.description and _NEW_GRAD_TITLE_RE.search(job.title):
        return _match_category(job.description.lower())
    return None


def is_within_experience_range(job: Job) -> bool:
    if _SENIORITY_RE.search(job.title):
        return False
    if job.description:
        min_years = _min_years_required(job.description)
        if min_years is not None and min_years >= MAX_YEARS_REQUIRED:
            return False
    return True


def _parse_posted_date(posted_date: str | None) -> datetime | None:
    if not posted_date:
        return None
    try:
        return datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_recent(job: Job, max_age_days: int = MAX_POSTING_AGE_DAYS) -> bool:
    """Discards stale postings so a backlog can't crowd out genuinely fresh
    ones (see MAX_NEW_JOBS_PER_CATEGORY_PER_RUN in main.py). Jobs with no
    parseable posted_date (Google's connector doesn't have one) are always
    kept -- we have no signal to discard them on, so dedup via state is the
    only freshness control that applies to them."""
    dt = _parse_posted_date(job.posted_date)
    if dt is None:
        return True
    return datetime.now(timezone.utc) - dt <= timedelta(days=max_age_days)


def time_ago(posted_date: str | None) -> str | None:
    dt = _parse_posted_date(posted_date)
    if dt is None:
        return None
    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(hours // 24)
    return f"{days} day{'s' if days != 1 else ''} ago"


def sort_by_recency(jobs: list[Job]) -> list[Job]:
    """Newest posted_date first, so if MAX_NEW_JOBS_PER_CATEGORY_PER_RUN
    forces a cap, the freshest postings win the slots -- directly serves
    "notify before other applicants" instead of an arbitrary discovery
    order. Jobs with no parseable posted_date (Google has none) sort last:
    unknown freshness shouldn't outrank a job we can confirm is fresh."""
    def key(job: Job) -> datetime:
        return _parse_posted_date(job.posted_date) or datetime.min.replace(tzinfo=timezone.utc)
    return sorted(jobs, key=key, reverse=True)


def is_us_location(job: Job) -> bool:
    if not job.location:
        return False  # exclude if location is missing/unclear — safer default than including
    loc = job.location.lower()
    if any(phrase in loc for phrase in CANADA_PHRASES) or _CANADA_PROVINCE_CA_RE.search(loc):
        return False
    if any(phrase in loc for phrase in US_PHRASES):
        return True
    return bool(_STATE_CODE_RE.search(loc)) or bool(_STATE_NAME_RE.search(loc))
