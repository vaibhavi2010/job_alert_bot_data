from collections import Counter
from datetime import UTC, datetime, timedelta, timezone

import requests

import config
from state import load_state

# Arizona doesn't observe DST, so America/Phoenix is a fixed UTC-7 year-round
# -- avoids pulling in a timezone library for one offset.
LOCAL_TZ = timezone(timedelta(hours=-7))
CATEGORIES = ("data_engineer", "data_analyst")


def _local_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str).astimezone(LOCAL_TZ)
    return dt.date().isoformat()


def _post(content: str) -> None:
    r = requests.post(
        f"https://discord.com/api/v10/channels/{config.EOD_UPDATES_CHANNEL_ID}/messages",
        headers={"Authorization": f"Bot {config.DISCORD_BOT_TOKEN}"},
        json={"content": content},
        timeout=15,
    )
    r.raise_for_status()


def build_summary(state: dict, today: str) -> str:
    posted_counts = Counter()
    applied_counts = Counter()

    for record in state.values():
        category = record.get("category")
        if category not in CATEGORIES:
            continue  # predates category tracking -- exclude so the
            # displayed total always matches the displayed breakdown
        if _local_date(record["first_seen"]) == today:
            posted_counts[category] += 1
        if record["status"] == "applied" and _local_date(record["status_updated_at"]) == today:
            applied_counts[category] += 1

    posted_total = sum(posted_counts.get(c, 0) for c in CATEGORIES)
    applied_total = sum(applied_counts.get(c, 0) for c in CATEGORIES)

    lines = [f"**End of Day Summary — {today}**", "", "Posted today:"]
    for cat in CATEGORIES:
        lines.append(f"  {cat}: {posted_counts.get(cat, 0)}")
    lines.append(f"  Total: {posted_total}")
    lines.append("")
    lines.append("Applied today:")
    for cat in CATEGORIES:
        lines.append(f"  {cat}: {applied_counts.get(cat, 0)}")
    lines.append(f"  Total: {applied_total}")

    return "\n".join(lines)


def run() -> None:
    state = load_state()
    today = datetime.now(UTC).astimezone(LOCAL_TZ).date().isoformat()
    summary = build_summary(state, today)
    _post(summary)
    print("posted end of day summary")


if __name__ == "__main__":
    run()
