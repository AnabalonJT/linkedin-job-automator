# 🏗️ LinkedIn Job Automator - Technical Architecture

**Complete technical documentation for all components and modules.**

---

## 📋 Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Modules](#core-modules)
3. [IA/ML Pipeline](#iaml-pipeline)
4. [Data Flow](#data-flow)
5. [Configuration](#configuration)
6. [Deployment](#deployment)

---

## System Architecture

### Docker Stack
```
Container Services (docker-compose.yml):

┌──────────────────────────────────────────────────────┐
│ n8n (http://localhost:5678)                          │
│ • Orchestration engine                               │
│ • Scheduled triggers (09:00 AM daily)                │
│ • Webhook triggers for manual runs                   │
└──────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────┐
│ runner (http://localhost:5000)                       │
│ • Flask API server                                   │
│ • IA classification endpoint                         │
│ • CV processing endpoint                             │
│ • Question answering endpoint                        │
└──────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────┐
│ selenium (http://localhost:4444)                     │
│ • Headless Chrome browser                            │
│ • Remote WebDriver endpoint                          │
│ • Form interaction control                           │
└──────────────────────────────────────────────────────┘
```

### Workflow Pipeline

```
Daily Execution (09:00 AM via n8n):

1. linkedin_scraper.py
   ├─ Search LinkedIn with criteria
   ├─ Extract job details (title, description, URL)
   ├─ Deduplicate against Google Sheets
   └─ Cache results → jobs_found.json

2. linkedin_applier.py  
   ├─ Read jobs from cache
   ├─ For each job:
   │  ├─ Classify with IA → Select CV type
   │  ├─ Fill form fields with config/templates
   │  ├─ Answer questions with IA (if confidence ≥ 0.85)
   │  ├─ Submit application
   │  └─ Log result
   └─ Write → application_results.json

3. google_sheets_manager.py
   ├─ Sync results to Google Sheets database
   ├─ Update Dashboard metrics
   └─ Log pending questions for manual review

4. Telegram Notification
   └─ Send summary: "N jobs applied ✅"
```

---

## Core Modules

### 🔍 linkedin_scraper.py
**Purpose**: Search LinkedIn and extract job listings

**Key Functions**:
- `search_jobs()` - Query LinkedIn with keywords, filters
- `extract_job_details()` - Parse job title, description, URL
- `deduplicate_against_sheets()` - Check against Google Sheets (source of truth)
- `save_to_cache()` - Write results to jobs_found.json

**Input**: Search keywords from .env
**Output**: jobs_found.json

**Dependencies**:
- Selenium (browser automation)
- Google Sheets API (deduplication)
- linkedin_cookies.json (authentication)

---

### ✍️ linkedin_applier.py
**Purpose**: Auto-apply to LinkedIn Easy Apply positions

**Architecture**:
```
Main Loop:
├─ Load jobs from jobs_found.json
├─ For each job (with error handling):
│  ├─ apply_to_job(job)
│  │  ├─ Classify job → determine CV type
│  │  ├─ Navigate to job page
│  │  ├─ Click "Easy Apply"
│  │  └─ process_application_form()
│  │     └─ 10-step application processing:
│  │        1. Check for errors
│  │        2. Detect form questions
│  │        3. Fill text fields (email, phone, etc)
│  │        4. Fill textareas (cover letter)
│  │        5. Handle radio buttons (with IA)
│  │        6. Handle dropdowns (with IA)
│  │        7. Handle checkboxes
│  │        8. Handle date fields
│  │        9. Handle file uploads (resume/cover letter)
│  │        10. Submit form
│  │
│  └─ Log result
│
├─ Handle new questions (manual review)
└─ Save results → application_results.json
```

**Key Methods**:
- `apply_to_job()` - Main application orchestrator
- `process_application_form()` - 10-step form processing loop
- `handle_radio_questions()` - Radio button logic with IA + comprehensive logging
- `handle_dropdown_questions()` - Dropdown logic with IA + comprehensive logging
- `fill_text_field()` - Fill text inputs from config
- `fill_textarea()` - Fill textarea from templates
- `find_answer_for_question()` - Search config for answer

**Enhanced Logging**:
- Question text asked
- Available options
- IA response + confidence score
- Answer source (IA/Config)
- Auto vs Manual submission status
- CV context used for decision

**Input**: jobs_found.json
**Output**: application_results.json, debug screenshots

---

### 📊 CV Processing Structure

#### cv_processor.py (~750 lines)
**Purpose**: Extract CV data and maintain context cache

**Dual CV Support**:
```
CV Files (config/):
├─ CV Software Engineer Anabalon.pdf → curriculum_context_software.json
└─ CV Automatización_Data Anabalón.pdf → curriculum_context_engineer.json

Cache In-Memory:
├─ software: {skills, experience, projects, certifications, etc.}
└─ engineer: {automation, data, tools, etc.}
```

**Key Methods**:
- `extract_pdf_to_json()` - Convert CV PDF → structured JSON
- `get_context_by_type()` - Get cached CV context for type
- `load_all_or_create()` - Initialize both CVs
- `get_context_string_by_type()` - Get formatted string for IA

**Data Schema**:
```json
{
  "personal_info": {
    "name": "José Tomás",
    "email": "...",
    "phone": "...",
    "linkedin_url": "..."
  },
  "summary": "...",
  "skills": ["Python", "Automation", ...],
  "experience": [
    {
      "title": "...",
      "company": "...",
      "duration": "...",
      "description": "..."
    }
  ],
  "projects": [...],
  "certifications": [...]
}
```

---

### 🤖 IA/ML Pipeline

#### openrouter_client.py (~300 lines)
**Purpose**: OpenRouter API communication

**Model**: meta-llama/llama-3.3-70b-instruct
**Provider**: OpenRouter API
**Cost**: ~$0.01 per 1000 tokens

**Key Methods**:
- `call()` - Generic API call
- `classify_job()` - Classify job type
- `answer_question()` - Answer application question

**Response Format**:
```json
{
  "answer": "string",
  "confidence": 0.95,
  "reasoning": "explanation",
  "auto_submit": true,
  "sources": ["CV skill: Python", "Experience: 5 years"]
}
```

---

#### ia_classifier.py (~473 lines)
**Purpose**: Classification and question answering with confidence scoring

**Intelligence Features**:
- CV classification (software vs engineer)
- Job-to-CV matching
- Question answering with confidence threshold
- Context-aware responses

**Key Methods**:
- `classify_job()` - Determine CV type + confidence
- `answer_question()` - Answer with confidence scoring
- `set_cv_type()` - Switch between CVs
- `get_current_cv_context()` - Get active CV context
- `get_stats()` - Return usage statistics

**Confidence Threshold**: 0.85
- If `confidence >= 0.85` → auto-submit
- If `confidence < 0.85` → mark MANUAL (requires review)

**Statistics Tracked**:
- Total questions answered
- Auto-answered vs manual
- Average confidence
- Distinct keywords encountered

---

#### ia_integration.py (~324 lines)
**Purpose**: Unified interface for all IA operations

**Integrates**:
- openrouter_client.py
- ia_classifier.py
- cv_processor.py

**Key Methods**:
- `classify_job()` - Wrapper for job classification
- `answer_question()` - Wrapper for question answering
- `set_cv_type()` - Set active CV and apply in classifier
- `get_stats()` - Get unified statistics
- `test_connection()` - Validate OpenRouter API

**Usage**:
```python
from ia_integration import IAIntegration

ia = IAIntegration(logger, debug=True)

# Classify job
classification = ia.classify_job(
    job_title="Senior Software Engineer",
    job_description="...",
    job_requirements="Python, Django"
)
# Returns: {'job_type': '...', 'recommended_cv': 'software', 'confidence': 0.92, ...}

# Answer question
answer = ia.answer_question(
    question_text="What is your experience with Python?",
    question_type="text",
    options=None
)
# Returns: {'answer': '...', 'confidence': 0.88, 'auto_submit': True, ...}
```

---

## Data Flow

### Job Search & Application Flow

```
1. Daily Trigger (09:00 AM)
   ↓
2. linkedin_scraper.py
   Input: Search keywords (.env)
   Output: jobs_found.json
   ├─ title
   ├─ company
   ├─ url
   ├─ description
   └─ requirements
   
3. linkedin_applier.py
   Input: jobs_found.json
   ├─ For each job:
   │  ├─ IA Classify
   │  ├─ Select CV
   │  └─ Fill form
   Output: application_results.json
   ├─ job_title
   ├─ company
   ├─ status (success/error)
   ├─ questions_encountered
   ├─ cv_used
   ├─ ia_classification
   └─ answers_log
      ├─ question_text
      ├─ answer
      ├─ source (IA/Config)
      ├─ ia_confidence
      └─ ia_auto
   
4. answer_log.json (for manual review)
   ├─ Unanswered questions
   └─ Low confidence answers

5. google_sheets_manager.py
   Sync to Google Sheets
   ├─ Applications sheet
   ├─ Dashboard metrics
   └─ Pending questions

6. Telegram Notification
   "✅ Applied to 5 positions"
```

---

## Configuration

### .env Variables
```bash
# LinkedIn Credentials
LINKEDIN_USERNAME=...
LINKEDIN_PASSWORD=...

# OpenRouter IA
OPENROUTER_API_KEY=...
IA_DEBUG=false
IA_CONFIDENCE_THRESHOLD=0.85

# CV Files
CV_SOFTWARE_PATH=config/CV Software Engineer Anabalon.pdf
CV_ENGINEER_PATH=config/CV Automatización_Data Anabalón.pdf

# Search Keywords
SEARCH_KEYWORDS=python,automation,data engineer

# Google Sheets
GOOGLE_SHEETS_ID=...
GOOGLE_SHEETS_CREDENTIALS=config/google_credentials.json

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# N8N
N8N_URL=http://localhost:5678
```

### respuestas_comunes.json
```json
{
  "informacion_personal": {
    "email": "your@email.com",
    "phone": "+56912345678",
    "linkedin_url": "https://linkedin.com/in/...",
    "ciudad": "Santiago"
  },
  "respuestas_abiertas_template": {
    "por_que_empresa": "Estoy interesado en...",
    "por_que_posicion": "This role aligns with..."
  }
}
```

---

## Deployment

### Docker Setup
```bash
# Start all containers
docker-compose up -d

# Verify containers
docker-compose ps

# View logs
docker-compose logs -f runner
docker-compose logs -f n8n
docker-compose logs -f selenium
```

### n8n Workflow Configuration
```
1. Open http://localhost:5678
2. Create workflow:
   ├─ Trigger: Schedule (09:00 AM daily)
   ├─ Step 1: Execute linkedin_scraper.py
   ├─ Step 2: Execute linkedin_applier.py
   ├─ Step 3: Execute google_sheets_manager.py
   └─ Step 4: Send Telegram notification
3. Deploy and activate
```

### Environment Setup
```bash
# 1. Create config directory
mkdir -p config/

# 2. Add CV files
# Copy: CV Software Engineer Anabalon.pdf → config/
# Copy: CV Automatización_Data Anabalón.pdf → config/

# 3. Add Google Sheets credentials
# From Google Cloud Console: config/google_credentials.json

# 4. Create .env file
cp .env.example .env
# Edit with your credentials

# 5. Install Python dependencies
pip install -r requirements.txt

# 6. Setup credentials manager
python scripts/credentials_manager.py setup
```

---

## Monitoring & Debugging

### Logs Location: `data/logs/`
```
├─ execution_YYYYMMDD_HHMMSS.log
├─ runner_server.log
├─ debug_no_button_*.png (form errors)
├─ application_results.json
└─ jobs_found.json
```

### Debug Mode
Enable in .env:
```bash
IA_DEBUG=true
```

This logs:
- Job classifications
- IA responses + confidence
- CV context loaded
- Form filling details
- Question answering logic

### Health Checks
```bash
# Test OpenRouter API
python -c "from scripts.ia_integration import IAIntegration; ia = IAIntegration(None, debug=True); ia.test_connection()"

# Test LinkedIn connection
python scripts/linkedin_scraper.py --test

# Test Google Sheets
python -c "from scripts.google_sheets_manager import GoogleSheetsManager; gsm = GoogleSheetsManager(); print(gsm.test_connection())"
```

---

## Error Handling

### Common Issues & Solutions

**1. LinkedIn Login Fails**
- Check: linkedin_cookies.json freshness
- Solution: `python scripts/credentials_manager.py reset-cookies`

**2. CV Extraction Failed**
- Check: PDF file format + location
- Solution: Verify `config/CV*.pdf` files exist and are readable

**3. IA Low Confidence**
- Check: CV context completeness (< 2000 chars)
- Solution: Extract full CV data using PROMPT_CV_EXTRACTION.md

**4. Form Submission Fails**
- Check: Debug screenshot at `data/logs/debug_no_button_*.png`
- Solution: Review screenshot and adjust selectors in linkedin_applier.py

**5. Google Sheets Sync Fails**
- Check: Service account has Edit access to sheet
- Solution: Re-share Google Sheet with service account email

---

## Performance Metrics

### Typical Execution Times
- Job search: 2-5 minutes (10-25 jobs)
- IA classification: 5-10 seconds per job
- Form filling: 30-60 seconds per application
- Total cycle: 30-60 minutes for 15-25 applications

### API Costs
- OpenRouter (Llama-3.3-70B):
  - ~15,000 tokens per 25 jobs × 6 questions each
  - Cost: ~$0.10-0.15 per execution (free tier usually sufficient)

### Data Storage
- Each job record: ~500-800 bytes
- Each application result: ~2-3 KB
- Logs: ~1-2 MB per month

---

## Module Dependencies

```
linkedin_applier.py
├─ ia_integration.py
│  ├─ ia_classifier.py
│  │  ├─ openrouter_client.py
│  │  └─ cv_processor.py
│  │     └─ pdf2image, pytesseract, etc.
│  └─ cv_processor.py
├─ google_sheets_manager.py
├─ utils.py
└─ Selenium WebDriver

linkedin_scraper.py
├─ google_sheets_manager.py
├─ utils.py
└─ Selenium WebDriver

google_sheets_manager.py
└─ Google Sheets API v4

n8n (Orchestration)
├─ HTTP calls to runner API
├─ Google Drive integration
└─ Telegram integration
```

---

## Security Considerations

1. **Credentials**: All stored encrypted in config/credentials.enc
2. **API Keys**: Loaded from environment variables only
3. **Google Sheets**: Service account (not user credentials)
4. **Telegram**: Bot token with restricted permissions
5. **Logs**: No credentials logged (filtered)

---

**Last Updated**: February 2025
**Version**: 2.0 (IA Integration Complete)
**Status**: Production Ready ✅
