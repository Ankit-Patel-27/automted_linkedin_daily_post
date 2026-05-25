# LinkedIn Daily Post Bot — Ankit Patel

Automatically publishes a daily LinkedIn post using Groq (Llama 4), tailored
for job hunting as a Senior Data Engineer in Healthcare/Biotech.

Posts every weekday at **9:00 AM IST** via GitHub Actions.

---

## File structure

```
.
├── post_generator.py              # Generates post via Groq API
├── linkedin_poster.py             # Publishes to LinkedIn via UGC API
├── requirements.txt
├── used_topics.json               # Auto-created: tracks post format rotation
├── post_history.json              # Auto-created: published post log
└── .github/
    └── workflows/
        └── daily_post.yml         # GitHub Actions schedule
```

---

## One-time setup

### Step 1 — Get your Groq API key
1. Sign up at https://console.groq.com
2. Create an API key
3. Copy it

### Step 2 — Get LinkedIn API credentials

1. Go to https://www.linkedin.com/developers/ → **Create app**
2. Fill in app name, associate your LinkedIn page, upload a logo
3. Under **Products**, request access to:
   - ✅ Share on LinkedIn
   - ✅ Sign In with LinkedIn using OpenID Connect
4. Go to **Auth** tab → note your `Client ID` and `Client Secret`
5. Generate an access token:
   - Visit: https://www.linkedin.com/developers/tools/oauth/token-generator
   - Select scopes: `openid`, `profile`, `w_member_social`
   - Click **Request access token** → copy the token
6. Get your Person URN:
   - Call: `https://api.linkedin.com/v2/userinfo` with your token
   - Or use: `https://api.linkedin.com/v2/me` — the `id` field gives you the URN
   - Format: `urn:li:person:XXXXXXXXXXXXXXX`

> ⚠️ LinkedIn access tokens expire in **60 days**. Set a calendar reminder to regenerate.

### Step 3 — Add GitHub Secrets

In your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name               | Value                          |
|---------------------------|--------------------------------|
| `GROQ_API_KEY`            | Your Groq API key              |
| `LINKEDIN_ACCESS_TOKEN`   | 60-day OAuth token             |
| `LINKEDIN_PERSON_URN`     | `urn:li:person:XXXXXXXXXXXXXXX`|

### Step 4 — Push to GitHub

```bash
git init
git add .
git commit -m "feat: LinkedIn daily post bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/linkedin-bot.git
git push -u origin main
```

### Step 5 — Test it manually

Go to **Actions** tab in your repo → select **Daily LinkedIn Post** → click **Run workflow**.
Check the logs to confirm the post was generated and published.

---

## Post formats (rotates automatically)

| Format | Description |
|--------|-------------|
| `insight` | Practical lesson from data engineering work |
| `achievement` | Storytelling around a real project win |
| `industry_take` | Opinion on trends in Healthcare data/AI |
| `open_to_work` | Direct, confident job-seeking post |
| `tip` | Mini how-to guide (Spark, AWS, CI/CD, etc.) |
| `project_spotlight` | Deep dive on a specific project |

The bot avoids repeating the same format within 6 posts.

---

## Token renewal reminder

LinkedIn tokens expire every 60 days. To renew:
1. Go to https://www.linkedin.com/developers/tools/oauth/token-generator
2. Generate a new token
3. Update `LINKEDIN_ACCESS_TOKEN` in GitHub Secrets

---

## Running locally

```bash
pip install -r requirements.txt

export GROQ_API_KEY=your_key_here
export LINKEDIN_ACCESS_TOKEN=your_token_here
export LINKEDIN_PERSON_URN=urn:li:person:XXXXXXXXXXXXXXX

python post_generator.py    # generates today_post.json
python linkedin_poster.py   # publishes it
```


---

## New features (v2)

### Telegram notifications
Get notified on your phone for every post, failure, and weekly report.

1. Open Telegram → search **@BotFather** → `/newbot` → follow steps → copy the token
2. Search **@userinfobot** → start it → it shows your Chat ID
3. Add to GitHub Secrets:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From BotFather |
| `TELEGRAM_CHAT_ID` | Your numeric chat ID |

### Trending topics (optional)
For posts that reference current industry news:
1. Sign up free at https://serpapi.com (100 searches/month free)
2. Add `SERPAPI_KEY` to GitHub Secrets

### Token expiry reminder
`token_meta.json` is created automatically on first run and tracks when your LinkedIn token was issued. You'll get a Telegram warning 7 days before it expires.

### Post analytics
`analytics_report.json` is updated daily with likes, comments, shares per post.
A weekly summary is sent to Telegram every Monday.

### First comment
After each technical post, a first comment with the official docs link is added automatically — this boosts LinkedIn reach.

### Retry logic
If LinkedIn API is temporarily down, the poster retries 3 times with 30-second delays before failing.

---

## All GitHub Secrets

| Secret | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Groq API key |
| `LINKEDIN_ACCESS_TOKEN` | ✅ | LinkedIn OAuth token (refresh every 60 days) |
| `LINKEDIN_PERSON_URN` | ✅ | `urn:li:person:YOUR_ID` |
| `TELEGRAM_BOT_TOKEN` | Optional | For phone notifications |
| `TELEGRAM_CHAT_ID` | Optional | Your Telegram chat ID |
| `SERPAPI_KEY` | Optional | For trending topic injection |
