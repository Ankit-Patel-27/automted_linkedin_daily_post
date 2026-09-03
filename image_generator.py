import os
import io
import json
import time
import hashlib
import requests
from datetime import date
from urllib.parse import quote


# NOTE: use canonical lowercase keywords for domain detection and do substring match
TECHNICAL_DOMAINS = {"databricks", "aws", "pyspark", "sql"}

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
    # If the post generator already returned a focused image prompt, use it verbatim
    explicit = post_data.get("image_prompt")
    if explicit:
        return explicit

    fmt    = post_data.get("format_type", "insight")
    topic  = post_data.get("topic", "")

    base_prompt = FORMAT_PROMPTS.get(fmt, FORMAT_PROMPTS["insight"])

    # Enrich with topic keywords
    topic_keywords = " ".join(topic.split()[:6]) if topic else ""
    if topic_keywords:
        base_prompt = f"{topic_keywords} concept, {base_prompt}"

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


# -- Main image orchestration function -----------------------------------------

def get_image_for_post(post_data: dict, output_path: str = "post_image.png") -> bool:
    """
    Main orchestration function for image generation.
    
    - For technical domains (Databricks, AWS, PySpark, SQL): generate a diagram and enhance it
    - For non-technical posts: use text-to-image generation
    
    Returns True if image generation succeeded, False otherwise.
    """
    domain = post_data.get("domain", "")
    topic = post_data.get("topic", "")
    
    # Check if this is a technical domain (case-insensitive)
    is_technical = domain.lower() in TECHNICAL_DOMAINS
    
    if is_technical:
        # Technical domain: generate diagram and enhance
        print(f"\n📐 Technical domain detected: {domain}")
        
        # Step 1: Generate raw diagram
        diagram_path = "diagram_raw.png"
        if not generate_technical_diagram(post_data, output_path=diagram_path):
            print(f"⚠ Failed to generate diagram, falling back to text-to-image")
            # Fallback to non-technical image
            prompt = build_nontechnical_prompt(post_data)
            return pollinations_text_to_image(prompt, output_path=output_path)
        
        # Step 2: Enhance the diagram
        if not pollinations_enhance_diagram(diagram_path, topic, domain, output_path=output_path):
            print(f"⚠ Failed to enhance diagram, using raw diagram")
            # Copy raw diagram as fallback
            import shutil
            shutil.copy(diagram_path, output_path)
            return True
        
        return True
    else:
        # Non-technical domain: use text-to-image
        print(f"\n🎨 Non-technical domain: {domain}")
        prompt = build_nontechnical_prompt(post_data)
        return pollinations_text_to_image(prompt, output_path=output_path)


# -- Diagram configs ------------------------------------------------------ [...]

def _diagram_databricks_medallion() -> dict:
    """Databricks medallion architecture (Bronze/Silver/Gold)."""
    return {
        "title": "Databricks Medallion Architecture",
        "subtitle": "Delta Lake Layered Data Pipeline",
        "accent": "#4a90e2",
        "nodes": [
            {"x": 1.5, "y": 3.5, "label": "Raw Data", "sublabel": "(Sources)", "color": "#e24a4a"},
            {"x": 5, "y": 3.5, "label": "Bronze Layer", "sublabel": "(Auto Loader)", "color": "#4a90e2"},
            {"x": 8.5, "y": 3.5, "label": "Silver Layer", "sublabel": "(Transformations)", "color": "#50c878"},
            {"x": 12, "y": 3.5, "label": "Gold Layer", "sublabel": "(Analytics)", "color": "#f4a460"},
        ],
        "arrows": [
            {"x1": 2.3, "y1": 3.5, "x2": 3.8, "y2": 3.5, "color": "#4a90e2"},
            {"x1": 5.8, "y1": 3.5, "x2": 7.7, "y2": 3.5, "color": "#4a90e2"},
            {"x1": 9.3, "y1": 3.5, "x2": 11.2, "y2": 3.5, "color": "#4a90e2"},
        ],
        "section_labels": [],
    }


def _diagram_databricks_dlt() -> dict:
    """Databricks Delta Live Tables (DLT) pipeline."""
    return {
        "title": "Delta Live Tables Pipeline",
        "subtitle": "Declarative ETL with DLT",
        "accent": "#50c878",
        "nodes": [
            {"x": 2, "y": 5, "label": "Source", "color": "#e24a4a"},
            {"x": 2, "y": 3, "label": "Bronze", "sublabel": "(Ingestion)", "color": "#4a90e2"},
            {"x": 5, "y": 4, "label": "Silver", "sublabel": "(Transformation)", "color": "#50c878"},
            {"x": 8, "y": 4, "label": "Gold", "sublabel": "(Aggregation)", "color": "#f4a460"},
            {"x": 8, "y": 2, "label": "BI/Analytics", "color": "#9467bd"},
        ],
        "arrows": [
            {"x1": 2, "y1": 4.3, "x2": 2, "y2": 3.7, "color": "#4a90e2"},
            {"x1": 2.8, "y1": 3, "x2": 4.2, "y2": 3.7, "color": "#4a90e2"},
            {"x1": 5.8, "y1": 4, "x2": 7.2, "y2": 4, "color": "#4a90e2"},
            {"x1": 8, "y1": 3.6, "x2": 8, "y2": 2.6, "color": "#4a90e2"},
        ],
        "section_labels": [],
    }


def _diagram_databricks_unity() -> dict:
    """Databricks Unity Catalog."""
    return {
        "title": "Unity Catalog Governance",
        "subtitle": "Centralized Metadata & Access Control",
        "accent": "#9467bd",
        "nodes": [
            {"x": 3, "y": 5, "label": "Unity Catalog", "sublabel": "(Central Registry)", "color": "#9467bd"},
            {"x": 1, "y": 3.5, "label": "Catalog", "color": "#4a90e2"},
            {"x": 3, "y": 3.5, "label": "Schema", "color": "#4a90e2"},
            {"x": 5, "y": 3.5, "label": "Table", "color": "#4a90e2"},
            {"x": 7, "y": 3.5, "label": "Column Tags", "color": "#e24a4a"},
        ],
        "arrows": [
            {"x1": 3, "y1": 4.6, "x2": 1.5, "y2": 3.8, "color": "#4a90e2"},
            {"x1": 3, "y1": 4.6, "x2": 3, "y2": 3.8, "color": "#4a90e2"},
            {"x1": 3, "y1": 4.6, "x2": 4.5, "y2": 3.8, "color": "#4a90e2"},
            {"x1": 5.8, "y1": 3.5, "x2": 6.2, "y2": 3.5, "color": "#e24a4a"},
        ],
        "section_labels": [],
    }


def _diagram_aws_glue() -> dict:
    """AWS Glue ETL."""
    return {
        "title": "AWS Glue ETL Pipeline",
        "subtitle": "Serverless Data Integration",
        "accent": "#ff9900",
        "nodes": [
            {"x": 1.5, "y": 4, "label": "Data Sources", "color": "#ff9900"},
            {"x": 4, "y": 4, "label": "Glue Crawler", "color": "#ff9900"},
            {"x": 6.5, "y": 4, "label": "Glue Catalog", "color": "#e24a4a"},
            {"x": 9, "y": 4, "label": "Glue Jobs", "color": "#ff9900"},
            {"x": 11.5, "y": 4, "label": "S3 / Redshift", "color": "#4a90e2"},
        ],
        "arrows": [
            {"x1": 2.3, "y1": 4, "x2": 3.2, "y2": 4, "color": "#ff9900"},
            {"x1": 4.8, "y1": 4, "x2": 5.7, "y2": 4, "color": "#ff9900"},
            {"x1": 7.3, "y1": 4, "x2": 8.2, "y2": 4, "color": "#ff9900"},
            {"x1": 9.8, "y1": 4, "x2": 10.7, "y2": 4, "color": "#ff9900"},
        ],
        "section_labels": [],
    }


def _diagram_aws_streaming() -> dict:
    """AWS Kinesis streaming."""
    return {
        "title": "AWS Kinesis Streaming",
        "subtitle": "Real-time Data Ingestion",
        "accent": "#ff9900",
        "nodes": [
            {"x": 2, "y": 4, "label": "Producers", "color": "#e24a4a"},
            {"x": 5, "y": 4, "label": "Kinesis Stream", "color": "#ff9900"},
            {"x": 8, "y": 5, "label": "Lambda", "color": "#ff9900"},
            {"x": 8, "y": 3, "label": "Firehose", "color": "#ff9900"},
            {"x": 11, "y": 4, "label": "S3", "color": "#4a90e2"},
        ],
        "arrows": [
            {"x1": 2.8, "y1": 4, "x2": 4, "y2": 4, "color": "#ff9900"},
            {"x1": 6, "y1": 4.3, "x2": 7.2, "y2": 4.7, "color": "#ff9900"},
            {"x1": 6, "y1": 3.7, "x2": 7.2, "y2": 3.3, "color": "#ff9900"},
            {"x1": 8.8, "y1": 4, "x2": 10.2, "y2": 4, "color": "#ff9900"},
        ],
        "section_labels": [],
    }


def _diagram_aws_lakeformation() -> dict:
    """AWS Lake Formation governance."""
    return {
        "title": "AWS Lake Formation",
        "subtitle": "Secure Data Lake Governance",
        "accent": "#ff9900",
        "nodes": [
            {"x": 3, "y": 5, "label": "Lake Formation", "sublabel": "(Central Hub)", "color": "#ff9900"},
            {"x": 1, "y": 3.5, "label": "Data Catalog", "color": "#4a90e2"},
            {"x": 3, "y": 3.5, "label": "Permissions", "color": "#e24a4a"},
            {"x": 5, "y": 3.5, "label": "Encryption", "color": "#50c878"},
            {"x": 7, "y": 3.5, "label": "Audit Logs", "color": "#9467bd"},
        ],
        "arrows": [
            {"x1": 3, "y1": 4.5, "x2": 1.5, "y2": 3.9, "color": "#ff9900"},
            {"x1": 3, "y1": 4.5, "x2": 3, "y2": 3.9, "color": "#ff9900"},
            {"x1": 3, "y1": 4.5, "x2": 4.5, "y2": 3.9, "color": "#ff9900"},
            {"x1": 5.8, "y1": 3.5, "x2": 6.2, "y2": 3.5, "color": "#ff9900"},
        ],
        "section_labels": [],
    }


def _diagram_spark_joins() -> dict:
    """PySpark join strategies."""
    return {
        "title": "PySpark Join Strategies",
        "subtitle": "Performance Optimization Techniques",
        "accent": "#e24a4a",
        "nodes": [
            {"x": 2, "y": 5, "label": "Broadcast Join", "sublabel": "(Small table)", "color": "#e24a4a"},
            {"x": 5, "y": 5, "label": "Sort-Merge Join", "sublabel": "(Default)", "color": "#4a90e2"},
            {"x": 8, "y": 5, "label": "Shuffle Join", "sublabel": "(Large tables)", "color": "#50c878"},
            {"x": 3.5, "y": 3, "label": "When: <2GB", "color": "#e24a4a"},
            {"x": 5, "y": 3, "label": "When: Medium", "color": "#4a90e2"},
            {"x": 6.5, "y": 3, "label": "When: >10GB", "color": "#50c878"},
        ],
        "arrows": [
            {"x1": 2, "y1": 4.6, "x2": 2.5, "y2": 3.4, "color": "#aaa"},
            {"x1": 5, "y1": 4.6, "x2": 5, "y2": 3.4, "color": "#aaa"},
            {"x1": 8, "y1": 4.6, "x2": 7.5, "y2": 3.4, "color": "#aaa"},
        ],
        "section_labels": [],
    }


def _diagram_spark_partitions() -> dict:
    """PySpark partitioning strategies."""
    return {
        "title": "PySpark Partitioning",
        "subtitle": "Reducing Skew & Improving Performance",
        "accent": "#4a90e2",
        "nodes": [
            {"x": 2, "y": 5, "label": "Data Skew", "sublabel": "(Problem)", "color": "#e24a4a"},
            {"x": 5, "y": 5, "label": "Repartition", "color": "#4a90e2"},
            {"x": 8, "y": 5, "label": "Salting", "sublabel": "(Add randomness)", "color": "#50c878"},
            {"x": 11, "y": 5, "label": "Balanced Data", "sublabel": "(Solution)", "color": "#50c878"},
        ],
        "arrows": [
            {"x1": 2.8, "y1": 5, "x2": 4.2, "y2": 5, "color": "#4a90e2"},
            {"x1": 5.8, "y1": 5, "x2": 7.2, "y2": 5, "color": "#4a90e2"},
            {"x1": 8.8, "y1": 5, "x2": 10.2, "y2": 5, "color": "#4a90e2"},
        ],
        "section_labels": [],
    }


def _diagram_spark_pipeline() -> dict:
    """Generic PySpark pipeline."""
    return {
        "title": "PySpark Data Pipeline",
        "subtitle": "Extract → Transform → Load",
        "accent": "#e24a4a",
        "nodes": [
            {"x": 2, "y": 4, "label": "Extract", "color": "#e24a4a"},
            {"x": 5, "y": 4, "label": "Transform", "color": "#4a90e2"},
            {"x": 8, "y": 4, "label": "Load", "color": "#50c878"},
        ],
        "arrows": [
            {"x1": 2.8, "y1": 4, "x2": 4.2, "y2": 4, "color": "#e24a4a"},
            {"x1": 5.8, "y1": 4, "x2": 7.2, "y2": 4, "color": "#e24a4a"},
        ],
        "section_labels": [],
    }


def _diagram_dbt_incremental() -> dict:
    """dbt incremental models."""
    return {
        "title": "dbt Incremental Models",
        "subtitle": "Full Refresh vs Incremental Strategy",
        "accent": "#50c878",
        "nodes": [
            {"x": 2, "y": 5, "label": "Source Data", "color": "#e24a4a"},
            {"x": 5, "y": 5.5, "label": "Full Refresh", "sublabel": "(Rebuild all)", "color": "#4a90e2"},
            {"x": 5, "y": 4.5, "label": "Incremental", "sublabel": "(New rows only)", "color": "#50c878"},
            {"x": 8, "y": 5, "label": "dbt Model", "color": "#9467bd"},
        ],
        "arrows": [
            {"x1": 2.8, "y1": 5.3, "x2": 4.2, "y2": 5.5, "color": "#4a90e2"},
            {"x1": 2.8, "y1": 4.7, "x2": 4.2, "y2": 4.5, "color": "#4a90e2"},
            {"x1": 5.8, "y1": 5, "x2": 7.2, "y2": 5, "color": "#9467bd"},
        ],
        "section_labels": [],
    }


def _diagram_scd2() -> dict:
    """Slowly Changing Dimensions Type 2."""
    return {
        "title": "SCD Type 2 Implementation",
        "subtitle": "Track Historical Changes with dbt",
        "accent": "#9467bd",
        "nodes": [
            {"x": 2, "y": 4, "label": "Source", "color": "#e24a4a"},
            {"x": 4.5, "y": 5, "label": "Current", "color": "#4a90e2"},
            {"x": 4.5, "y": 3, "label": "Historical", "color": "#9467bd"},
            {"x": 7, "y": 4, "label": "SCD Type 2", "sublabel": "(Merged)", "color": "#50c878"},
        ],
        "arrows": [
            {"x1": 2.8, "y1": 4.3, "x2": 4, "y2": 4.7, "color": "#4a90e2"},
            {"x1": 2.8, "y1": 3.7, "x2": 4, "y2": 3.3, "color": "#9467bd"},
            {"x1": 5.3, "y1": 4.5, "x2": 6.2, "y2": 4.2, "color": "#4a90e2"},
            {"x1": 5.3, "y1": 3.5, "x2": 6.2, "y2": 3.8, "color": "#9467bd"},
        ],
        "section_labels": [],
    }
