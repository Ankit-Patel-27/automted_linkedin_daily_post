"""
LinkedIn Publisher
Uses ugcPosts API (v2) — the correct API for personal profile posting.
The newer /rest/posts endpoint requires Marketing Developer Platform
which is not available for personal apps.
"""

import os
import json
import requests
from datetime import date


DOMAIN_IMAGES = {
    "Databricks": "images/databricks_flow.svg",
    "AWS":        "images/aws_data_pipeline.svg",
    "PySpark":    "images/pyspark_flow.svg",
    "SQL / dbt":  "images/sql_dbt_flow.svg",
}


# ── Get member URN from token ──────────────────────────────────────────────────

def get_member_urn(access_token: str) -> str:
    """
    Fetch authenticated member's URN.
    Tries /userinfo (OpenID) first, then /v2/me, then falls back to secret.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    # OpenID userinfo — needs openid + profile scope
    r = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    if r.status_code == 200:
        sub = r.json().get("sub", "")
        if sub:
            urn = f"urn:li:person:{sub}"
            print(f"✓ URN from userinfo: {urn}")
            return urn

    # /v2/me fallback — needs r_liteprofile scope
    r2 = requests.get("https://api.linkedin.com/v2/me", headers=headers)
    if r2.status_code == 200:
        mid = r2.json().get("id", "")
        if mid:
            urn = f"urn:li:member:{mid}"
            print(f"✓ URN from /v2/me: {urn}")
            return urn

    # Secret fallback
    urn = os.environ.get("LINKEDIN_PERSON_URN", "")
    if urn:
        print(f"⚠ Using URN from secret: {urn}")
        return urn

    raise ValueError(
        "Could not get member URN from API or secret. "
        "Add LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID to GitHub Secrets."
    )


# ── Image helpers ──────────────────────────────────────────────────────────────

def svg_to_png(svg_path: str, png_path: str) -> bool:
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=800, output_height=500)
        print(f"✓ {svg_path} → {png_path}")
        return True
    except Exception as e:
        print(f"⚠ SVG→PNG failed (text-only post): {e}")
        return False


def upload_image(access_token: str, person_urn: str, png_path: str) -> str | None:
    """Upload image via ugcPosts asset registration. Returns asset URN or None."""
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
        print(f"⚠ Image registration failed {reg.status_code} — text-only")
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

def publish_post(access_token: str, person_urn: str, text: str, asset_urn: str | None = None) -> str:
    """Publish via ugcPosts API — works for all personal LinkedIn apps."""
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
                "description": {"text": "Data Engineering Architecture Diagram"},
                "media": asset_urn,
                "title": {"text": "Architecture Diagram"},
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
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=payload
    )

    if resp.status_code == 201:
        post_id = resp.headers.get("x-restli-id", "unknown")
        print(f"✓ Post published! ID: {post_id}")
        return post_id

    print(f"✗ Publish failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()


# ── Log ────────────────────────────────────────────────────────────────────────

def log_post(post_data: dict, post_id: str, had_image: bool, log_path="post_history.json"):
    history = []
    if os.path.exists(log_path):
        with open(log_path) as f:
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
    with open(log_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"✓ Logged to {log_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN secret not set")

    if not os.path.exists("today_post.json"):
        raise FileNotFoundError("today_post.json not found — run post_generator.py first")

    with open("today_post.json") as f:
        post_data = json.load(f)

    person_urn = get_member_urn(access_token)

    domain = post_data.get("domain", "")
    print(f"\n▶ [{post_data['format_type']}] · [{domain}] · {post_data['date']}")
    print(f"  Author: {person_urn}")
    print(f"\n--- Preview ---\n{post_data['text'][:200]}...\n")

    # Attach image only for technical domain posts
    asset_urn = None
    svg_file  = DOMAIN_IMAGES.get(domain)

    if svg_file and os.path.exists(svg_file):
        png_file = svg_file.replace(".svg", ".png")
        if svg_to_png(svg_file, png_file):
            asset_urn = upload_image(access_token, person_urn, png_file)
    elif svg_file:
        print(f"⚠ Image not found: {svg_file} — text-only")

    post_id = publish_post(access_token, person_urn, post_data["text"], asset_urn)
    log_post(post_data, post_id, had_image=asset_urn is not None)


if __name__ == "__main__":
    main()