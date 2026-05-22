"""
LinkedIn Post Generator — Ankit Patel
Uses Groq (Llama 4) to generate daily job-hunting posts for a
Senior Data Engineer / Data Platform Lead in Healthcare/Biotech.
"""

import os
import json
import random
from datetime import date
from groq import Groq

# ── Profile context ────────────────────────────────────────────────────────────
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
Certifications: AWS Certified AI Practitioner, AWS Solutions Architect – Associate,
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

# ── Topic domains — one is picked randomly to focus each post ─────────────────
TOPIC_DOMAINS = [
    {
        "domain": "databricks",
        "label": "Databricks",
        "topics": [
            "Delta Lake ACID transactions and why they matter for healthcare data",
            "Databricks Unity Catalog for data governance in regulated industries",
            "Auto Loader vs COPY INTO for incremental ingestion",
            "Delta Live Tables (DLT) pipelines — declarative ETL in practice",
            "Databricks Photon engine — when it helps and when it doesn't",
            "Z-ordering and liquid clustering for query optimisation",
            "Databricks Workflows vs Apache Airflow — when to use which",
            "Databricks Feature Store for ML pipelines in biotech",
            "Optimising small file problems in Delta Lake",
            "Change Data Feed (CDF) in Delta Lake for CDC pipelines",
        ],
    },
    {
        "domain": "aws",
        "label": "AWS",
        "topics": [
            "AWS Glue vs EMR vs Lambda — choosing the right compute for ETL",
            "AWS Lake Formation fine-grained access control for PHI data",
            "S3 lifecycle policies and Intelligent-Tiering for cost optimisation",
            "AWS Glue Data Quality — catching bad data before it hits production",
            "Redshift Spectrum vs Athena — when to query S3 directly",
            "AWS Step Functions for orchestrating multi-step data pipelines",
            "Kinesis Data Streams vs Kafka — real-time ingestion trade-offs",
            "AWS ECS vs EKS for containerised data workloads",
            "CloudFormation vs Terraform for data infrastructure as code",
            "AWS Glue Catalog as a central metadata store",
        ],
    },
    {
        "domain": "pyspark",
        "label": "PySpark",
        "topics": [
            "PySpark broadcast joins — when and how to use them",
            "Avoiding data skew in PySpark with salting techniques",
            "PySpark UDFs vs Pandas UDFs — performance difference explained",
            "Spark execution plan — how to read and optimise it",
            "Partitioning strategies in PySpark for large-scale ETL",
            "PySpark window functions for time-series healthcare data",
            "Caching and persistence in Spark — .cache() vs .persist()",
            "Spark shuffle — what it is and how to reduce it",
            "Writing efficient PySpark transformations for 500M+ record datasets",
            "PySpark structured streaming for near-real-time pipelines",
        ],
    },
    {
        "domain": "sql",
        "label": "SQL / Analytics Engineering",
        "topics": [
            "Window functions every data engineer should master (RANK, LAG, LEAD)",
            "dbt incremental models — full refresh vs append vs merge strategies",
            "SQL query optimisation patterns for large analytical workloads",
            "CTEs vs subqueries vs temp tables — performance and readability trade-offs",
            "Slowly Changing Dimensions (SCD Type 2) with dbt and Delta Lake",
            "dbt tests and data contracts — enforcing data quality at the model layer",
            "Materialised views in Redshift and Databricks SQL",
            "SQL anti-patterns that kill pipeline performance",
            "Using dbt macros to build reusable SQL components",
            "Designing star schemas for healthcare analytics warehouses",
        ],
    },
]

# ── Post format rotation ───────────────────────────────────────────────────────
POST_FORMATS = [
    {
        "type": "insight",
        "instruction": (
            "Share a practical technical insight or lesson learned about the given topic. "
            "Write from personal experience. Start with a punchy hook (one bold sentence). "
            "Use short paragraphs (2–3 lines max). End with a question to spark comments."
        ),
    },
    {
        "type": "achievement",
        "instruction": (
            "Highlight one of Ankit's real achievements, tying it to the given topic. "
            "Frame it as 'here's a problem I solved' — the challenge, the approach, "
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
            "3–5 key points or steps. Write as someone who has used this in production."
        ),
    },
    {
        "type": "tip",
        "instruction": (
            "Share 3–5 concise, actionable tips about the given topic. "
            "Each tip should be one or two lines. Lead with a strong hook. "
            "End with a CTA (save this, share it, try it today)."
        ),
    },
    {
        "type": "project_spotlight",
        "instruction": (
            "Spotlight a specific project or initiative Ankit worked on that relates to "
            "the given topic. Tell the story: context → problem → solution → impact. "
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


def generate_post(api_key: str) -> dict:
    client = Groq(api_key=api_key)

    used   = load_used_topics()
    fmt    = pick_format(used)
    domain, topic = pick_domain_and_topic(used)

    hashtags = (
        HASHTAG_SETS[fmt["type"]] + "  " + DOMAIN_HASHTAGS[domain["domain"]]
    )

    system_prompt = f"""You are a LinkedIn ghostwriter specialising in data engineering and cloud careers.
You write authentic, engaging posts for job seekers targeting senior technical roles.
Write in first person as Ankit Patel.
Keep posts between 150–250 words. No fluff, no corporate buzzwords.
Use line breaks for readability. End with 4–6 relevant hashtags on the last line.

Candidate profile:
{PROFILE}
"""

    user_prompt = f"""Today's post format: {fmt['type']}
Today's technical topic: {topic}
Topic domain: {domain['label']}

Instructions: {fmt['instruction']}

Tie the post to the specific topic above. Be concrete — use real command names,
API names, or config patterns where relevant. Write as someone who has used this
in production at scale.

Use these hashtags at the end (all on one line): {hashtags}

Write the full LinkedIn post now. Output only the post text, nothing else.
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_tokens=600,
    )

    post_text = response.choices[0].message.content.strip()
    save_used_topic(fmt["type"], domain["domain"], topic)

    return {
        "text": post_text,
        "format_type": fmt["type"],
        "domain": domain["label"],
        "topic": topic,
        "date": str(date.today()),
    }


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
    print(f"{'='*60}\n")
    print(result["text"])

    # Save post for the poster script to pick up
    with open("today_post.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n✓ Saved to today_post.json")
