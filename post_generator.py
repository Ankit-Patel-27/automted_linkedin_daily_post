"""
LinkedIn Post Generator - Ankit Patel
Uses Groq (Llama 3.1 70B) to generate daily job-hunting posts for a
Senior Data Engineer / Data Platform Lead in Healthcare/Biotech.
"""

import os
import json
import random
import re
import requests
from datetime import date
from groq import Groq

# ── Profile context ─────────────────────────────────────────────────────────
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

# ── Topic domains - one is picked randomly to focus each post 
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
        ],
    },
]

# ── Post format rotation 
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
            "the given topic. Tell the story: context - problem - solution - impact. "
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


# --- New helpers: sanitize, hashtags, image prompt builder ---

def sanitize_text(text: str) -> str:
    """
    Remove markdown/code fences and backticks but keep the inner content.
    Collapse excessive blank lines and remove bold/italic markers.
    """
    # Remove code fences ```...```
    text = re.sub(r'```(?:\w+\n)?([\s\S]*?)```', r'\1', text)
    # Remove inline backticks `code`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove markdown bold/italic markers
    text = text.replace("**", "").replace("__", "").replace("*", "")
    # Remove markdown headings like ###
    text = re.sub(r'^\s{0,3}#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Collapse 3+ newlines to two
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def pick_hashtags(fmt_type: str, domain_key: str, min_tags=4, max_tags=6) -> str:
    """
    Build a 4-6 hashtag line from the existing sets. Prefer format-specific first,
    then add domain tags, then trim or expand to meet count.
    """
    base = HASHTAG_SETS.get(fmt_type, "").split()
    domain = DOMAIN_HASHTAGS.get(domain_key, "").split()
    # Remove duplicates
    combined = []
    for h in base + domain:
        if h and h not in combined:
            combined.append(h)
    # Trim or pad (if too few tags, keep what we have)
    target = max(min_tags, min(max_tags, len(combined)))
    return " ".join(combined[:target])


def build_image_prompt(domain_key: str, topic: str, fmt_type: str) -> str:
    """
    Build a focused image prompt the image generator can use.
    Keep it short (1-2 sentences) and domain-aware.
    """
    style = ("clean professional infographic suitable for LinkedIn feed; "
             "muted blue/teal palette; high contrast labels; no people; no logos; "
             "minimal text on image; clear icons for data, locks (security), and cloud.")
    if domain_key == "databricks":
        visual = (f"Diagram comparing Unity Catalog vs Hive metastore: "
                  "data lineage arrows, padlock icons for fine-grained access, "
                  "S3 bucket and Delta Lake icons for storage.")
    elif domain_key == "aws":
        visual = (f"Architecture diagram showing S3, Lake Formation, Glue catalog, "
                  "access-control overlays and audit/log icons.")
    elif domain_key == "pyspark":
        visual = (f"Illustration of a Spark execution graph, partitioned data blocks, "
                  "and shuffle arrows with a performance/speed icon.")
    else:
        visual = f"Abstract data platform graphic related to {topic}."
    return f"{visual} {style} Topic: {topic}."


def generate_post(api_key: str) -> dict:
    # Dynamically select the best available model
    model = select_best_model(api_key)
    client = Groq(api_key=api_key)

    used   = load_used_topics()
    fmt    = pick_format(used)
    domain, topic = pick_domain_and_topic(used)

    # enforce 4-6 hashtags
    hashtags_line = pick_hashtags(fmt["type"], domain["domain"])

    system_prompt = f"""You are a LinkedIn ghostwriter specialising in data engineering and cloud careers.
Write in first person as Ankit Patel. Keep posts between 150-250 words. No fluff, no corporate buzzwords.
Write with line breaks for readability (short paragraphs). Include concrete commands or config names when relevant.
Candidate profile:
{PROFILE}
"""

    user_prompt = f"""Today's post format: {fmt['type']}
Today's technical topic: {topic}
Topic domain: {domain['label']}

Instructions: {fmt['instruction']}

Important formatting rules:
- DO NOT use Markdown formatting (no ```, no **bold**, no *italics*, no markdown headings).
- DO NOT output code fences. If you include code examples, output them as plain, unquoted lines (e.g. CREATE DATABASE mydb USING DELTA LOCATION /mnt/secure/data).
- Keep the post plain text, LinkedIn-ready. Use short paragraphs and a final single line with 4-6 hashtags.
- Create a concise, focused image prompt (1-2 sentences) appropriate for a professional LinkedIn infographic illustrating the technical idea.

Output requirement (MANDATORY):
Return ONLY valid JSON, with these exact keys:
{
  "post_text": "<The LinkedIn post plain text, 150-250 words, no markdown>",
  "hashtags": "<single-line of 4-6 hashtags, space-separated>",
  "image_prompt": "<short image prompt for an AI image generator>"
}

Do not include any extra commentary or surrounding text. JSON must be parseable.
"""

    # Lower temperature for more deterministic outputs
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=600,
    )

    raw = response.choices[0].message.content.strip()

    # Robust JSON extraction/parsing fallback
    parsed = None
    try:
        parsed = json.loads(raw)
    except Exception:
        # try to extract the first JSON-looking block
        m = re.search(r'(\{[\s\S]*\})', raw)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                parsed = None

    result_obj = {}
    if parsed and isinstance(parsed, dict):
        # ensure required keys exist, otherwise fallback to sanitized raw
        post_text = parsed.get("post_text", "").strip()
        hashtags = parsed.get("hashtags", "").strip() or hashtags_line
        image_prompt = parsed.get("image_prompt", "").strip() or build_image_prompt(domain["domain"], topic, fmt["type"])
        # sanitize again in case model included stray backticks
        post_text = sanitize_text(post_text)
        result_obj = {
            "text": post_text,
            "format_type": fmt["type"],
            "domain": domain["label"],
            "topic": topic,
            "date": str(date.today()),
            "model_used": model,
            "hashtags": hashtags,
            "image_prompt": image_prompt,
        }
    else:
        # Fallback: sanitize the full raw response and construct hashtags and image prompt
        post_text = sanitize_text(raw)
        image_prompt = build_image_prompt(domain["domain"], topic, fmt["type"])
        result_obj = {
            "text": post_text,
            "format_type": fmt["type"],
            "domain": domain["label"],
            "topic": topic,
            "date": str(date.today()),
            "model_used": model,
            "hashtags": hashtags_line,
            "image_prompt": image_prompt,
        }

    # Save used topic as before
    save_used_topic(fmt["type"], domain["domain"], topic)

    return result_obj


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
