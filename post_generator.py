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

# JSON schema for LLM output (defined once to avoid format string issues)
JSON_SCHEMA = """{
  "post_text": string,         // final LinkedIn post text (150-250 words, may include line breaks)
  "image_prompt": string|null, // short focused prompt for the image generator (2-12 words + style), or null
  "hashtags": string           // 4-6 hashtags separated by spaces (will be placed on the last line)
}"""


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


def auto_generate_image_prompt(topic: str, domain_label: str, fmt_type: str) -> str:
    """Create a visual-first prompt when the model doesn't provide one."""
    words = re.findall(r"\w+", topic)
    keywords = " ".join(words[:8])

    style_map = {
        "tip": "numbered step diagram with labeled boxes and arrows, clean infographic layout, blue and teal accents, minimal text",
        "concept_explainer": "numbered step diagram with labeled boxes and arrows, clean infographic layout, blue and teal accents, minimal text",
        "achievement": "before vs after infographic, left and right comparison, clear labels, polished layout, no text overlay",
        "project_spotlight": "before vs after infographic, left and right comparison, clear labels, polished layout, no text overlay",
        "myth_vs_reality": "myth vs reality infographic, split comparison layout, bold labeled columns, clean modern design, no text overlay",
        "insight": "flowchart with labeled boxes and arrows, clean infographic layout, modern presentation, no text overlay",
        "industry_take": "flowchart with labeled boxes and arrows, clean infographic layout, modern presentation, no text overlay",
        "open_to_work": "flowchart with labeled boxes and arrows, clean infographic layout, modern presentation, no text overlay",
    }

    style = style_map.get(fmt_type, style_map["insight"])
    prompt = f"{domain_label} {keywords} — {fmt_type} visual, {style}"
    return prompt


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
    for field in ("post_text", "image_prompt", "hashtags"):
        value = extract_json_string_value(s, field)
        if value is not None:
            recovered[field] = value

    if recovered:
        return json.dumps(recovered)

    return None


def generate_post(api_key: str) -> dict:
    # Dynamically select the best available model
    model = select_best_model(api_key)
    
    client = Groq(api_key=api_key)

    used   = load_used_topics()
    fmt    = pick_format(used)
    domain, topic = pick_domain_and_topic(used)

    default_hashtags = HASHTAG_SETS[fmt["type"]] + "  " + DOMAIN_HASHTAGS[domain["domain"]]

    system_prompt = f"""You are a LinkedIn ghostwriter specialising in data engineering and cloud careers.
You write authentic, visual-first posts for job seekers targeting senior technical roles.
Write in first person as Ankit Patel.
Treat the image as the primary content. The post must read like a short title and takeaway for a diagram-style infographic.
Keep the post extremely short: 20-50 words total, 2-3 short lines max.
Do not write long explanations, stories, or paragraphs. The image should explain the topic almost entirely.
Do not ask the audience to comment, like, share, or follow. Keep it professional and self-contained.
Use line breaks for readability and make the post feel like a polished infographic caption.

Candidate profile:
{PROFILE}
"""

    # Build user prompt with proper handling of the JSON schema
    user_prompt = f"""Today's post format: {fmt['type']}
Today's technical topic: {topic}
Topic domain: {domain['label']}

Instructions: {fmt['instruction']}

Tie the post to the specific topic above. Be concrete — use real command names, API names, or config patterns where relevant. Write as someone who has used this in production at scale.
This is a diagram-first post. The visual should carry the learning. The text should be a short headline + one takeaway only.
Do not write a long paragraph, checklist, or article. Keep it extremely concise and ready to sit under a diagram-style infographic.
Do not include audience engagement prompts such as comments, follows, shares, DM me, or 'let me know'.

IMPORTANT: Output JSON only (no surrounding text). The JSON schema must be:
{JSON_SCHEMA}

If you cannot comply, still output the full post text but it will be sanitised by the poster. Use the hashtags provided earlier if helpful: {default_hashtags}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=700,
    )

    raw = response.choices[0].message.content.strip()

    # Try to parse structured JSON from the model
    parsed = None
    image_prompt = None
    post_text = None
    hashtags = None

    json_str = extract_json_from_text(raw)
    if json_str:
        try:
            parsed = json.loads(json_str)
            post_text = parsed.get("post_text")
            image_prompt = parsed.get("image_prompt")
            hashtags = parsed.get("hashtags")
        except Exception:
            parsed = None

    if not parsed:
        # Fallback: treat entire response as post_text
        post_text = raw
        image_prompt = None
        hashtags = None

    # Sanitize post_text and ensure hashtags line
    final_hashtags = hashtags if isinstance(hashtags, str) and hashtags.strip() else default_hashtags
    post_text_sanitized = sanitize_post_text(post_text, final_hashtags)

    # Ensure image_prompt exists (auto-generate if missing)
    if not image_prompt:
        image_prompt = auto_generate_image_prompt(topic, domain["label"], fmt["type"])

    save_used_topic(fmt["type"], domain["domain"], topic)

    result = {
        "text": post_text_sanitized,
        "format_type": fmt["type"],
        "domain": domain["label"],
        "topic": topic,
        "date": str(date.today()),
        "model_used": model,
        "image_prompt": image_prompt,
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
