# Digital Bridge Assistant
**ALX Digital Bridge Accessibility Hackathon 2026 — Track 3: Multilingual Assistant and Live Help**  
**Lead & Knowledge Base:** Kidus | **Widget & Chat Sessions:** Koket | **AI Engine & Channels:** Samuel | **Support & Careers:** Yensew  

---

## What It Does
Digital Bridge Assistant is a lightweight, accessible learner-support plugin for existing learning management platforms, starting with ALX Savanna. It provides:
1. **Evidence-grounded course tutoring** in Amharic and English, citing actual lesson sections and refusing to hallucinate when evidence is missing.
2. **Unified communication channels:** Web widget, Telegram bot, and low-bandwidth SMS on a single central Django intelligence backend with offline keyword and curated FAQ fallbacks.
3. **One-click human escalation & live help:** Learner-controlled handoff to human support agents with explicit chat consent boundaries, learner-controlled screen sharing, and low-bandwidth screen snapshot fallback.
4. **Career Gateway & Accommodations:** Search and grounded Q&A for job opportunities, interview accommodation requests requiring **zero medical diagnoses**, and outbound job alert notifications via Telegram and 160-char SMS.

---

## The Main Tasks We Tested
> *"A blind or low-connectivity learner asks a course question in Amharic or English via Telegram or low-bandwidth SMS, receives an evidence-grounded answer citing the exact lesson section, and has an immediate route to human escalation if the material cannot verify the answer."*
>
> *"A learner encounters an accessibility barrier or complex problem on a Savanna course page, escalates to a human agent with one click, controls screen sharing with a persistent stop control, and discovers accessible job opportunities with private interview accommodations."*

---

## Run It

### Option A: Local Development Environment
```bash
# 1. Clone & switch to feature branch
git checkout feature/yensew-support-careers

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Apply migrations
python backend/manage.py migrate

# 4. Seed demo data (Support tickets, Ethiopian jobs, accommodations, subscriptions)
python backend/manage.py seed_careers_and_support

# 5. Run automated tests (45 unit & integration tests)
pytest

# 6. Start the backend development server
python backend/manage.py runserver 0.0.0.0:8000
```
- Interactive Swagger UI: [http://localhost:8000/docs/](http://localhost:8000/docs/)
- Redoc Documentation: [http://localhost:8000/redoc/](http://localhost:8000/redoc/)
- OpenAPI 3.0 Schema: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

### Option B: Docker Compose
```bash
docker compose up --build
```
Open [http://localhost:8000/docs/](http://localhost:8000/docs/) in your browser.

### Option C: Run Telegram Bot (Long-Polling Mode for Demo Laptops)
To demonstrate the Telegram bot without needing a public IP or webhook tunnel:
```bash
# Add your BotFather token to .env: TELEGRAM_BOT_TOKEN=...
python backend/manage.py run_telegram_bot
```

---

## Install, Level 1: Web Embed

The widget can be added to any HTML or LMS page with a single script tag:
```html
<!-- Digital Bridge Assistant Web Component -->
<script src="http://localhost:8000/static/widget/bridge.js" defer></script>
<db-assistant lang="am" api="http://localhost:8000"></db-assistant>
```

---

## Install, Level 2: REST API & Curl Examples

OpenAPI 3.0 specification is available at `openapi.yaml`.

### 1. Check AI Engine Health & Provider Status
```bash
curl -X GET http://localhost:8000/api/v1/ai/status/
```
**Response:**
```json
{
  "status": "healthy",
  "active_provider": "offline",
  "supported_providers": ["offline", "cloud", "local", "mock"],
  "grounding_threshold": 0.25,
  "supported_languages": ["am", "en"],
  "offline_fallback_enabled": true
}
```

### 2. Generate Grounded Course Answer (Amharic)
```bash
curl -X POST http://localhost:8000/api/v1/ai/answer/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "ሰው ሰራሽ አስተውሎት AI የቨርቹዋል ረዳቶችን ሥራ እንዴት ይቀርጸዋል?",
    "language": "am"
  }'
```

### 3. Generate Grounded Course Answer (English)
```bash
curl -X POST http://localhost:8000/api/v1/ai/answer/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is shaping the future of virtual assistant work?",
    "language": "en"
  }'
```

### 4. Low-Bandwidth SMS Inbound Route (<= 160 Characters)
```bash
curl -X POST http://localhost:8000/sms/inbound \
  -H "Content-Type: application/json" \
  -d '{
    "from": "0911223344",
    "text": "What is shaping the future of VA work?"
  }'
```
**Plain Text Response (<= 160 chars):**
```text
According to course section «What is Shaping the Future of VA Work?»: More remote-first businesses Companies are now more comfortable... [Ref: What is Shaping the Future]
```

### 5. Outbound Job Alert Notification Dispatch (Contract for Yensew)
```bash
curl -X POST http://localhost:8000/api/v1/channels/notifications/send/ \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "0911223344",
    "channel": "sms",
    "title": "New Job Alert",
    "message": "Junior Virtual Assistant position open in Addis Ababa. Apply now."
  }'
```

---

## Languages
- **Supported:** English (`en`) and Amharic (`am`) with complete Ethiopic script typography.
- **Adding a new language:**
  1. Add translations to `backend/ai_engine/data/faqs.json`.
  2. Add language code to `LANGUAGE_CHOICES` in `backend/channels/models.py`.
  3. Directionality (`dir="auto"`) automatically handles RTL languages like Arabic.

---

## Offline & Low-Bandwidth Strategy
- **Offline Keyword Provider:** Scores lesson sections directly against questions with BM25-style keyword matching and title boosts. Requires zero external AI credentials or internet connection.
- **Curated FAQ Fallback:** Matches common support and accessibility queries when outside course boundaries, clearly flagging them with `[Offline FAQ Match]`.
- **Low-Bandwidth SMS:** All inbound SMS replies are normalized to international Ethiopian phone numbers (`+2519...`, `+2517...`) and strictly truncated to **160 characters**.

---

## Data & Privacy
- **Least Privilege:** Does not store unnecessary personal identity secrets.
- **Decoupled Identity:** `ChannelIdentity` maps Telegram chat IDs and phone numbers to session identifiers without exposing user secrets to clients.
- **No Hallucination / Honest Uncertainty:** The AI engine refuses to fabricate citations or generate course answers unsupported by retrieved evidence.

---

## Cost to Run
- **Offline Mode:** $0 / month (no cloud API calls, completely self-hosted).
- **Cloud Mode (OpenAI / Gemini):** ~$0.0003 per query (~$5 to $15 / month for 3,000 active learners).
- **Telegram Channel:** $0 (Telegram Bot API is free).

---

## Finished and In-Progress Status (Milestone 1)

### Finished:
- [x] Provider-independent AI interface (`BaseAIProvider`, `CloudAIProvider`, `LocalAIProvider`, `OfflineKeywordProvider`, `MockAIProvider`).
- [x] Grounded answer generation using the 5 lesson sections from `concept-with-navigation.html`.
- [x] Honest refusal when evidence is missing (both in English and Amharic).
- [x] Bilingual offline FAQ fallback engine (`faqs.json`).
- [x] Telegram bot handler with `/start`, language picker inline keyboard, and markdown citation formatter.
- [x] Telegram long-polling runner command (`python manage.py run_telegram_bot`) for laptop demos.
- [x] Ethiopian phone normalizer (`09...`, `07...`, `+251...`).
- [x] Low-bandwidth SMS inbound endpoint (`/sms/inbound` and `/api/v1/channels/sms/inbound/`) with 160-char truncation.
- [x] Outbound notification dispatcher interface for Yensew (`send_notification`).
- [x] OpenAPI 3.0 specification (`openapi.yaml`) and Swagger UI at `/docs/`.
- [x] 23 automated unit and integration tests passing (`pytest`).

### Scheduled for Milestone 2 (Cross-Module Integration):
- [ ] Connect Kidus's dynamic PDF/DOCX chunking pipeline when merged.
- [ ] Connect Koket's PostgreSQL chat session database when merged.
- [ ] Wire Yensew's live job alerts trigger to `send_notification`.

---

## Libraries & Licences
- `django` (BSD-3-Clause)
- `djangorestframework` (BSD-3-Clause)
- `drf-spectacular` (BSD-3-Clause)
- `requests` (Apache-2.0)
- `pytest` & `pytest-django` (MIT)
- `python-dotenv` & `django-environ` (BSD/MIT)
