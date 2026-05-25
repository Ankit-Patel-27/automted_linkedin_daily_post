"""
LinkedIn Post Analytics
Fetches impressions, likes, comments and shares for recent posts
and saves a weekly performance report to analytics_report.json
"""

import os
import json
import requests
from datetime import date, timedelta


def get_member_urn(access_token: str) -> str:
    r = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if r.status_code == 200:
        sub = r.json().get("sub", "")
        if sub:
            return f"urn:li:person:{sub}"
    r2 = requests.get(
        "https://api.linkedin.com/v2/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if r2.status_code == 200:
        mid = r2.json().get("id", "")
        if mid:
            return f"urn:li:member:{mid}"
    urn = os.environ.get("LINKEDIN_PERSON_URN", "")
    if urn:
        return urn
    raise ValueError("Could not determine member URN")


def fetch_post_stats(access_token: str, post_id: str) -> dict:
    """Fetch social actions (likes, comments, shares) for a post."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    stats = {"likes": 0, "comments": 0, "shares": 0, "impressions": 0}

    # Social counts
    encoded_id = requests.utils.quote(f"urn:li:ugcPost:{post_id}", safe="")
    r = requests.get(
        f"https://api.linkedin.com/v2/socialActions/{encoded_id}",
        headers=headers
    )
    if r.status_code == 200:
        data = r.json()
        stats["likes"]    = data.get("likesSummary", {}).get("totalLikes", 0)
        stats["comments"] = data.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
        stats["shares"]   = data.get("sharesSummary", {}).get("totalShares", 0)

    return stats


def build_report(access_token: str) -> dict:
    """Build analytics report from post_history.json"""
    if not os.path.exists("post_history.json"):
        print("⚠ No post_history.json found")
        return {}

    with open("post_history.json") as f:
        history = json.load(f)

    # Only look at last 30 days
    cutoff = str(date.today() - timedelta(days=30))
    recent = [p for p in history if p.get("date", "") >= cutoff]

    print(f"📊 Fetching stats for {len(recent)} recent posts...")

    enriched = []
    for post in recent:
        post_id = post.get("post_id", "")
        if post_id and post_id != "unknown":
            stats = fetch_post_stats(access_token, post_id)
            post.update(stats)
            print(f"  {post['date']} [{post.get('format_type')}] "
                  f"❤ {stats['likes']}  💬 {stats['comments']}  🔁 {stats['shares']}")
        enriched.append(post)

    # Best performing format
    format_scores = {}
    for p in enriched:
        ft = p.get("format_type", "unknown")
        score = p.get("likes", 0) * 3 + p.get("comments", 0) * 5 + p.get("shares", 0) * 4
        if ft not in format_scores:
            format_scores[ft] = {"total_score": 0, "count": 0}
        format_scores[ft]["total_score"] += score
        format_scores[ft]["count"] += 1

    format_avg = {
        ft: round(v["total_score"] / v["count"], 1)
        for ft, v in format_scores.items()
    }
    best_format = max(format_avg, key=format_avg.get) if format_avg else "N/A"

    report = {
        "generated_date": str(date.today()),
        "posts_analysed": len(enriched),
        "total_likes":    sum(p.get("likes", 0) for p in enriched),
        "total_comments": sum(p.get("comments", 0) for p in enriched),
        "total_shares":   sum(p.get("shares", 0) for p in enriched),
        "best_format":    best_format,
        "format_avg_scores": format_avg,
        "posts": enriched,
    }

    with open("analytics_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Report saved to analytics_report.json")
    print(f"  Best performing format: {best_format}")
    print(f"  Total engagement: ❤ {report['total_likes']}  "
          f"💬 {report['total_comments']}  🔁 {report['total_shares']}")

    return report


if __name__ == "__main__":
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set")
    build_report(token)
