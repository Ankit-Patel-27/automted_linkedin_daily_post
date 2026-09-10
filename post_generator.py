"""
LinkedIn Post Generator — Ankit Patel
Uses Groq (Llama 3.1 70B) to generate daily job-hunting posts for a
Senior Data Engineer / Data Platform Lead in Healthcare/Biotech.
"""

from __future__ import annotations

import os
import json
import random
import re
import requests
from datetime import date
from groq import Groq

# -- Profile context -------------------------------------------------------
PROFILE = """
Name: Ankit Patel
Current role: Lead Data Engineer at Tata Consultancy Services (5 years exp)
Target role: Senior Data Engineer / Data Platform Lead
Target industry: Healthcare / Biotech
Key skills: AWS (Glue, Lambda, S3, Redshift, Lake Formation, ECS/EKS),
            Databricks, Apache Spark, PySpark, Delta Lake, dbt, Airflow,
            Terraform, CloudFormation, Docker, GitHub Actions CI/CD,
            LangChain, LLM API integration (Anthropic, OpenAI),
            Kafka, Kinesis, Data Mesh, Data Contracts
Certifications: AWS Certified AI Practitioner, AWS Solutions Architect - Associate,
                AWS Cloud Practitioner
Achievements:
  - 10TB zero-downtime cloud migration, 20% cost reduction
  - 40% ETL runtime reduction on 500M+ daily records
  - 2nd prize GenAI Hackathon (LLMs, LangChain, semantic search)
  - Reusable ETL framework cutting onboarding time by 50%
  - GitHub Actions CI/CD pipelines reducing deployment cycle by 35%
Open to: Senior Data Engineer, Data Platform Lead, or Cloud Data roles
         in Healthcare / Biotech (open to remote/hybrid)
"""

# -- Topic domains - one is picked randomly to focus each post -----------
TOPIC_DOMAINS = [
    {
        "domain": "databricks",
        "label": "Databricks",
        "topics": [
            "Delta Lake ACID transactions and why they matter for healthcare data",
            "Databricks Unity Catalog for data governance in regulated industries",
            "Auto Loader vs COPY INTO for incremental ingestion",
            "Delta Live Tables (DLT) pipelines - declarative ETL in practice",
            "Databricks Photon engine - when it helps and when it doesn't",
            "Z-ordering and liquid clustering for query optimisation",
            "Databricks Workflows vs Apache Airflow - when to use which",
            "Databricks Feature Store for ML pipelines in biotech",
            "Optimising small file problems in Delta Lake",
            "Change Data Feed (CDF) in Delta Lake for CDC pipelines",
            "Delta Sharing for secure cross-team data access",
            "Databricks SQL dashboards for operational analytics",
            "Managing Lakehouse data quality with expectations and alerts",
            "Databricks Repos and CI/CD for governed data projects",
            "Streaming ETL patterns with Auto Loader and Kafka",
            # -- explainer-style topics: map cleanly onto the infographic template --
            "Delta Lake explained simply - what it is and why it exists",
            "Reliable Databricks pipelines - data quality checks that actually catch bad data",
            "End-to-end Databricks Lakehouse architecture, from raw files to dashboards",
            "Medallion architecture explained simply for a non-technical stakeholder",
            "Why Unity Catalog matters - governance for regulated healthcare data",
        ],
    },
    {
        "domain": "aws",
        "label": "AWS",
        "topics": [
            "AWS Glue vs EMR vs Lambda - choosing the right compute for ETL",
            "AWS Lake Formation fine-grained access control for PHI data",
            "S3 lifecycle policies and Intelligent-Tiering for cost optimisation",
            "AWS Glue Data Quality - catching bad data before it hits production",
            "Redshift Spectrum vs Athena - when to query S3 directly",
            "AWS Step Functions for orchestrating multi-step data pipelines",
            "Kinesis Data Streams vs Kafka - real-time ingestion trade-offs",
            "AWS ECS vs EKS for containerised data workloads",
            "CloudFormation vs Terraform for data infrastructure as code",
            "AWS Glue Catalog as a central metadata store",
            "Designing resilient ingestion with EventBridge and Lambda",
            "Amazon Redshift performance tuning for healthcare analytics",
            "AWS Backup and disaster recovery patterns for data platforms",
            "S3 object tagging and lineage for governance at scale",
            "Choosing the right AWS storage layer for analytics workloads",
            # -- explainer-style topics: map cleanly onto the infographic template --
            "Amazon Redshift explained simply - where your data lives for analytics",
            "Reliable AWS data pipelines start with data quality",
            "End-to-end data pipeline on AWS, simple and fully automated",
            "AWS Glue explained simply for a non-technical stakeholder",
            "Why Lake Formation matters for PHI data governance",
        ],
    },
    {
        "domain": "pyspark",
        "label": "PySpark",
        "topics": [
            "PySpark broadcast joins - when and how to use them",
            "Avoiding data skew in PySpark with salting techniques",
            "PySpark UDFs vs Pandas UDFs - performance difference explained",
            "Spark execution plan - how to read and optimise it",
            "Partitioning strategies in PySpark for large-scale ETL",
            "PySpark window functions for time-series healthcare data",
            "Caching and persistence in Spark - .cache() vs .persist()",
            "Spark shuffle - what it is and how to reduce it",
            "Writing efficient PySpark transformations for 500M+ record datasets",
            "PySpark structured streaming for near-real-time pipelines",
            "Optimising joins for large healthcare fact tables",
            "Using dynamic partitions in PySpark for scalable ETL",
            "How to debug slow Spark jobs with UI and plans",
            "Managing stateful streaming jobs in PySpark",
            "Schema evolution strategies in large PySpark pipelines",
            # -- explainer-style topics: map cleanly onto the infographic template --
            "PySpark explained simply - how distributed processing actually works",
            "Reliable PySpark pipelines - catching data quality issues before they scale",
            "End-to-end PySpark ETL pipeline, from raw files to a clean table",
            "Why partitioning strategy matters as your data grows",
        ],
    },
    {
        "domain": "sql",
        "label": "SQL / Analytics Engineering",
        "topics": [
            "Window functions every data engineer should master (RANK, LAG, LEAD)",
            "dbt incremental models - full refresh vs append vs merge strategies",
            "SQL query optimisation patterns for large analytical workloads",
            "CTEs vs subqueries vs temp tables - performance and readability trade-offs",
            "Slowly Changing Dimensions (SCD Type 2) with dbt and Delta Lake",
            "dbt tests and data contracts - enforcing data quality at the model layer",
            "Materialised views in Redshift and Databricks SQL",
            "SQL anti-patterns that kill pipeline performance",
            "Using dbt macros to build reusable SQL components",
            "Designing star schemas for healthcare analytics warehouses",
            "Building reusable semantic layer metrics with dbt",
            "Optimising fact and dimension modelling for BI queries",
            "Data contracts for cross-team analytics handoffs",
            "How to choose between views, materialized views, and tables",
            "Writing readable SQL for high-stakes healthcare reporting",
            # -- explainer-style topics: map cleanly onto the infographic template --
            "dbt explained simply - how a modern analytics engineering workflow works",
            "Reliable analytics starts with data contracts and dbt tests",
            "End-to-end analytics engineering pipeline, from raw tables to a trusted metric",
            "Why a semantic layer matters for cross-team reporting",
        ],
    },
]

# -- Post format rotation -------------------------------------------------
POST_FORMATS = [
    {
        "type": "insight",
        "instruction": (
            "Share a practical technical insight or lesson learned about the given topic. "
            "Write from personal experience. Start with a punchy hook (one bold sentence). "
            "Use short paragraphs (2-3 lines max). End with a question to spark comments."
        ),
    },
    {
        "type": "achievement",
        "instruction": (
            "Highlight one of Ankit's real achievements, tying it to the given topic. "
            "Frame it as 'here's a problem I solved' - the challenge, the approach, "
            "the result. Make it feel human, not like a resume bullet."
        ),
    },
    {
        "type": "industry_take",
        "instruction": (
            "Share a thoughtful, opinionated take on the given topic in the context of "
            "healthcare or biotech data infrastructure. Reference real tools and trade-offs. "
            "Be direct. Avoid buzzwords. Invite debate."
        ),
    },
    {
        "type": "open_to_work",
        "instruction": (
            "Write a genuine, confident 'open to opportunities' post, weaving in the given "
            "technical topic as evidence of Ankit's expertise. Mention target role "
            "(Senior Data Engineer / Data Platform Lead) and healthcare/biotech focus. "
            "Be direct and human. End with a call to connect or share."
        ),
    },
    {
        "type": "concept_explainer",
        "instruction": (
            "Explain the given technical concept clearly for a data engineering audience. "
            "Use an analogy or real-world example. Format as a short explainer with "
            "3-5 key points or steps. Write as someone who has used this in production."
        ),
    },
    {
        "type": "tip",
        "instruction": (
            "Share 3-5 concise, actionable tips about the given topic. "
            "Each tip should be one or two lines. Lead with a strong hook. "
            "End with a CTA (save this, share it, try it today)."
        ),
    },
    {
        "type": "project_spotlight",
        "instruction": (
            "Spotlight a specific project or initiative Ankit worked on that relates to "
            "the given topic. Tell the story: context -> problem -> solution -> impact. "
            "Include real numbers where possible. Keep it authentic."
        ),
    },
    {
        "type": "myth_vs_reality",
        "instruction": (
            "Pick a common misconception or bad practice related to the given topic. "
            "Structure as 'Myth vs Reality' or 'What most people do vs what actually works'. "
            "Be specific and practical. Show real expertise."
        ),
    },
]

HASHTAG_SETS = {
    "insight":           "#DataEngineering #DataPlatform #HealthcareData #TechLeadership",
    "achievement":       "#DataEngineering #CloudMigration #AWS #CareerGrowth #TechLeadership",
    "industry_take":     "#DataEngineering #HealthTech #DataMesh #GenAI #CloudArchitecture",
    "open_to_work":      "#OpenToWork #DataEngineering #AWS #Databricks #HiringNow #HealthcareIT",
    "concept_explainer": "#DataEngineering #LearnInPublic #TechEducation #DataPlatform",
    "tip":               "#DataEngineering #TechTips #LearnInPublic #DataPlatform",
    "project_spotlight": "#DataEngineering #GenAI #Databricks #ProjectShowcase #HealthTech",
    "myth_vs_reality":   "#DataEngineering #BestPractices #DataPlatform #TechTips",
}

# Domain-specific hashtag additions (appended to the base set above)
DOMAIN_HASHTAGS = {
    "databricks": "#Databricks #DeltaLake #ApacheSpark",
    "aws":        "#AWS #CloudEngineering #AWSCloud",
    "pyspark":    "#PySpark #ApacheSpark #BigData",
    "sql":        "#SQL #dbt #AnalyticsEngineering",
}

# Allowed icon names for infographic content - keep in sync with image_icons.py's ICON_KINDS
ALLOWED_ICONS = [
    "check", "cross", "warning", "gear", "shield", "rocket", "bulb",
    "chart", "lock", "target", "database", "star", "magnify", "coin",
    "clock", "refresh", "cloud", "scale", "puzzle", "arrow_up",
]

# JSON schema for LLM output (defined once to avoid format string issues)
JSON_SCHEMA = """{
  "post_text": string,         // short LinkedIn caption (20-50 words, 2-3 lines) - the image carries the content
  "hashtags": string,          // 4-6 hashtags separated by spaces (will be placed on the last line)
  "infographic": {
    "title": string,                 // bold headline, 4-8 words, ALL CAPS, e.g. "RELIABLE PIPELINES START WITH DATA QUALITY"
    "subtitle": string,               // one short supporting line, <=12 words
    "badge": string,                  // 2-4 char label for the corner badge, e.g. "AWS", "PY", "SQL", "DBX"
    "problem_heading": string,        // e.g. "THE REAL PROBLEM"
    "problem_points": [string, string, string, string],  // 4 short pain points, <=6 words each
    "solution_heading": string,       // e.g. "HOW DATA ENGINEERS HANDLE THIS"
    "pipeline_heading": string,       // e.g. "REAL PIPELINE WITH QUALITY CHECKS"
    "pipeline_steps": [{"label": string, "icon": string}, ...],  // 4-5 steps, label <=2 words, icon from the allowed list below
    "why_heading": string,            // e.g. "WHY THIS MATTERS"
    "why_matters": [{"title": string, "desc": string, "icon": string}, ...],  // exactly 4 items, title <=3 words, desc <=6 words
    "mindset_heading": string,        // e.g. "KEY MINDSET OF A DATA ENGINEER"
    "mindset_before": string,         // <=8 words, the naive/common approach
    "mindset_after": string,          // <=8 words, what strong engineers actually do
    "simple_words_heading": string,   // usually "IN SIMPLE WORDS"
    "simple_words_chain": [string, string],  // 2 short phrases, <=2 words each, forming a "X -> Y" takeaway
    "tagline": string                 // short closing line, <=8 words, e.g. "Better data. Better insights. Better impact."
  }
}"""

ICON_HINT = ", ".join(ALLOWED_ICONS)


def get_available_models(api_key: str) -> list:
    """
    Fetch available models from Groq API.
    Returns a list of model objects.
    """
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching models from Groq API: {e}")
        return []


def select_best_model(api_key: str) -> str:
    """
    Dynamically select the best available model from Groq.
    Prioritizes models that support vision/image capabilities.
    Falls back to the most capable text model if no vision model is available.
    """
    models = get_available_models(api_key)
    
    if not models:
        print("⚠️  No models found from Groq API. Using fallback model.")
        return "llama-3.3-70b-versatile"
    
    # Models with vision/image capabilities (prioritized)
    vision_models = []
    # Models without vision but still capable
    text_models = []
    
    for model in models:
        model_id = model.get("id", "")
        # Check if model supports vision (common patterns in model names)
        if any(keyword in model_id.lower() for keyword in ["vision", "image", "multimodal"]):
            vision_models.append(model_id)
        else:
            text_models.append(model_id)
    
    # Prefer vision-capable models
    if vision_models:
        selected = vision_models[0]
        print(f"✓ Selected vision-capable model: {selected}")
        return selected
    
    # Fall back to best text model (usually the most recent or capable)
    if text_models:
        selected = text_models[0]
        print(f"✓ Selected text model: {selected}")
        return selected
    
    # Last resort fallback
    print("⚠️  Falling back to hardcoded model: llama-3.3-70b-versatile")
    return "llama-3.3-70b-versatile"


def load_used_topics(path="used_topics.json"):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_used_topic(format_type, domain, topic, path="used_topics.json"):
    topics = load_used_topics(path)
    topics.append({
        "type": format_type,
        "domain": domain,
        "topic": topic,
        "date": str(date.today()),
    })
    # Keep last 40 entries
    topics = topics[-40:]
    with open(path, "w") as f:
        json.dump(topics, f, indent=2)


def pick_format(used_topics):
    """Pick a format not used in the last 6 posts."""
    recent_types = [t["type"] for t in used_topics[-6:]]
    available = [f for f in POST_FORMATS if f["type"] not in recent_types]
    if not available:
        available = POST_FORMATS
    return random.choice(available)


def pick_hashtags(format_type: str, domain: str) -> str:
    """Return a compact hashtag set suitable for the post."""
    base_tags = HASHTAG_SETS.get(format_type, HASHTAG_SETS["insight"]).split()
    domain_tags = DOMAIN_HASHTAGS.get(domain.lower(), "").split()
    tags = (base_tags + domain_tags)[:6]
    return " ".join(tags)


def pick_domain_and_topic(used_topics):
    """
    Pick a domain, then a topic within it.
    - Avoids repeating the same domain 2 posts in a row.
    - Avoids repeating a specific topic seen in the last 40 posts.
    """
    recent_domains = [t.get("domain") for t in used_topics[-2:]]
    recent_topics  = {t.get("topic") for t in used_topics[-40:]}

    # Filter out the domain used in the last 2 posts if possible
    available_domains = [d for d in TOPIC_DOMAINS if d["domain"] not in recent_domains]
    if not available_domains:
        available_domains = TOPIC_DOMAINS

    domain = random.choice(available_domains)

    # Filter out recently used specific topics
    available_topics = [t for t in domain["topics"] if t not in recent_topics]
    if not available_topics:
        available_topics = domain["topics"]

    topic = random.choice(available_topics)
    return domain, topic


def sanitize_text(s: str, default_hashtags: str = "") -> str:
    """Compatibility wrapper used by the existing tests."""
    if not s:
        return ""
    return sanitize_post_text(s, default_hashtags or "#DataEngineering #DataPlatform")


def sanitize_post_text(s: str, default_hashtags: str) -> str:
    """Sanitize raw model output into a LinkedIn-ready post text.

    - Remove fenced code blocks
    - Strip malformed JSON wrappers, duplicate post_text chunks, and stray braces/quotes
    - Collapse extra blank lines
    - Ensure hashtags are on the last line
    - Keep the final caption concise and image-friendly
    """
    if not s:
        return ""

    s = s.strip()
    s = s.replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'")

    # Remove fenced code blocks ``` ``` and ```lang
    s = re.sub(r"```[\s\S]*?```", "", s)
    s = re.sub(r"`", "", s)
    s = s.replace("**", "")

    # Drop common malformed JSON wrappers repeatedly produced by the model.
    s = re.sub(r'(?s)^\s*\{\s*"?post_text"?\s*:\s*', '', s, count=1)
    s = re.sub(r'(?s)\{\s*"?post_text"?\s*:\s*', '', s)
    s = re.sub(r'(?s)\{\s*"?image_prompt"?\s*:\s*', '', s)
    s = re.sub(r'(?s)\{\s*"?hashtags"?\s*:\s*', '', s)
    s = re.sub(r'(?s)\s*\}\s*$', '', s)
    s = re.sub(r'(?s)\s*"\s*\}\s*', '', s)

    # Trim stray leading/trailing quotes/braces caused by mixed JSON and text output.
    s = re.sub(r'(?s)^\s*[{\[]+', '', s)
    s = re.sub(r'(?s)[}\]]+\s*$', '', s)
    s = re.sub(r'(?s)^\s*[\"\']+', '', s)
    s = re.sub(r'(?s)[\"\']+\s*$', '', s)

    # Collapse excessive blank lines
    s = re.sub(r"\n\s*\n+", "\n\n", s).strip()

    # Extract hashtags and remove them from body
    tags = re.findall(r"(?:#\w[\w-]*)", s)
    body = re.sub(r"(?:#\w[\w-]*)", "", s).strip()

    # Prefer default hashtags if none found or too many/too few
    if 4 <= len(tags) <= 6:
        hashtags_line = " ".join(tags[:6])
    else:
        hashtags_line = default_hashtags

    # Keep posts concise and visually oriented.
    words = body.split()
    if len(words) > 80:
        truncated = " ".join(words[:80])
        m = re.search(r"(.+[\.\!\?])\s+[^\.\!\?]*$", truncated)
        if m:
            body = m.group(1)
        else:
            body = truncated

    body = re.sub(r'\s+', ' ', body).strip()
    final = body.rstrip() + "\n\n" + hashtags_line
    return final



def extract_json_string_value(s: str, field: str) -> str | None:
    """Extract a JSON string field value from malformed model output."""
    pattern = rf'"{field}"\s*:\s*"((?:\\.|[^"\\])*)"'
    match = re.search(pattern, s)
    if not match:
        return None
    try:
        return json.loads(f'"{match.group(1)}"')
    except Exception:
        return None


def extract_json_from_text(s: str) -> str | None:
    """Try to extract a JSON object substring from a model response.

    Returns the JSON string if found, else None.
    """
    # First try direct parse
    try:
        json.loads(s)
        return s
    except Exception:
        pass

    # Try to recover a structured payload even when the model returns
    # malformed nested JSON or duplicated post_text fragments.
    recovered = {}
    for field in ("post_text", "hashtags"):
        value = extract_json_string_value(s, field)
        if value is not None:
            recovered[field] = value

    if recovered:
        return json.dumps(recovered)

    return None


# -- Infographic fallback content ------------------------------------------
# Used to fill in any field the model leaves out or gets wrong, so the
# renderer never receives a broken/incomplete infographic payload.

DOMAIN_PIPELINE_DEFAULTS = {
    "databricks": [
        {"label": "Raw Data", "icon": "database"}, {"label": "Bronze", "icon": "gear"},
        {"label": "Silver", "icon": "refresh"}, {"label": "Gold", "icon": "chart"},
    ],
    "aws": [
        {"label": "Amazon S3", "icon": "database"}, {"label": "Lambda", "icon": "gear"},
        {"label": "Glue", "icon": "refresh"}, {"label": "Redshift", "icon": "database"},
        {"label": "Analytics", "icon": "chart"},
    ],
    "pyspark": [
        {"label": "Extract", "icon": "database"}, {"label": "Transform", "icon": "gear"},
        {"label": "Optimize", "icon": "refresh"}, {"label": "Load", "icon": "chart"},
    ],
    "sql": [
        {"label": "Source", "icon": "database"}, {"label": "Model", "icon": "gear"},
        {"label": "Test", "icon": "check"}, {"label": "Serve", "icon": "chart"},
    ],
}

DOMAIN_BADGE = {"databricks": "DBX", "aws": "AWS", "pyspark": "PY", "sql": "SQL"}


def build_fallback_infographic(topic: str, domain_key: str, domain_label: str, fmt_type: str) -> dict:
    """A complete, safe-to-render infographic payload built from the topic alone.
    Used to fill any gaps left by the model's JSON output."""
    short_topic = topic.split(" - ")[0].split(" – ")[0]
    return {
        "title": short_topic.upper(),
        "subtitle": f"A practical look for data engineers working with {domain_label}",
        "badge": DOMAIN_BADGE.get(domain_key, domain_label[:4].upper()),
        "problem_heading": "THE REAL PROBLEM",
        "problem_points": [
            "Inconsistent or messy inputs", "Manual, error-prone steps",
            "Hard to scale reliably", "Costly to fix downstream",
        ],
        "solution_heading": "HOW DATA ENGINEERS HANDLE THIS",
        "pipeline_heading": f"A REAL {domain_label.upper()} WORKFLOW",
        "pipeline_steps": DOMAIN_PIPELINE_DEFAULTS.get(domain_key, DOMAIN_PIPELINE_DEFAULTS["sql"]),
        "why_heading": "WHY THIS MATTERS",
        "why_matters": [
            {"title": "Builds Trust", "desc": "Stakeholders trust the data", "icon": "shield"},
            {"title": "Saves Time", "desc": "Less rework, fewer re-runs", "icon": "clock"},
            {"title": "Cost Efficient", "desc": "Less wasted compute & storage", "icon": "coin"},
            {"title": "Scales Well", "desc": "Holds up as data grows", "icon": "chart"},
        ],
        "mindset_heading": "KEY MINDSET OF A DATA ENGINEER",
        "mindset_before": "Anyone can move data around.",
        "mindset_after": "Great engineers build systems that hold up.",
        "simple_words_heading": "IN SIMPLE WORDS",
        "simple_words_chain": [domain_label, "Reliable Data"],
        "tagline": "Better data. Better insights. Better impact.",
    }


def _sanitize_icon(icon) -> str:
    if isinstance(icon, str) and icon.lower() in ALLOWED_ICONS:
        return icon.lower()
    return "check"


def merge_infographic(parsed_info, topic: str, domain_key: str, domain_label: str, fmt_type: str) -> dict:
    """Merge the model's infographic JSON over a safe fallback, field by field."""
    fallback = build_fallback_infographic(topic, domain_key, domain_label, fmt_type)
    info = parsed_info if isinstance(parsed_info, dict) else {}

    def s(key, maxlen=None):
        v = info.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()[:maxlen] if maxlen else v.strip()
        return fallback[key]

    out = {
        "title": s("title", 70),
        "subtitle": s("subtitle", 90),
        "badge": s("badge", 4).upper(),
        "problem_heading": s("problem_heading", 40),
        "solution_heading": s("solution_heading", 50),
        "pipeline_heading": s("pipeline_heading", 60),
        "why_heading": s("why_heading", 30),
        "mindset_heading": s("mindset_heading", 50),
        "mindset_before": s("mindset_before", 60),
        "mindset_after": s("mindset_after", 70),
        "simple_words_heading": s("simple_words_heading", 30),
        "tagline": s("tagline", 70),
    }

    pts = info.get("problem_points")
    if isinstance(pts, list) and len(pts) >= 3:
        out["problem_points"] = [str(p)[:60] for p in pts[:4]]
    else:
        out["problem_points"] = fallback["problem_points"]

    steps = info.get("pipeline_steps")
    if isinstance(steps, list) and len(steps) >= 3:
        out["pipeline_steps"] = [
            {"label": str(st.get("label", "Step"))[:16], "icon": _sanitize_icon(st.get("icon"))}
            for st in steps[:5] if isinstance(st, dict)
        ] or fallback["pipeline_steps"]
    else:
        out["pipeline_steps"] = fallback["pipeline_steps"]

    why = info.get("why_matters")
    if isinstance(why, list) and len(why) >= 3:
        out["why_matters"] = [
            {"title": str(w.get("title", ""))[:24], "desc": str(w.get("desc", ""))[:40],
             "icon": _sanitize_icon(w.get("icon"))}
            for w in why[:4] if isinstance(w, dict)
        ] or fallback["why_matters"]
    else:
        out["why_matters"] = fallback["why_matters"]

    chain = info.get("simple_words_chain")
    if isinstance(chain, list) and len(chain) >= 2:
        out["simple_words_chain"] = [str(c)[:16] for c in chain[:2]]
    else:
        out["simple_words_chain"] = fallback["simple_words_chain"]

    return out


def generate_post(api_key: str) -> dict:
    # Dynamically select the best available model
    model = select_best_model(api_key)
    
    client = Groq(api_key=api_key)

    used   = load_used_topics()
    fmt    = pick_format(used)
    domain, topic = pick_domain_and_topic(used)

    default_hashtags = HASHTAG_SETS[fmt["type"]] + "  " + DOMAIN_HASHTAGS[domain["domain"]]

    system_prompt = f"""You are a LinkedIn ghostwriter and infographic content designer specialising in data engineering and cloud careers.
You produce two things for each post: (1) a short LinkedIn caption, and (2) the structured content for a premium, multi-section
LinkedIn infographic image (think: bold headline banner, "the real problem" section with pain points, a pipeline/flow diagram
with 4-5 labeled steps, a "why this matters" card grid, a "key mindset" before/after comparison, and an "in simple words" closing
banner — the exact style of a polished AWS/Databricks explainer carousel graphic).
Write in first person as Ankit Patel where the caption calls for it.
The image is the primary content — keep the caption extremely short: 20-50 words, 2-3 short lines max, no long explanations.
Do not ask the audience to comment, like, share, or follow. Keep it professional and self-contained.

Every field in the "infographic" object must be filled in and specific to today's topic — write like an engineer who has actually
used this in production, with concrete tool/API/config names where relevant. Keep every field within its stated word limit so it
fits its box in the layout. For every "icon" field, choose ONLY from this exact list: {ICON_HINT}.

Candidate profile:
{PROFILE}
"""

    # Build user prompt with proper handling of the JSON schema
    user_prompt = f"""Today's post format: {fmt['type']}
Today's technical topic: {topic}
Topic domain: {domain['label']}

Caption instructions: {fmt['instruction']}
Keep the caption to a short headline + one takeaway — the infographic image carries the actual explanation, not the caption.
Do not include audience engagement prompts such as comments, follows, shares, DM me, or 'let me know'.

Tie every infographic field to the specific topic above — no generic filler. Follow the word/item-count limits in the schema exactly
so the layout doesn't overflow. pipeline_steps should reflect a real, ordered technical flow for this topic (e.g. real AWS/Databricks/
Spark/SQL service or step names). why_matters must have exactly 4 items.

IMPORTANT: Output JSON only (no surrounding text, no markdown fences). The JSON schema must be:
{JSON_SCHEMA}

Use the hashtags provided earlier if helpful: {default_hashtags}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()

    # Try to parse structured JSON from the model
    parsed = None
    post_text = None
    hashtags = None
    infographic_raw = None

    json_str = extract_json_from_text(raw)
    if json_str:
        try:
            parsed = json.loads(json_str)
            post_text = parsed.get("post_text")
            hashtags = parsed.get("hashtags")
            infographic_raw = parsed.get("infographic")
        except Exception:
            parsed = None

    if not parsed:
        # Fallback: treat entire response as post_text
        post_text = raw
        hashtags = None
        infographic_raw = None

    # Sanitize post_text and ensure hashtags line
    final_hashtags = hashtags if isinstance(hashtags, str) and hashtags.strip() else default_hashtags
    post_text_sanitized = sanitize_post_text(post_text, final_hashtags)

    # Merge model infographic content over a safe fallback so the renderer
    # always gets a complete, on-topic payload even on partial LLM output.
    infographic = merge_infographic(infographic_raw, topic, domain["domain"], domain["label"], fmt["type"])

    save_used_topic(fmt["type"], domain["domain"], topic)

    result = {
        "text": post_text_sanitized,
        "format_type": fmt["type"],
        "domain": domain["label"],
        "topic": topic,
        "date": str(date.today()),
        "model_used": model,
        "hashtags": final_hashtags,
        "infographic": infographic,
        "raw_llm": raw,
    }

    return result


if __name__ == "__main__":
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    result = generate_post(api_key)
    print(f"\n{'='*60}")
    print(f"Format : {result['format_type']}")
    print(f"Domain : {result['domain']}")
    print(f"Topic  : {result['topic']}")
    print(f"Date   : {result['date']}")
    print(f"Model  : {result['model_used']}")
    print(f"{'='*60}\n")
    print(result["text"])

    # Save post for the poster script to pick up
    with open("today_post.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n✓ Saved to today_post.json")
