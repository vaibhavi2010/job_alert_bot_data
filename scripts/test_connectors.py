"""Read-only sanity check: fetches every enabled company's connector and
reports how many jobs pass the DA/DE/DS + US + experience + freshness
filters. Does not post to Discord, write to Sheets, or touch the Gist --
safe to run any time. Run from the repo root: `python scripts/test_connectors.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from connectors import CONNECTORS
from filters import is_recent, is_us_location, is_within_experience_range, job_category


def main() -> None:
    companies = config.load_companies()
    had_error = False

    for c in companies:
        if not c.get("enabled", True):
            print(f"{c['name']}: SKIPPED (disabled)")
            continue
        connector = CONNECTORS.get(c["connector"])
        if connector is None:
            print(f"{c['name']}: ERROR unknown connector '{c['connector']}'")
            had_error = True
            continue
        try:
            jobs = connector(c)
            relevant = [
                j for j in jobs
                if job_category(j) is not None
                and is_us_location(j) and is_within_experience_range(j) and is_recent(j)
            ]
            print(f"{c['name']}: OK -- {len(jobs)} total jobs, {len(relevant)} pass all filters")
        except Exception as e:
            print(f"{c['name']}: ERROR -- {type(e).__name__}: {e}")
            had_error = True

    sys.exit(1 if had_error else 0)


if __name__ == "__main__":
    main()
