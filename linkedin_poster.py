"""
LinkedIn Publisher
- Technical posts (Databricks/AWS/PySpark/SQL) → architecture diagram
- All other posts → branded card via card_generator.py
- Every post gets an image
- Retry logic (3 attempts, 30s delay)
- Auto-adds first comment with resource link for technical posts
"""

import os
import json
import time
import requests
from datetime import date


TECHNICAL_DOMAINS = {"Databricks", "AWS", "PySpark", "SQL / dbt"}

MAX_RETRIES  = 3
RETRY_DELAY  = 30


# ── Member URN ─────────────────────────────────────────────────────────────────

def get_member_urn(access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    if r.status_code == 200:
        sub = r.json().get("sub", "")
        if sub:
            urn = f"urn:li:person:{sub}"
            print(f"✓ URN from userinfo: {urn}")
            return urn
    r2 = requests.get("https://api.linkedin.com/v2/me", headers=headers)
    if r2.status_code == 200:
        mid = r2.json().get("id", "")
        if mid:
            urn = f"urn:li:member:{mid}"
            print(f"✓ URN from /v2/me: {urn}")
            return urn
    urn = os.environ.get("LINKEDIN_PERSON_URN", "")
    if urn:
        print(f"⚠ Using URN from secret: {urn}")
        return urn
    raise ValueError("Could not determine member URN")


# ── Image preparation ──────────────────────────────────────────────────────────


def prepare_image(post_data: dict) -> str | None:
    """
    Returns path to a PNG ready for upload, or None on failure.
    - Technical domain → convert architecture SVG to PNG
    - All other formats → generate a branded card PNG
    """
    domain = post_data.get("domain", "")

    from image_generator import get_image_for_post
    success = get_image_for_post(post_data, "post_image.png")
    return "post_image.png" if success else None


# ── LinkedIn image upload ──────────────────────────────────────────────────────

def upload_image(access_token: str, person_urn: str, png_path: str) -> str | None:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    reg = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": person_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
    )
    if reg.status_code != 200:
        print(f"⚠ Image registration failed {reg.status_code} — posting text-only")
        return None

    upload_url = reg.json()["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn  = reg.json()["value"]["asset"]

    with open(png_path, "rb") as f:
        up = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "image/png"},
            data=f.read()
        )
    if up.status_code in (200, 201):
        print(f"✓ Image uploaded: {asset_urn}")
        return asset_urn

    print(f"⚠ Image upload failed {up.status_code} — text-only")
    return None


# ── Publish ────────────────────────────────────────────────────────────────────

def publish_post(access_token: str, person_urn: str, text: str, asset_urn: str | None) -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    if asset_urn:
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [{
                "status": "READY",
                "description": {"text": "Data Engineering Visual"},
                "media": asset_urn,
                "title": {"text": "Data Engineering"},
            }]
        }
    else:
        share_content = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE",
        }

    payload = {
        "author":         person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility":     {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  Publish attempt {attempt}/{MAX_RETRIES}...")
        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers, json=payload
        )
        if resp.status_code == 201:
            post_id = resp.headers.get("x-restli-id", "unknown")
            print(f"✓ Published! ID: {post_id}")
            return post_id

        print(f"  Failed: {resp.status_code} {resp.text}")
        if resp.status_code in (401, 403):
            resp.raise_for_status()
        if attempt < MAX_RETRIES:
            print(f"  Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    resp.raise_for_status()


# ── First comment ──────────────────────────────────────────────────────────────

def add_first_comment(access_token: str, post_id: str, person_urn: str, domain: str):
    links = {
        "Databricks": "📚 Databricks docs: https://docs.databricks.com",
        "AWS":        "📚 AWS Data & Analytics: https://aws.amazon.com/big-data/",
        "PySpark":    "📚 PySpark docs: https://spark.apache.org/docs/latest/api/python/",
        "SQL / dbt":  "📚 dbt docs: https://docs.getdbt.com",
    }
    comment_text = links.get(domain, "")
    if not comment_text:
        return

    encoded = requests.utils.quote(f"urn:li:ugcPost:{post_id}", safe="")
    resp = requests.post(
        f"https://api.linkedin.com/v2/socialActions/{encoded}/comments",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json={"actor": person_urn, "message": {"text": comment_text}}
    )
    if resp.status_code == 201:
        print(f"✓ First comment added")
    else:
        print(f"⚠ Comment failed {resp.status_code} — non-critical")


# ── Log ────────────────────────────────────────────────────────────────────────

def log_post(post_data: dict, post_id: str, had_image: bool):
    path    = "post_history.json"
    history = []
    if os.path.exists(path):
        with open(path) as f:
            history = json.load(f)
    history.append({
        "date":        str(date.today()),
        "post_id":     post_id,
        "format_type": post_data.get("format_type"),
        "domain":      post_data.get("domain"),
        "had_image":   had_image,
        "preview":     post_data["text"][:120] + "...",
    })
    history = history[-90:]
    with open(path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"✓ Logged to {path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set")

    if not os.path.exists("today_post.json"):
        raise FileNotFoundError("today_post.json not found")

    with open("today_post.json") as f:
        post_data = json.load(f)

    person_urn = get_member_urn(access_token)
    domain     = post_data.get("domain", "")

    print(f"\n▶ [{post_data['format_type']}] · [{domain}] · {post_data['date']}")
    print(f"  Author: {person_urn}")
    print(f"\n--- Preview ---\n{post_data['text'][:200]}...\n")

    # Every post gets an image
    png_path  = prepare_image(post_data)
    asset_urn = None
    if png_path:
        asset_urn = upload_image(access_token, person_urn, png_path)
    else:
        print("⚠ No image available — posting text-only")

    post_id = publish_post(access_token, person_urn, post_data["text"], asset_urn)
    log_post(post_data, post_id, had_image=asset_urn is not None)
    add_first_comment(access_token, post_id, person_urn, domain)


if __name__ == "__main__":
    main()
