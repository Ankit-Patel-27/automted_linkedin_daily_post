"""
Notifications & Monitoring
- Token expiry check (warns in logs + creates expiry_warning.txt)
- Failure notification via GitHub Actions summary
- Weekly analytics summary written to WEEKLY_REPORT.md in repo
"""

import os
import json
import sys
from datetime import date, datetime, timedelta


def check_token_expiry():
    """
    Tracks token issue date in token_meta.json.
    Writes expiry_warning.txt if within 7 days — visible in repo.
    """
    meta_path = "token_meta.json"

    if not os.path.exists(meta_path):
        with open(meta_path, "w") as f:
            json.dump({"issued_date": str(date.today())}, f)
        print("✓ Token issue date recorded")
        return

    with open(meta_path) as f:
        meta = json.load(f)

    issued    = datetime.strptime(meta.get("issued_date", str(date.today())), "%Y-%m-%d").date()
    expiry    = issued + timedelta(days=60)
    days_left = (expiry - date.today()).days

    print(f"🔑 LinkedIn token expires in {days_left} days ({expiry})")

    warning_path = "expiry_warning.txt"

    if days_left <= 0:
        msg = (
            f"🚨 LINKEDIN TOKEN EXPIRED on {expiry}\n"
            f"The bot will fail until you renew it.\n\n"
            f"Renew at: https://www.linkedin.com/developers/tools/oauth/token-generator\n"
            f"Then update LINKEDIN_ACCESS_TOKEN in GitHub Secrets."
        )
        with open(warning_path, "w") as f:
            f.write(msg)
        print(f"🚨 Token EXPIRED — written to {warning_path}")

    elif days_left <= 7:
        msg = (
            f"⚠️ LINKEDIN TOKEN EXPIRING IN {days_left} DAYS (on {expiry})\n\n"
            f"Renew at: https://www.linkedin.com/developers/tools/oauth/token-generator\n"
            f"Then update LINKEDIN_ACCESS_TOKEN in GitHub Secrets."
        )
        with open(warning_path, "w") as f:
            f.write(msg)
        print(f"⚠️ Token expiry warning written to {warning_path}")

    else:
        # Remove old warning file if token is fine
        if os.path.exists(warning_path):
            os.remove(warning_path)


def write_failure_summary(error: str):
    """
    Writes a FAILURE_REPORT.md to the repo so failures are visible
    in GitHub without needing to dig through Actions logs.
    """
    content = (
        f"# 🚨 LinkedIn Bot Failure Report\n\n"
        f"**Date:** {date.today()}\n\n"
        f"**Error:**\n```\n{error[:800]}\n```\n\n"
        f"**Action required:** Check the [Actions logs]"
        f"(../../actions) for full details.\n\n"
        f"---\n*This file is overwritten on each failure and deleted on next success.*\n"
    )
    with open("FAILURE_REPORT.md", "w") as f:
        f.write(content)
    print("✓ FAILURE_REPORT.md written to repo")


def clear_failure_report():
    """Remove failure report when bot runs successfully."""
    if os.path.exists("FAILURE_REPORT.md"):
        os.remove("FAILURE_REPORT.md")
        print("✓ Cleared old FAILURE_REPORT.md")


def write_weekly_report():
    """
    Writes WEEKLY_REPORT.md every Monday with analytics summary.
    """
    if date.today().weekday() != 0:  # 0 = Monday
        print("ℹ Not Monday — skipping weekly report")
        return

    if not os.path.exists("analytics_report.json"):
        print("⚠ No analytics_report.json — skipping weekly report")
        return

    with open("analytics_report.json") as f:
        report = json.load(f)

    best    = report.get("best_format", "N/A")
    likes   = report.get("total_likes", 0)
    comms   = report.get("total_comments", 0)
    shares  = report.get("total_shares", 0)
    count   = report.get("posts_analysed", 0)
    scores  = report.get("format_avg_scores", {})

    # Format scores table
    scores_rows = "\n".join(
        f"| {fmt} | {score} |"
        for fmt, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    )

    # Recent posts table
    posts = report.get("posts", [])[-10:]  # last 10
    posts_rows = "\n".join(
        f"| {p.get('date','')} | {p.get('format_type','')} | {p.get('domain','')} "
        f"| {p.get('likes',0)} | {p.get('comments',0)} | {p.get('shares',0)} |"
        for p in reversed(posts)
    )

    content = f"""# 📊 Weekly LinkedIn Analytics Report

**Generated:** {date.today()}
**Period:** Last 30 days

---

## Summary

| Metric | Value |
|---|---|
| Posts analysed | {count} |
| Total likes | {likes} |
| Total comments | {comms} |
| Total shares | {shares} |
| 🏆 Best format | **{best}** |

---

## Format Performance (avg engagement score)

| Format | Avg Score |
|---|---|
{scores_rows}

> Score = (likes × 3) + (comments × 5) + (shares × 4)

---

## Recent Posts

| Date | Format | Domain | ❤️ | 💬 | 🔁 |
|---|---|---|---|---|---|
{posts_rows}

---

*Updated every Monday automatically by GitHub Actions.*
"""

    with open("WEEKLY_REPORT.md", "w") as f:
        f.write(content)
    print(f"✓ WEEKLY_REPORT.md written for week of {date.today()}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"

    if mode == "success":
        clear_failure_report()
        check_token_expiry()
        write_weekly_report()

    elif mode == "failure":
        error_msg = sys.argv[2] if len(sys.argv) > 2 else "Unknown error — check Actions logs"
        write_failure_summary(error_msg)
        check_token_expiry()

    elif mode == "check":
        check_token_expiry()
