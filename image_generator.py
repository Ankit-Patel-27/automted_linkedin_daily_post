"""
Dynamic Image Generator
- Non-technical posts  -> Pollinations AI generates topic-relevant image
- Technical posts      -> Python generates a diagram PNG -> Pollinations AI
                         enhances it visually while preserving all content exactly
"""

import os
import io
import json
import time
import hashlib
import requests
from datetime import date
from urllib.parse import quote


TECHNICAL_DOMAINS = {"Databricks", "AWS", "PySpark", "SQL / dbt"}

# -- Pollinations AI ------------------------------------------------------- [...]

def pollinations_text_to_image(prompt: str, width: int = 1200, height: int = 630,
                                seed: int = None, output_path: str = "post_image.png") -> bool:
    """
    Generate image via Pollinations AI (free, no API key).
    Uses the /prompt/ endpoint with GET request.
    """
    if seed is None:
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 99999

    encoded_prompt = quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
    )

    print(f"🎨 Generating image via Pollinations AI...")
    print(f"   Prompt: {prompt[:100]}...")

    for attempt in range(1, 4):
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                print(f"✓ Image saved: {output_path} ({len(resp.content)//1024}KB)")
                return True
            else:
                print(f"  Attempt {attempt} failed: {resp.status_code}, size={len(resp.content)}")
        except Exception as e:
            print(f"  Attempt {attempt} error: {e}")

        if attempt < 3:
            time.sleep(10)

    return False


def pollinations_enhance_diagram(diagram_path: str, topic: str,
                                  domain: str, output_path: str = "post_image.png") -> bool:
    """
    Pass a locally generated diagram to Pollinations AI for visual enhancement.
    The prompt strictly instructs it to preserve all diagram content/text/structure.

    Uses img2img-style URL approach: encode diagram as base64 and send as
    an image prompt with strict enhancement-only instructions.
    """
    import base64

    with open(diagram_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Strict enhancement prompt - preserves content, only improves visuals
    enhance_prompt = (
        f"Enhance this data engineering architecture diagram for {domain} showing {topic}. "
        f"STRICT RULES: Do NOT change, move, remove, or alter any text labels, boxes, arrows, "
        f"node names, or diagram structure. Keep ALL technical content exactly as-is. "
        f"Only improve: background depth, color contrast, glow effects on arrows, "
        f"box shadows, gradient fills on nodes, overall visual polish. "
        f"Dark professional theme. The diagram must remain fully readable and technically accurate. "
        f"Style: dark background #0a0e1a, glowing connectors, crisp white text, "
        f"technology company presentation quality."
    )

    encoded_prompt = quote(enhance_prompt)
    seed = int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) % 99999

    # Pollinations img2img endpoint
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1200&height=630&seed={seed}&nologo=true"
        f"&image=data:image/png;base64,{img_b64}"
    )

    print(f"✨ Enhancing diagram via Pollinations AI (content-preserving)...")

    for attempt in range(1, 4):
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                print(f"✓ Enhanced diagram saved: {output_path}")
                return True
            else:
                print(f"  Attempt {attempt} - status {resp.status_code}, size {len(resp.content)}")
        except Exception as e:
            print(f"  Attempt {attempt} error: {e}")

        if attempt < 3:
            time.sleep(15)

    # Fallback: use original diagram if enhancement fails
    print("⚠ Enhancement failed - using original diagram")
    import shutil
    shutil.copy(diagram_path, output_path)
    return True   # Still return True - original diagram is fine


# -- Non-technical post image prompts ---------------------------------------

FORMAT_PROMPTS = {
    "insight": (
        "Professional dark tech workspace, glowing data streams, neural network visualization, "
        "blue and purple light, cinematic depth of field, 4K, no text"
    ),
    "achievement": (
        "Abstract golden trophy made of data nodes and connections, dark background, "
        "particle effects, professional tech aesthetic, 4K, no text"
    ),
    "open_to_work": (
        "Professional data engineer at modern workstation, city skyline background, "
        "blue ambient lighting, career growth concept, cinematic, 4K, no text"
    ),
    "tip": (
        "Glowing code terminal with data pipeline visualization, dark background, "
        "teal and white colors, professional tech aesthetic, 4K, no text"
    ),
    "myth_vs_reality": (
        "Two contrasting paths of light in dark space, one dim and one bright, "
        "abstract data visualization, professional, 4K, no text"
    ),
    "project_spotlight": (
        "Futuristic data platform architecture visualization, glowing nodes connected "
        "by light streams, dark space background, cinematic, 4K, no text"
    ),
    "industry_take": (
        "Abstract healthcare data visualization, DNA helix merged with cloud infrastructure, "
        "blue and green colors, dark background, 4K, no text"
    ),
}


def build_nontechnical_prompt(post_data: dict) -> str:
    """Build a rich, topic-aware prompt for non-technical posts."""
    fmt    = post_data.get("format_type", "insight")
    topic  = post_data.get("topic", "")
    domain = post_data.get("domain", "")

    base_prompt = FORMAT_PROMPTS.get(fmt, FORMAT_PROMPTS["insight"])

    # Enrich with topic keywords
    topic_keywords = " ".join(topic.split()[:6]) if topic else ""
    if topic_keywords:
        base_prompt = f"{topic_keywords} concept, {base_prompt}"

    # If post_data contains an explicit image_prompt (from post_generator), prefer it
    explicit = post_data.get("image_prompt")
    if explicit:
        return explicit

    return base_prompt


# -- Dynamic technical diagram generator -------------------------------------

def generate_technical_diagram(post_data: dict, output_path: str = "diagram_raw.png") -> bool:
    """
    Generates a clean, readable architecture/flow diagram using matplotlib
    based on the specific topic and domain.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    except ImportError:
        print("⚠ matplotlib not available")
        return False

    domain = post_data.get("domain", "")
    topic  = post_data.get("topic", "")

    DIAGRAMS = _get_diagram_config(domain, topic)

    fig, ax = plt.subplots(figsize=(14, 7.35))
    fig.patch.set_facecolor("#0a0e1a")
    ax.set_facecolor("#0a0e1a")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7.35)
    ax.axis("off")

    # Title
    ax.text(7, 6.9, DIAGRAMS["title"], ha="center", va="top",
            fontsize=16, fontweight="bold", color=DIAGRAMS["accent"],
            fontfamily="monospace")
    ax.text(7, 6.55, DIAGRAMS["subtitle"], ha="center", va="top",
            fontsize=9, color="#8892a4", fontfamily="monospace")

    # Draw nodes
    for node in DIAGRAMS["nodes"]:
        x, y, w, h = node["x"], node["y"], node.get("w", 2.2), node.get("h", 0.7)
        box = FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.05",
            facecolor=node.get("bg", "#1a2030"),
            edgecolor=node.get("color", DIAGRAMS["accent"]),
            linewidth=1.5
        )
        ax.add_patch(box)
        ax.text(x, y + 0.08, node["label"],
                ha="center", va="center", fontsize=9, fontweight="bold",
                color=node.get("color", DIAGRAMS["accent"]), fontfamily="monospace")
        if node.get("sublabel"):
            ax.text(x, y - 0.18, node["sublabel"],
                    ha="center", va="center", fontsize=7,
                    color="#6a7a94", fontfamily="monospace")

    # Draw arrows
    for arrow in DIAGRAMS["arrows"]:
        ax.annotate("",
            xy=(arrow["x2"], arrow["y2"]),
            xytext=(arrow["x1"], arrow["y1"]),
            arrowprops=dict(
                arrowstyle="->",
                color=arrow.get("color", DIAGRAMS["accent"]),
                lw=1.5,
                connectionstyle=arrow.get("style", "arc3,rad=0.0")
            )
        )
        if arrow.get("label"):
            mx = (arrow["x1"] + arrow["x2"]) / 2
            my = (arrow["y1"] + arrow["y2"]) / 2
            ax.text(mx + 0.1, my + 0.1, arrow["label"],
                    fontsize=7, color="#8892a4", fontfamily="monospace")

    # Section labels
    for label in DIAGRAMS.get("section_labels", []):
        ax.text(label["x"], label["y"], label["text"],
                ha="center", va="center", fontsize=8,
                color="#4a5568", fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#0a0e1a",
                          edgecolor="#1e2538", linewidth=0.5))

    plt.tight_layout(pad=0.2)
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="#0a0e1a", edgecolor="none")
    plt.close()
    print(f"✓ Diagram generated: {output_path}")
    return True


def _get_diagram_config(domain: str, topic: str) -> dict:
    """Returns diagram node/arrow config based on domain and topic keywords."""

    topic_lower = topic.lower()

    # -- Databricks configs -------------------------------------------------
    if domain == "Databricks":
        if "medallion" in topic_lower or "bronze" in topic_lower or "delta" in topic_lower:
            return _diagram_databricks_medallion()
        elif "dlt" in topic_lower or "live table" in topic_lower:
            return _diagram_databricks_dlt()
        elif "unity" in topic_lower:
            return _diagram_databricks_unity()
        else:
            return _diagram_databricks_medallion()

    # -- AWS configs -------------------------------------------------------
    elif domain == "AWS":
        if "glue" in topic_lower or "etl" in topic_lower:
            return _diagram_aws_glue()
        elif "kinesis" in topic_lower or "streaming" in topic_lower:
            return _diagram_aws_streaming()
        elif "lake formation" in topic_lower or "phi" in topic_lower:
            return _diagram_aws_lakeformation()
        else:
            return _diagram_aws_glue()

    # -- PySpark configs ---------------------------------------------------
    elif domain == "PySpark":
        if "join" in topic_lower or "broadcast" in topic_lower:
            return _diagram_spark_joins()
        elif "partition" in topic_lower or "skew" in topic_lower:
            return _diagram_spark_partitions()
        else:
            return _diagram_spark_pipeline()

    # -- SQL / dbt configs -------------------------------------------------
    else:
        if "incremental" in topic_lower or "dbt" in topic_lower:
            return _diagram_dbt_incremental()
        elif "scd" in topic_lower or "slowly changing" in topic_lower:
            return _diagram_scd2()
        else:
            return _diagram_dbt_incremental()


# -- Diagram configs ------------------------------------------------------ [...]

def _diagram_databricks_medallion():
    return {
        "title":    "Delta Lake - Medallion Architecture",
        "subtitle": "Bronze - Silver - Gold - ACID Transactions - Schema Evolution",
        "accent":   "#FF6B35",
        "nodes": [
            {"x":1.2, "y":5.5, "label":"Kafka / Kinesis",  "sublabel":"Streaming source",  "color":"#FF6B35", "bg":"#1a1500"},
            {"x":1.2, "y":4.2, "label":"S3 / ADLS",        "sublabel":"Batch files",        "color":"#FF6B35", "bg":"#1a1500"},
            {"x":1.2, "y":2.9, "label":"JDBC / APIs",       "sublabel":"Databases",          "color":"#FF6B35", "bg":"#1a1500"},
            {"x":3.8, "y":4.2, "label":"Auto Loader",       "sublabel":"cloudFiles",         "color":"#1E88E5", "bg":"#0a1520"},
            {"x":6.2, "y":5.2, "label":"🥉 Bronze",         "sublabel":"Raw - Append-only",  "color":"#CD7F32", "bg":"#2a1800"},
            {"x":6.2, "y":4.2, "label":"🥈 Silver",         "sublabel":"Cleaned - Z-order",  "color":"#C0C0C0", "bg":"#1a1f2e"},
            {"x":6.2, "y":3.2, "label":"🥇 Gold",           "sublabel":"Business-ready",     "color":"#FFD700", "bg":"#1f1a00"},
            {"x":9.0, "y":5.2, "label":"Spark / PySpark",   "sublabel":"Compute",            "color":"#00C853", "bg":"#0a1a0a"},
            {"x":9.0, "y":4.2, "label":"MLflow",            "sublabel":"Experiment tracking","color":"#00C853", "bg":"#0a1a0a"},
            {"x":9.0, "y":3.2, "label":"Feature Store",     "sublabel":"ML features",        "color":"#00C853", "bg":"#0a1a0a"},
            {"x":11.8,"y":4.2, "label":"SQL Warehouse",     "sublabel":"BI / Tableau",       "color":"#FF6B35", "bg":"#1a0a00"},
            {"x":11.8,"y":3.2, "label":"Unity Catalog",     "sublabel":"Governance",         "color":"#CE93D8", "bg":"#150a20"},
        ],
        "arrows": [
            {"x1":1.9,"y1":5.5,"x2":3.0,"y2":4.6,"color":"#FF6B35"},
            {"x1":1.9,"y1":4.2,"x2":3.0,"y2":4.2,"color":"#FF6B35"},
            {"x1":1.9,"y1":2.9,"x2":3.0,"y2":3.8,"color":"#FF6B35"},
            {"x1":4.9,"y1":4.2,"x2":5.0,"y2":4.8,"color":"#1E88E5","label":"ingest"},
            {"x1":7.3,"y1":5.2,"x2":7.8,"y2":5.2,"color":"#C0C0C0"},
            {"x1":6.2,"y1":4.8,"x2":6.2,"y2":4.5,"color":"#C0C0C0"},
            {"x1":6.2,"y1":3.9,"x2":6.2,"y2":3.5,"color":"#FFD700"},
            {"x1":7.3,"y1":3.2,"x2":7.8,"y2":3.8,"color":"#00C853","label":"compute"},
            {"x1":10.1,"y1":4.2,"x2":10.7,"y2":4.2,"color":"#FF6B35","label":"serve"},
        ],
        "section_labels": [
            {"x":1.2,"y":1.9,"text":"SOURCES"},
            {"x":3.8,"y":1.9,"text":"INGEST"},
            {"x":6.2,"y":1.9,"text":"DELTA LAKE"},
            {"x":9.0,"y":1.9,"text":"COMPUTE"},
            {"x":11.8,"y":1.9,"text":"SERVE"},
        ],
    }


def _diagram_databricks_dlt():
    return {
        "title":    "Delta Live Tables (DLT) Pipeline",
        "subtitle": "Declarative ETL - Auto-scaling - Built-in Quality Checks",
        "accent":   "#FF6B35",
        "nodes": [
            {"x":1.5, "y":5.0, "label":"Raw Sources",     "sublabel":"S3 / Kafka",         "color":"#FF6B35","bg":"#1a1500"},
            {"x":4.0, "y":5.8, "label":"@dlt.table",      "sublabel":"Bronze layer",        "color":"#CD7F32","bg":"#2a1800"},
            {"x":4.0, "y":4.2, "label":"@dlt.view",       "sublabel":"Streaming ingestion", "color":"#1E88E5","bg":"#0a1520"},
            {"x":7.0, "y":5.8, "label":"Expectations",    "sublabel":"Quality checks",      "color":"#F44336","bg":"#1a0a0a"},
            {"x":7.0, "y":4.2, "label":"Silver Table",    "sublabel":"Cleaned - validated", "color":"#C0C0C0","bg":"#1a1f2e"},
            {"x":10.0,"y":5.0, "label":"Gold Table",      "sublabel":"Aggregated metrics",  "color":"#FFD700","bg":"#1f1a00"},
            {"x":12.5,"y":5.0, "label":"SQL Warehouse",   "sublabel":"BI / Dashboards",     "color":"#00C853","bg":"#0a1a0a"},
            {"x":7.0, "y":2.5, "label":"DLT Pipeline UI", "sublabel":"Lineage + monitoring","color":"#CE93D8","bg":"#150a20"},
        ],
        "arrows": [
            {"x1":2.6,"y1":5.0,"x2":3.0,"y2":5.5,"color":"#FF6B35"},
            {"x1":2.6,"y1":5.0,"x2":3.0,"y2":4.5,"color":"#FF6B35"},
            {"x1":5.1,"y1":5.8,"x2":6.0,"y2":5.8,"color":"#CD7F32","label":"validate"},
            {"x1":5.1,"y1":4.2,"x2":6.0,"y2":4.2,"color":"#1E88E5"},
            {"x1":8.1,"y1":5.0,"x2":8.9,"y2":5.0,"color":"#FFD700","label":"aggregate"},
            {"x1":11.1,"y1":5.0,"x2":11.5,"y2":5.0,"color":"#00C853","label":"serve"},
            {"x1":7.0,"y1":3.9,"x2":7.0,"y2":3.0,"color":"#CE93D8","style":"arc3,rad=0.0"},
        ],
        "section_labels": [],
    }


# (the rest of diagram functions remain functionally unchanged but with ASCII-normalised strings)
