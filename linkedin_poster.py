"""
LinkedIn Publisher
Reads today_post.json and publishes it to LinkedIn via the UGC Posts API.
For technical domain posts (Databricks, AWS, PySpark, SQL/dbt), attaches
the matching architecture diagram as an image.
"""

import os
import json
import base64
import subprocess
import requests
from datetime import date
from pathlib import Path


# Map domain names → SVG image file in /images/
DOMAIN_IMAGES = {
    "Databricks":  "images/databricks_flow.svg",
    "AWS":         "images/aws_data_pipeline.svg",
    "PySpark":     "images/pyspark_flow.svg",
    "SQL / dbt":   "images/sql_dbt_flow.svg",
}


# ── Image helpers ──────────────────────────────────────────────────────────────

def svg_to_png(svg_path: str, png_path: str) -> bool:
    """Convert SVG → PNG using cairosvg (installed in workflow)."""
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=800, output_height=500)
        print(f"✓ Converted {svg_path} → {png_path}")
        return True
    except Exception as e:
        print(f"⚠ SVG→PNG conversion failed: {e}")
        return False


def register_image_linkedin(access_token: str, person_urn: str) -> tuple[str, str] | None:
    """
    Step 1 of LinkedIn image upload: register the asset, get upload URL + asset URN.
    Returns (upload_url, asset_urn) or None on failure.
    """
    url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"⚠ Image registration failed: {resp.status_code} {resp.text}")
        return None

    data = resp.json()
    upload_url  = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn   = data["value"]["asset"]
    return upload_url, asset_urn


def upload_image_linkedin(upload_url: str, png_path: str, access_token: str) -> bool:
    """Step 2: Upload the PNG bytes to the pre-signed upload URL."""
    with open(png_path, "rb") as f:
        image_bytes = f.read()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "image/png",
    }
    resp = requests.put(upload_url, headers=headers, data=image_bytes)
    if resp.status_code in (200, 201):
        print("✓ Image uploaded to LinkedIn")
        return True
    else:
        print(f"⚠ Image upload failed: {resp.status_code} {resp.text}")
        return False


# ── Post publishing ────────────────────────────────────────────────────────────

def post_to_linkedin(access_token: str, person_urn: str, post_text: str, asset_urn: str | None = None) -> dict:
    """Publishes a post (text-only or with image) via the UGC Posts API."""
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    if asset_urn:
        share_content = {
            "shareCommentary": {"text": post_text},
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "description": {"text": "Data Engineering Architecture Diagram"},
                    "media": asset_urn,
                    "title": {"text": "Architecture Diagram"},
                }
            ],
        }
    else:
        share_content = {
            "shareCommentary": {"text": post_text},
            "shareMediaCategory": "NONE",
        }

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 201:
        post_id = resp.headers.get("x-restli-id", "unknown")
        print(f"✓ Post published! ID: {post_id}")
        return {"success": True, "post_id": post_id}
    else:
        print(f"✗ Publish failed: {resp.status_code} {resp.text}")
        resp.raise_for_status()


def log_published_post(post_data: dict, post_id: str, had_image: bool, log_path="post_history.json"):
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
    person_urn   = os.environ.get("LINKEDIN_PERSON_URN")

    if not access_token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set")
    if not person_urn:
        raise ValueError("LINKEDIN_PERSON_URN not set")

    if not os.path.exists("today_post.json"):
        raise FileNotFoundError("today_post.json not found — run post_generator.py first")

    with open("today_post.json") as f:
        post_data = json.load(f)

    domain = post_data.get("domain", "")
    print(f"\nPublishing [{post_data['format_type']}] post on [{domain}] for {post_data['date']}")
    print(f"\n--- Preview ---\n{post_data['text'][:200]}...\n")

    # ── Try to attach image for technical domain posts ──
    asset_urn = None
    svg_file  = DOMAIN_IMAGES.get(domain)

    if svg_file and os.path.exists(svg_file):
        png_file = svg_file.replace(".svg", ".png")
        converted = svg_to_png(svg_file, png_file)

        if converted:
            reg = register_image_linkedin(access_token, person_urn)
            if reg:
                upload_url, asset_urn_candidate = reg
                uploaded = upload_image_linkedin(upload_url, png_file, access_token)
                if uploaded:
                    asset_urn = asset_urn_candidate
                    print(f"✓ Image ready: {asset_urn}")
    elif svg_file:
        print(f"⚠ Image file not found: {svg_file} — posting text-only")

    result = post_to_linkedin(access_token, person_urn, post_data["text"], asset_urn)

    if result["success"]:
        log_published_post(post_data, result["post_id"], had_image=asset_urn is not None)


if __name__ == "__main__":
    main()
