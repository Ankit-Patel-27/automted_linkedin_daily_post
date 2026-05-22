"""
LinkedIn Publisher
Uses the newer LinkedIn Posts API (2022-02) which:
- Auto-fetches your member URN from the token (no manual URN needed)
- No X-Restli-Protocol-Version header required
- Simpler payload structure
"""

import os
import json
import requests
from datetime import date


# Map domain names → SVG image file in /images/
DOMAIN_IMAGES = {
    "Databricks": "images/databricks_flow.svg",
    "AWS":        "images/aws_data_pipeline.svg",
    "PySpark":    "images/pyspark_flow.svg",
    "SQL / dbt":  "images/sql_dbt_flow.svg",
}


# ── Step 1: Get member URN from token ─────────────────────────────────────────

def get_member_urn(access_token: str) -> str:
    """
    Fetch the authenticated member's URN using /userinfo (OpenID Connect).
    Falls back to LINKEDIN_PERSON_URN secret if API call fails.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    # Try OpenID userinfo first
    resp = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    if resp.status_code == 200:
        sub = resp.json().get("sub")
        if sub:
            urn = f"urn:li:person:{sub}"
            print(f"✓ Member URN from userinfo: {urn}")
            return urn

    # Try /v2/me as fallback
    resp2 = requests.get("https://api.linkedin.com/v2/me", headers=headers)
    if resp2.status_code == 200:
        member_id = resp2.json().get("id")
        if member_id:
            urn = f"urn:li:member:{member_id}"
            print(f"✓ Member URN from /v2/me: {urn}")
            return urn

    # Final fallback: use the secret
    urn = os.environ.get("LINKEDIN_PERSON_URN", "")
    if urn:
        print(f"⚠ Using URN from secret: {urn}")
        return urn

    raise ValueError(
        "Could not determine member URN. "
        "Set LINKEDIN_PERSON_URN secret as urn:li:member:YOUR_NUMERIC_ID"
    )


# ── Image helpers ──────────────────────────────────────────────────────────────

def svg_to_png(svg_path: str, png_path: str) -> bool:
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=800, output_height=500)
        print(f"✓ Converted {svg_path} → {png_path}")
        return True
    except Exception as e:
        print(f"⚠ SVG→PNG failed (skipping image): {e}")
        return False


def upload_image(access_token: str, person_urn: str, png_path: str) -> str | None:
    """Upload image to LinkedIn, return asset URN or None."""
    # Register upload
    reg_resp = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
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

    if reg_resp.status_code != 200:
        print(f"⚠ Image registration failed: {reg_resp.status_code} — posting text-only")
        return None

    data       = reg_resp.json()
    upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn  = data["value"]["asset"]

    # Upload image bytes
    with open(png_path, "rb") as f:
        up_resp = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "image/png"},
            data=f.read()
        )

    if up_resp.status_code in (200, 201):
        print(f"✓ Image uploaded: {asset_urn}")
        return asset_urn
    else:
        print(f"⚠ Image upload failed: {up_resp.status_code} — posting text-only")
        return None


# ── Post publishing ────────────────────────────────────────────────────────────

def publish_post(access_token: str, person_urn: str, text: str, asset_urn: str | None = None) -> str:
    """
    Publish using the newer LinkedIn Posts API (versioned: 202210).
    Returns post ID on success, raises on failure.
    """
    headers = {
        "Authorization":       f"Bearer {access_token}",
        "Content-Type":        "application/json",
        "LinkedIn-Version":    "202310",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author":          person_urn,
        "commentary":      text,
        "visibility":      "PUBLIC",
        "distribution": {
            "feedDistribution":               "MAIN_FEED",
            "targetEntities":                 [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState":  "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    if asset_urn:
        payload["content"] = {
            "media": {
                "altText": "Data Engineering Architecture Diagram",
                "id":      asset_urn
            }
        }

    resp = requests.post("https://api.linkedin.com/rest/posts", headers=headers, json=payload)

    if resp.status_code == 201:
        post_id = resp.headers.get("x-restli-id", resp.headers.get("X-LinkedIn-Id", "unknown"))
        print(f"✓ Post published! ID: {post_id}")
        return post_id
    else:
        print(f"✗ Publish failed: {resp.status_code} {resp.text}")
        resp.raise_for_status()


# ── Logging ────────────────────────────────────────────────────────────────────

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
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set")

    if not os.path.exists("today_post.json"):
        raise FileNotFoundError("today_post.json not found — run post_generator.py first")

    with open("today_post.json") as f:
        post_data = json.load(f)

    # Auto-fetch URN from token
    person_urn = get_member_urn(access_token)

    domain = post_data.get("domain", "")
    print(f"\nPublishing [{post_data['format_type']}] · [{domain}] · {post_data['date']}")
    print(f"Author URN:")
    for i in person_urn:
        print(f"  {i}", end="")
    print(f"\n--- Preview ---\n{post_data['text'][:200]}...\n")

    # Try image for technical posts
    asset_urn = None
    svg_file  = DOMAIN_IMAGES.get(domain)

    if svg_file and os.path.exists(svg_file):
        png_file = svg_file.replace(".svg", ".png")
        if svg_to_png(svg_file, png_file):
            asset_urn = upload_image(access_token, person_urn, png_file)
    elif svg_file:
        print(f"⚠ Image not found: {svg_file} — text-only post")

    post_id = publish_post(access_token, person_urn, post_data["text"], asset_urn)
    log_post(post_data, post_id, had_image=asset_urn is not None)


if __name__ == "__main__":
    main()