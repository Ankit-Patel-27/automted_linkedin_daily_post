"""
Dynamic Image Generator
- Non-technical posts  → Pollinations AI generates topic-relevant image
- Technical posts      → Python generates a diagram PNG → Pollinations AI
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

# ── Pollinations AI ────────────────────────────────────────────────────────────

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

    # Strict enhancement prompt — preserves content, only improves visuals
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
                print(f"  Attempt {attempt} — status {resp.status_code}, size {len(resp.content)}")
        except Exception as e:
            print(f"  Attempt {attempt} error: {e}")

        if attempt < 3:
            time.sleep(15)

    # Fallback: use original diagram if enhancement fails
    print("⚠ Enhancement failed — using original diagram")
    import shutil
    shutil.copy(diagram_path, output_path)
    return True   # Still return True — original diagram is fine


# ── Non-technical post image prompts ──────────────────────────────────────────

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

    return base_prompt


# ── Dynamic technical diagram generator ───────────────────────────────────────

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

    # ── Databricks configs ──
    if domain == "Databricks":
        if "medallion" in topic_lower or "bronze" in topic_lower or "delta" in topic_lower:
            return _diagram_databricks_medallion()
        elif "dlt" in topic_lower or "live table" in topic_lower:
            return _diagram_databricks_dlt()
        elif "unity" in topic_lower:
            return _diagram_databricks_unity()
        else:
            return _diagram_databricks_medallion()

    # ── AWS configs ──
    elif domain == "AWS":
        if "glue" in topic_lower or "etl" in topic_lower:
            return _diagram_aws_glue()
        elif "kinesis" in topic_lower or "streaming" in topic_lower:
            return _diagram_aws_streaming()
        elif "lake formation" in topic_lower or "phi" in topic_lower:
            return _diagram_aws_lakeformation()
        else:
            return _diagram_aws_glue()

    # ── PySpark configs ──
    elif domain == "PySpark":
        if "join" in topic_lower or "broadcast" in topic_lower:
            return _diagram_spark_joins()
        elif "partition" in topic_lower or "skew" in topic_lower:
            return _diagram_spark_partitions()
        else:
            return _diagram_spark_pipeline()

    # ── SQL / dbt configs ──
    else:
        if "incremental" in topic_lower or "dbt" in topic_lower:
            return _diagram_dbt_incremental()
        elif "scd" in topic_lower or "slowly changing" in topic_lower:
            return _diagram_scd2()
        else:
            return _diagram_dbt_incremental()


# ── Diagram configs ────────────────────────────────────────────────────────────

def _diagram_databricks_medallion():
    return {
        "title":    "Delta Lake — Medallion Architecture",
        "subtitle": "Bronze → Silver → Gold · ACID Transactions · Schema Evolution",
        "accent":   "#FF6B35",
        "nodes": [
            {"x":1.2, "y":5.5, "label":"Kafka / Kinesis",  "sublabel":"Streaming source",  "color":"#FF6B35", "bg":"#1a1500"},
            {"x":1.2, "y":4.2, "label":"S3 / ADLS",        "sublabel":"Batch files",        "color":"#FF6B35", "bg":"#1a1500"},
            {"x":1.2, "y":2.9, "label":"JDBC / APIs",       "sublabel":"Databases",          "color":"#FF6B35", "bg":"#1a1500"},
            {"x":3.8, "y":4.2, "label":"Auto Loader",       "sublabel":"cloudFiles",         "color":"#1E88E5", "bg":"#0a1520"},
            {"x":6.2, "y":5.2, "label":"🥉 Bronze",         "sublabel":"Raw · Append-only",  "color":"#CD7F32", "bg":"#2a1800"},
            {"x":6.2, "y":4.2, "label":"🥈 Silver",         "sublabel":"Cleaned · Z-order",  "color":"#C0C0C0", "bg":"#1a1f2e"},
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
        "subtitle": "Declarative ETL · Auto-scaling · Built-in Quality Checks",
        "accent":   "#FF6B35",
        "nodes": [
            {"x":1.5, "y":5.0, "label":"Raw Sources",     "sublabel":"S3 / Kafka",         "color":"#FF6B35","bg":"#1a1500"},
            {"x":4.0, "y":5.8, "label":"@dlt.table",      "sublabel":"Bronze layer",        "color":"#CD7F32","bg":"#2a1800"},
            {"x":4.0, "y":4.2, "label":"@dlt.view",       "sublabel":"Streaming ingestion", "color":"#1E88E5","bg":"#0a1520"},
            {"x":7.0, "y":5.8, "label":"Expectations",    "sublabel":"Quality checks",      "color":"#F44336","bg":"#1a0a0a"},
            {"x":7.0, "y":4.2, "label":"Silver Table",    "sublabel":"Cleaned / validated", "color":"#C0C0C0","bg":"#1a1f2e"},
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


def _diagram_databricks_unity():
    return {
        "title":    "Databricks Unity Catalog — Data Governance",
        "subtitle": "Metastore · Fine-grained ACL · Lineage · Audit",
        "accent":   "#CE93D8",
        "nodes": [
            {"x":7.0, "y":6.2, "label":"Unity Catalog Metastore","sublabel":"Central governance","color":"#CE93D8","bg":"#150a20","w":3.2},
            {"x":2.5, "y":4.8, "label":"Catalog: prod",      "sublabel":"Production data",    "color":"#1E88E5","bg":"#0a1520"},
            {"x":7.0, "y":4.8, "label":"Catalog: dev",        "sublabel":"Development",        "color":"#1E88E5","bg":"#0a1520"},
            {"x":11.5,"y":4.8, "label":"Catalog: sandbox",    "sublabel":"Experimentation",    "color":"#1E88E5","bg":"#0a1520"},
            {"x":2.5, "y":3.2, "label":"Schema: healthcare",  "sublabel":"PHI / clinical",     "color":"#FF6B35","bg":"#1a1500"},
            {"x":7.0, "y":3.2, "label":"Schema: finance",     "sublabel":"Claims / billing",   "color":"#FF6B35","bg":"#1a1500"},
            {"x":11.5,"y":3.2, "label":"Schema: analytics",   "sublabel":"Aggregated",         "color":"#00C853","bg":"#0a1a0a"},
            {"x":3.5, "y":1.8, "label":"Row/Col Filters",     "sublabel":"PHI masking",        "color":"#F44336","bg":"#1a0a0a"},
            {"x":7.0, "y":1.8, "label":"Data Lineage",        "sublabel":"End-to-end tracking","color":"#FFC107","bg":"#1a1400"},
            {"x":10.5,"y":1.8, "label":"Audit Logs",          "sublabel":"Who accessed what",  "color":"#CE93D8","bg":"#150a20"},
        ],
        "arrows": [
            {"x1":5.6,"y1":6.0,"x2":3.5,"y2":5.2,"color":"#CE93D8"},
            {"x1":7.0,"y1":5.8,"x2":7.0,"y2":5.2,"color":"#CE93D8"},
            {"x1":8.4,"y1":6.0,"x2":10.5,"y2":5.2,"color":"#CE93D8"},
            {"x1":2.5,"y1":4.4,"x2":2.5,"y2":3.6,"color":"#1E88E5"},
            {"x1":7.0,"y1":4.4,"x2":7.0,"y2":3.6,"color":"#1E88E5"},
            {"x1":11.5,"y1":4.4,"x2":11.5,"y2":3.6,"color":"#1E88E5"},
        ],
        "section_labels": [],
    }


def _diagram_aws_glue():
    return {
        "title":    "AWS Glue ETL Pipeline",
        "subtitle": "S3 → Glue → Redshift · Data Catalog · Job Bookmarks",
        "accent":   "#FF9900",
        "nodes": [
            {"x":1.2,"y":5.5,"label":"S3 Raw",          "sublabel":"Landing zone",       "color":"#FF9900","bg":"#1a1500"},
            {"x":1.2,"y":3.8,"label":"RDS / Aurora",     "sublabel":"JDBC source",        "color":"#FF9900","bg":"#1a1500"},
            {"x":3.8,"y":4.8,"label":"Glue Crawler",     "sublabel":"Schema discovery",   "color":"#4fc3f7","bg":"#0a1520"},
            {"x":3.8,"y":3.5,"label":"Glue Catalog",     "sublabel":"Metadata store",     "color":"#4fc3f7","bg":"#0a1520"},
            {"x":6.5,"y":5.5,"label":"Glue ETL Job",     "sublabel":"PySpark / Spark",    "color":"#00C853","bg":"#0a1a0a"},
            {"x":6.5,"y":3.8,"label":"Glue DataBrew",    "sublabel":"No-code transforms", "color":"#00C853","bg":"#0a1a0a"},
            {"x":9.2,"y":5.5,"label":"S3 Curated",       "sublabel":"Parquet / Delta",    "color":"#FF9900","bg":"#1a1500"},
            {"x":9.2,"y":3.8,"label":"S3 Analytics",     "sublabel":"Business-ready",     "color":"#FF9900","bg":"#1a1500"},
            {"x":11.8,"y":5.5,"label":"Redshift",        "sublabel":"Data warehouse",     "color":"#FF9900","bg":"#1a1500"},
            {"x":11.8,"y":3.8,"label":"Athena",          "sublabel":"SQL on S3",          "color":"#4fc3f7","bg":"#0a1520"},
            {"x":6.5, "y":2.2,"label":"Step Functions",  "sublabel":"Orchestration",      "color":"#CE93D8","bg":"#150a20"},
        ],
        "arrows": [
            {"x1":2.3,"y1":5.5,"x2":2.9,"y2":5.0,"color":"#FF9900"},
            {"x1":2.3,"y1":3.8,"x2":2.9,"y2":3.8,"color":"#FF9900"},
            {"x1":4.9,"y1":4.8,"x2":5.4,"y2":5.2,"color":"#4fc3f7","label":"catalog"},
            {"x1":5.4,"y1":5.5,"x2":5.4,"y2":5.5,"color":"#00C853"},
            {"x1":7.6,"y1":5.5,"x2":8.1,"y2":5.5,"color":"#FF9900","label":"write"},
            {"x1":7.6,"y1":3.8,"x2":8.1,"y2":3.8,"color":"#FF9900"},
            {"x1":10.3,"y1":5.5,"x2":10.7,"y2":5.5,"color":"#FF9900","label":"load"},
            {"x1":10.3,"y1":3.8,"x2":10.7,"y2":3.8,"color":"#4fc3f7"},
            {"x1":6.5,"y1":3.4,"x2":6.5,"y2":2.7,"color":"#CE93D8","label":"trigger"},
        ],
        "section_labels": [
            {"x":1.2,"y":1.2,"text":"SOURCES"},
            {"x":3.8,"y":1.2,"text":"CATALOG"},
            {"x":6.5,"y":1.2,"text":"TRANSFORM"},
            {"x":9.2,"y":1.2,"text":"STORE"},
            {"x":11.8,"y":1.2,"text":"SERVE"},
        ],
    }


def _diagram_aws_streaming():
    return {
        "title":    "AWS Real-time Streaming Pipeline",
        "subtitle": "Kinesis Streams → Lambda / Flink → S3 → Redshift",
        "accent":   "#FF9900",
        "nodes": [
            {"x":1.5,"y":5.5,"label":"IoT / Apps",         "sublabel":"Event producers",    "color":"#FF9900","bg":"#1a1500"},
            {"x":1.5,"y":4.0,"label":"HL7 / FHIR",         "sublabel":"Healthcare events",  "color":"#FF9900","bg":"#1a1500"},
            {"x":4.0,"y":5.5,"label":"Kinesis Streams",    "sublabel":"Real-time ingestion", "color":"#4fc3f7","bg":"#0a1520"},
            {"x":4.0,"y":4.0,"label":"MSK (Kafka)",        "sublabel":"Managed Kafka",       "color":"#4fc3f7","bg":"#0a1520"},
            {"x":7.0,"y":6.2,"label":"Lambda",             "sublabel":"Lightweight process", "color":"#00C853","bg":"#0a1a0a"},
            {"x":7.0,"y":4.8,"label":"KDA (Flink)",        "sublabel":"Stateful streaming",  "color":"#00C853","bg":"#0a1a0a"},
            {"x":7.0,"y":3.2,"label":"Firehose",           "sublabel":"Auto-batching",       "color":"#00C853","bg":"#0a1a0a"},
            {"x":10.0,"y":5.5,"label":"S3 Raw",            "sublabel":"Event store",         "color":"#FF9900","bg":"#1a1500"},
            {"x":10.0,"y":4.0,"label":"DynamoDB",          "sublabel":"Low-latency lookup",  "color":"#CE93D8","bg":"#150a20"},
            {"x":12.5,"y":5.0,"label":"Redshift",          "sublabel":"Analytics",           "color":"#FF9900","bg":"#1a1500"},
        ],
        "arrows": [
            {"x1":2.6,"y1":5.5,"x2":2.9,"y2":5.5,"color":"#FF9900"},
            {"x1":2.6,"y1":4.0,"x2":2.9,"y2":4.0,"color":"#FF9900"},
            {"x1":5.1,"y1":5.5,"x2":5.9,"y2":5.9,"color":"#4fc3f7"},
            {"x1":5.1,"y1":4.8,"x2":5.9,"y2":4.8,"color":"#4fc3f7"},
            {"x1":5.1,"y1":4.0,"x2":5.9,"y2":3.5,"color":"#4fc3f7"},
            {"x1":8.1,"y1":6.0,"x2":8.9,"y2":5.7,"color":"#00C853","label":"write"},
            {"x1":8.1,"y1":4.8,"x2":8.9,"y2":4.2,"color":"#00C853"},
            {"x1":8.1,"y1":3.2,"x2":8.9,"y2":3.8,"color":"#00C853"},
            {"x1":11.1,"y1":5.2,"x2":11.4,"y2":5.2,"color":"#FF9900","label":"load"},
        ],
        "section_labels": [],
    }


def _diagram_aws_lakeformation():
    return {
        "title":    "AWS Lake Formation — Healthcare Data Governance",
        "subtitle": "PHI Protection · Fine-grained ACL · Column-level Security",
        "accent":   "#CE93D8",
        "nodes": [
            {"x":7.0,"y":6.5,"label":"Lake Formation",     "sublabel":"Central governance",  "color":"#CE93D8","bg":"#150a20","w":3.2},
            {"x":2.0,"y":5.0,"label":"S3 Data Lake",       "sublabel":"Raw + Curated",       "color":"#FF9900","bg":"#1a1500"},
            {"x":5.5,"y":5.0,"label":"Glue Catalog",       "sublabel":"Metadata",            "color":"#4fc3f7","bg":"#0a1520"},
            {"x":9.0,"y":5.0,"label":"Glue ETL / Athena",  "sublabel":"Processing",          "color":"#00C853","bg":"#0a1a0a"},
            {"x":12.0,"y":5.0,"label":"Redshift",          "sublabel":"Analytics DW",        "color":"#FF9900","bg":"#1a1500"},
            {"x":2.0,"y":3.2,"label":"Data Filters",       "sublabel":"Row / column level",  "color":"#F44336","bg":"#1a0a0a"},
            {"x":5.5,"y":3.2,"label":"Tag-based ACL",      "sublabel":"PHI / PII labels",    "color":"#F44336","bg":"#1a0a0a"},
            {"x":9.0,"y":3.2,"label":"AWS KMS",            "sublabel":"Encryption at rest",  "color":"#FFC107","bg":"#1a1400"},
            {"x":12.0,"y":3.2,"label":"CloudTrail",        "sublabel":"Audit logs",          "color":"#CE93D8","bg":"#150a20"},
            {"x":3.5,"y":1.5,"label":"Data Engineers",     "sublabel":"Read / write",        "color":"#4fc3f7","bg":"#0a1520"},
            {"x":7.0,"y":1.5,"label":"Data Scientists",    "sublabel":"Read only (masked)",  "color":"#00C853","bg":"#0a1a0a"},
            {"x":10.5,"y":1.5,"label":"Compliance Team",   "sublabel":"Audit access",        "color":"#CE93D8","bg":"#150a20"},
        ],
        "arrows": [
            {"x1":5.6,"y1":6.2,"x2":3.1,"y2":5.4,"color":"#CE93D8"},
            {"x1":7.0,"y1":6.1,"x2":7.0,"y2":5.4,"color":"#CE93D8"},
            {"x1":8.4,"y1":6.2,"x2":10.1,"y2":5.4,"color":"#CE93D8"},
            {"x1":2.0,"y1":4.6,"x2":2.0,"y2":3.6,"color":"#F44336","label":"enforce"},
            {"x1":5.5,"y1":4.6,"x2":5.5,"y2":3.6,"color":"#F44336"},
            {"x1":3.1,"y1":5.0,"x2":4.4,"y2":5.0,"color":"#FF9900"},
            {"x1":6.6,"y1":5.0,"x2":7.9,"y2":5.0,"color":"#4fc3f7"},
            {"x1":10.1,"y1":5.0,"x2":10.9,"y2":5.0,"color":"#00C853"},
        ],
        "section_labels": [],
    }


def _diagram_spark_joins():
    return {
        "title":    "PySpark Join Strategies",
        "subtitle": "Broadcast · Sort-Merge · Bucket Join · Skew Handling",
        "accent":   "#E91E8C",
        "nodes": [
            {"x":2.0,"y":6.0,"label":"Large Table",        "sublabel":"500M+ records",       "color":"#E91E8C","bg":"#1a0010"},
            {"x":2.0,"y":4.5,"label":"Small Table",        "sublabel":"< 10MB dim table",    "color":"#E91E8C","bg":"#1a0010"},
            {"x":5.5,"y":6.8,"label":"Sort-Merge Join",    "sublabel":"Default for large×large","color":"#4fc3f7","bg":"#0a1520"},
            {"x":5.5,"y":5.3,"label":"Broadcast Join",     "sublabel":"broadcast(small_df)", "color":"#00C853","bg":"#0a1a0a"},
            {"x":5.5,"y":3.8,"label":"Bucket Join",        "sublabel":"Pre-bucketed tables", "color":"#FFC107","bg":"#1a1400"},
            {"x":5.5,"y":2.3,"label":"Salting",            "sublabel":"Skewed key handling", "color":"#F44336","bg":"#1a0a0a"},
            {"x":9.5,"y":5.8,"label":"Shuffle Stage",      "sublabel":"Network I/O cost",    "color":"#E91E8C","bg":"#1a0010"},
            {"x":9.5,"y":4.3,"label":"No Shuffle ✓",       "sublabel":"Optimal performance", "color":"#00C853","bg":"#0a1a0a"},
            {"x":12.0,"y":5.0,"label":"Result Dataset",    "sublabel":"Joined output",       "color":"#E91E8C","bg":"#1a0010"},
            {"x":3.5,"y":1.0,"label":"df.explain()",       "sublabel":"Check join strategy", "color":"#CE93D8","bg":"#150a20"},
        ],
        "arrows": [
            {"x1":3.1,"y1":5.9,"x2":4.4,"y2":6.5,"color":"#E91E8C"},
            {"x1":3.1,"y1":4.6,"x2":4.4,"y2":5.2,"color":"#E91E8C"},
            {"x1":3.1,"y1":4.4,"x2":4.4,"y2":3.9,"color":"#E91E8C"},
            {"x1":6.6,"y1":6.5,"x2":8.4,"y2":6.0,"color":"#4fc3f7","label":"shuffle"},
            {"x1":6.6,"y1":5.3,"x2":8.4,"y2":4.6,"color":"#00C853","label":"no shuffle"},
            {"x1":6.6,"y1":3.8,"x2":8.4,"y2":4.2,"color":"#FFC107"},
            {"x1":10.6,"y1":5.6,"x2":11.0,"y2":5.2,"color":"#E91E8C"},
            {"x1":10.6,"y1":4.4,"x2":11.0,"y2":4.8,"color":"#00C853"},
        ],
        "section_labels": [
            {"x":2.0,"y":1.0,"text":"INPUTS"},
            {"x":5.5,"y":1.0,"text":"STRATEGY"},
            {"x":9.5,"y":1.0,"text":"SHUFFLE?"},
            {"x":12.0,"y":1.0,"text":"OUTPUT"},
        ],
    }


def _diagram_spark_partitions():
    return {
        "title":    "PySpark Partitioning & Skew Handling",
        "subtitle": "repartition · coalesce · salting · AQE",
        "accent":   "#E91E8C",
        "nodes": [
            {"x":2.0,"y":5.5,"label":"Skewed Data",        "sublabel":"1 partition = 90% data","color":"#F44336","bg":"#1a0a0a"},
            {"x":5.0,"y":6.2,"label":"Salting",            "sublabel":"Add rand() salt key", "color":"#FFC107","bg":"#1a1400"},
            {"x":5.0,"y":5.0,"label":"AQE",                "sublabel":"Auto skew join",      "color":"#4fc3f7","bg":"#0a1520"},
            {"x":5.0,"y":3.8,"label":"repartition(n,key)", "sublabel":"Even distribution",   "color":"#00C853","bg":"#0a1a0a"},
            {"x":8.5,"y":5.5,"label":"Balanced Parts",     "sublabel":"Equal data per task", "color":"#00C853","bg":"#0a1a0a"},
            {"x":11.5,"y":6.2,"label":"coalesce(n)",       "sublabel":"Reduce (no shuffle)", "color":"#E91E8C","bg":"#1a0010"},
            {"x":11.5,"y":5.0,"label":"repartition(n)",    "sublabel":"Increase (shuffle)",  "color":"#E91E8C","bg":"#1a0010"},
            {"x":11.5,"y":3.8,"label":"partitionBy(col)",  "sublabel":"Write partitioning",  "color":"#E91E8C","bg":"#1a0010"},
            {"x":6.5,"y":2.2,"label":"spark.sql.shuffle\n.partitions=200","sublabel":"Default setting","color":"#CE93D8","bg":"#150a20","w":3.5},
        ],
        "arrows": [
            {"x1":3.1,"y1":5.5,"x2":3.9,"y2":5.9,"color":"#F44336","label":"fix with"},
            {"x1":3.1,"y1":5.5,"x2":3.9,"y2":5.1,"color":"#F44336"},
            {"x1":3.1,"y1":5.5,"x2":3.9,"y2":3.9,"color":"#F44336"},
            {"x1":6.1,"y1":5.9,"x2":7.4,"y2":5.7,"color":"#FFC107"},
            {"x1":6.1,"y1":5.0,"x2":7.4,"y2":5.3,"color":"#4fc3f7"},
            {"x1":6.1,"y1":3.8,"x2":7.4,"y2":5.1,"color":"#00C853"},
            {"x1":9.6,"y1":5.5,"x2":10.4,"y2":5.8,"color":"#00C853"},
            {"x1":9.6,"y1":5.5,"x2":10.4,"y2":5.1,"color":"#00C853"},
            {"x1":9.6,"y1":5.5,"x2":10.4,"y2":3.9,"color":"#00C853"},
        ],
        "section_labels": [],
    }


def _diagram_spark_pipeline():
    return {
        "title":    "PySpark Data Processing Pipeline",
        "subtitle": "SparkSession → Read → Transform → Optimise → Write",
        "accent":   "#E91E8C",
        "nodes": [
            {"x":1.5,"y":5.5,"label":"SparkSession",       "sublabel":"AQE + configs",       "color":"#E91E8C","bg":"#1a0010"},
            {"x":3.8,"y":6.2,"label":"Delta Lake Read",    "sublabel":"spark.read.format",   "color":"#AB47BC","bg":"#100010"},
            {"x":3.8,"y":5.0,"label":"JDBC Read",          "sublabel":"Partition pruning",   "color":"#AB47BC","bg":"#100010"},
            {"x":3.8,"y":3.8,"label":"Kafka Stream",       "sublabel":"readStream",          "color":"#AB47BC","bg":"#100010"},
            {"x":6.5,"y":5.5,"label":"Transformations",    "sublabel":"filter/groupBy/join", "color":"#4fc3f7","bg":"#0a1520"},
            {"x":9.0,"y":6.2,"label":"Cache / Persist",    "sublabel":"MEMORY_AND_DISK",     "color":"#FFC107","bg":"#1a1400"},
            {"x":9.0,"y":5.0,"label":"Repartition",        "sublabel":"Balance partitions",  "color":"#FFC107","bg":"#1a1400"},
            {"x":9.0,"y":3.8,"label":"Explain Plan",       "sublabel":"df.explain(cost)",    "color":"#FFC107","bg":"#1a1400"},
            {"x":11.8,"y":5.5,"label":"Delta Write",       "sublabel":"partitionBy(date)",   "color":"#00C853","bg":"#0a1a0a"},
        ],
        "arrows": [
            {"x1":2.6,"y1":5.7,"x2":2.8,"y2":6.0,"color":"#E91E8C"},
            {"x1":2.6,"y1":5.5,"x2":2.8,"y2":5.0,"color":"#E91E8C"},
            {"x1":2.6,"y1":5.3,"x2":2.8,"y2":3.9,"color":"#E91E8C"},
            {"x1":4.9,"y1":5.8,"x2":5.4,"y2":5.7,"color":"#AB47BC"},
            {"x1":4.9,"y1":5.0,"x2":5.4,"y2":5.3,"color":"#AB47BC"},
            {"x1":7.6,"y1":5.7,"x2":7.9,"y2":6.0,"color":"#4fc3f7","label":"optimise"},
            {"x1":7.6,"y1":5.5,"x2":7.9,"y2":5.0,"color":"#4fc3f7"},
            {"x1":7.6,"y1":5.3,"x2":7.9,"y2":3.9,"color":"#4fc3f7"},
            {"x1":10.1,"y1":5.5,"x2":10.7,"y2":5.5,"color":"#00C853","label":"write"},
        ],
        "section_labels": [
            {"x":1.5,"y":1.0,"text":"SESSION"},
            {"x":3.8,"y":1.0,"text":"READ"},
            {"x":6.5,"y":1.0,"text":"TRANSFORM"},
            {"x":9.0,"y":1.0,"text":"OPTIMISE"},
            {"x":11.8,"y":1.0,"text":"WRITE"},
        ],
    }


def _diagram_dbt_incremental():
    return {
        "title":    "dbt Incremental Model Strategy",
        "subtitle": "append · merge · delete+insert · Full Refresh",
        "accent":   "#00BFA5",
        "nodes": [
            {"x":1.5,"y":5.5,"label":"Source Table",       "sublabel":"Raw / staging",       "color":"#FF9900","bg":"#1a1500"},
            {"x":4.5,"y":6.2,"label":"is_incremental()",   "sublabel":"Check run type",      "color":"#00BFA5","bg":"#051510"},
            {"x":4.5,"y":5.0,"label":"Full Refresh",       "sublabel":"--full-refresh flag", "color":"#F44336","bg":"#1a0a0a"},
            {"x":7.5,"y":6.5,"label":"WHERE filter",       "sublabel":"updated_at > max()",  "color":"#00BFA5","bg":"#051510"},
            {"x":7.5,"y":5.3,"label":"SELECT *",           "sublabel":"All records",         "color":"#4fc3f7","bg":"#0a1520"},
            {"x":10.0,"y":6.5,"label":"Merge / Append",    "sublabel":"unique_key upsert",   "color":"#00BFA5","bg":"#051510"},
            {"x":10.0,"y":5.3,"label":"Table Rebuild",     "sublabel":"Drop + recreate",     "color":"#F44336","bg":"#1a0a0a"},
            {"x":12.5,"y":5.8,"label":"dbt Model",         "sublabel":"Materialised table",  "color":"#00C853","bg":"#0a1a0a"},
            {"x":4.5,"y":3.0,"label":"unique_key",         "sublabel":"Dedup strategy",      "color":"#FFC107","bg":"#1a1400"},
            {"x":7.5,"y":3.0,"label":"on_schema_change",   "sublabel":"sync_all_columns",    "color":"#FFC107","bg":"#1a1400"},
            {"x":10.0,"y":3.0,"label":"dbt test",          "sublabel":"not_null · unique",   "color":"#CE93D8","bg":"#150a20"},
        ],
        "arrows": [
            {"x1":2.6,"y1":5.6,"x2":3.4,"y2":6.0,"color":"#FF9900"},
            {"x1":2.6,"y1":5.4,"x2":3.4,"y2":5.1,"color":"#FF9900"},
            {"x1":5.6,"y1":6.2,"x2":6.4,"y2":6.4,"color":"#00BFA5","label":"True"},
            {"x1":5.6,"y1":5.0,"x2":6.4,"y2":5.3,"color":"#F44336","label":"False"},
            {"x1":8.6,"y1":6.5,"x2":8.9,"y2":6.5,"color":"#00BFA5"},
            {"x1":8.6,"y1":5.3,"x2":8.9,"y2":5.3,"color":"#4fc3f7"},
            {"x1":11.1,"y1":6.3,"x2":11.4,"y2":6.0,"color":"#00C853"},
            {"x1":11.1,"y1":5.3,"x2":11.4,"y2":5.6,"color":"#F44336"},
        ],
        "section_labels": [],
    }


def _diagram_scd2():
    return {
        "title":    "Slowly Changing Dimension — Type 2 (SCD2)",
        "subtitle": "dbt Snapshots · dbt_valid_from · dbt_valid_to · is_current",
        "accent":   "#00BFA5",
        "nodes": [
            {"x":1.5,"y":5.5,"label":"Source Record",      "sublabel":"patient_id=101",      "color":"#FF9900","bg":"#1a1500"},
            {"x":4.5,"y":6.2,"label":"Record Unchanged",   "sublabel":"No action",           "color":"#00C853","bg":"#0a1a0a"},
            {"x":4.5,"y":5.0,"label":"Record Changed",     "sublabel":"e.g. address update", "color":"#F44336","bg":"#1a0a0a"},
            {"x":7.5,"y":6.2,"label":"Keep existing row",  "sublabel":"valid_to = NULL",     "color":"#00C853","bg":"#0a1a0a"},
            {"x":7.5,"y":5.5,"label":"Close old row",      "sublabel":"valid_to = today",    "color":"#F44336","bg":"#1a0a0a"},
            {"x":7.5,"y":4.8,"label":"Insert new row",     "sublabel":"valid_from = today",  "color":"#00BFA5","bg":"#051510"},
            {"x":11.0,"y":5.5,"label":"Dim Table",         "sublabel":"Full history",        "color":"#00BFA5","bg":"#051510","w":2.5},
            {"x":3.5,"y":3.0,"label":"dbt snapshot",       "sublabel":"strategy: timestamp", "color":"#CE93D8","bg":"#150a20"},
            {"x":7.5,"y":3.0,"label":"unique_key",         "sublabel":"patient_id",          "color":"#FFC107","bg":"#1a1400"},
            {"x":11.0,"y":3.0,"label":"is_current = True", "sublabel":"Latest row filter",   "color":"#00C853","bg":"#0a1a0a"},
        ],
        "arrows": [
            {"x1":2.6,"y1":5.6,"x2":3.4,"y2":6.0,"color":"#FF9900","label":"compare"},
            {"x1":2.6,"y1":5.4,"x2":3.4,"y2":5.1,"color":"#FF9900"},
            {"x1":5.6,"y1":6.2,"x2":6.4,"y2":6.2,"color":"#00C853"},
            {"x1":5.6,"y1":5.0,"x2":6.4,"y2":5.5,"color":"#F44336"},
            {"x1":5.6,"y1":4.9,"x2":6.4,"y2":4.8,"color":"#F44336"},
            {"x1":8.6,"y1":6.2,"x2":9.7,"y2":5.8,"color":"#00C853"},
            {"x1":8.6,"y1":5.5,"x2":9.7,"y2":5.5,"color":"#F44336"},
            {"x1":8.6,"y1":4.8,"x2":9.7,"y2":5.2,"color":"#00BFA5"},
        ],
        "section_labels": [
            {"x":1.5,"y":1.5,"text":"SOURCE"},
            {"x":4.5,"y":1.5,"text":"CHANGED?"},
            {"x":7.5,"y":1.5,"text":"ACTION"},
            {"x":11.0,"y":1.5,"text":"RESULT"},
        ],
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def get_image_for_post(post_data: dict, output_path: str = "post_image.png") -> bool:
    """
    Main function called by linkedin_poster.py.
    Returns True if image was successfully generated/downloaded.
    """
    domain = post_data.get("domain", "")
    topic  = post_data.get("topic", "")
    fmt    = post_data.get("format_type", "insight")

    if domain in TECHNICAL_DOMAINS:
        # Step 1: generate clean diagram
        raw_diagram = "diagram_raw.png"
        success = generate_technical_diagram(post_data, raw_diagram)

        if success and os.path.exists(raw_diagram):
            # Step 2: enhance with Pollinations AI (content-preserving)
            enhanced = pollinations_enhance_diagram(raw_diagram, topic, domain, output_path)
            return enhanced
        else:
            # Fallback to text-to-image for technical topic
            prompt = (
                f"Professional dark-themed architecture diagram for {domain} "
                f"data engineering, {topic}, technical visualization, "
                f"dark background #0a0e1a, glowing nodes, professional, 4K, no watermark"
            )
            return pollinations_text_to_image(prompt, output_path=output_path)

    else:
        # Non-technical: pure AI image generation
        prompt = build_nontechnical_prompt(post_data)
        return pollinations_text_to_image(prompt, output_path=output_path)


if __name__ == "__main__":
    # Test
    import sys
    test_data = {
        "format_type": sys.argv[1] if len(sys.argv) > 1 else "open_to_work",
        "domain":      sys.argv[2] if len(sys.argv) > 2 else "AWS",
        "topic":       sys.argv[3] if len(sys.argv) > 3 else "AWS Glue vs EMR vs Lambda",
        "text":        "Test post text with emojis 🚀",
        "date":        str(date.today()),
    }
    success = get_image_for_post(test_data, "test_image.png")
    print(f"\n{'✓ Image ready' if success else '✗ Image failed'}: test_image.png")
