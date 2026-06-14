# ⚡ AI Persona-Based Sales Strategy & Content Generator

A Flask web app that uses Claude AI to generate complete, persona-specific
sales funnel strategies and marketing content — in seconds.

---

## 📁 Project Structure

```
project/
├── app.py                  # Flask app entry point (factory pattern)
├── requirements.txt        # Python dependencies
│
├── routes/
│   ├── __init__.py
│   └── main_routes.py      # HTTP route handlers (Blueprint)
│
├── services/
│   ├── __init__.py
│   └── ai_service.py       # AI logic: prompt building + Claude API call
│
├── templates/
│   └── index.html          # Single-page UI (Jinja2)
│
└── static/
    ├── css/
    │   └── style.css       # All styles (dark editorial theme)
    └── js/
        └── main.js         # Frontend logic (fetch, render, tabs, copy)
```

---

## 🏗️ High-Level Architecture

```
Browser (HTML/CSS/JS)
     │
     │  POST /generate  { product, persona }
     ▼
Flask Route (routes/main_routes.py)
     │
     │  calls
     ▼
AI Service (services/ai_service.py)
     │  1. Build system prompt (persona-specific tone + JSON schema)
     │  2. Build user prompt (product + persona)
     │  3. Call Anthropic Claude API
     │  4. Parse JSON response
     ▼
Returns structured dict
     │
Flask Route → JSON response
     │
Browser renders:
  • Summary bar
  • Text-based flowchart
  • Accordion stage cards (with tabs: Sales / Email / Marketing)
  • Quick tips
```

---

## ⚙️ Setup & Run

### 1. Clone / download the project
```bash
cd project/
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your Anthropic API key
```bash
# Mac/Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-...

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

Get your API key from: https://console.anthropic.com

### 5. Run the app
```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

---

## 🧠 How the AI Logic Works

### Persona Prompts

Each persona gets a different system prompt injected into the Claude API call.

| Persona       | Tone                          | Focus                        |
|---------------|-------------------------------|------------------------------|
| Student       | Friendly, motivating          | Career, learning, affordability |
| B2C Customer  | Emotional, urgency-driven     | Lifestyle, FOMO, deals       |
| B2B Business  | Professional, ROI-focused     | Revenue, efficiency, scale   |

### Output Schema

Claude returns strict JSON:
```json
{
  "persona": "Student",
  "product": "Python Bootcamp",
  "funnel": [
    {
      "stage": "Awareness",
      "goal": "...",
      "tactics": ["...", "...", "..."],
      "content": {
        "sales_message": "...",
        "email": { "subject": "...", "body": "..." },
        "marketing_text": "..."
      }
    }
    // ... 4 more stages
  ],
  "quick_tips": ["...", "...", "..."]
}
```

---

## 💡 Improvement Ideas

### Features
- [ ] PDF export of the full strategy
- [ ] History page (save past generations using SQLite)
- [ ] Multiple product comparison side-by-side
- [ ] Tone customisation slider (formal ↔ casual)
- [ ] Language localisation (Hindi, Spanish, etc.)
- [ ] Share link for a generated strategy

### Technical
- [ ] Add Flask-Caching to avoid redundant API calls
- [ ] Stream the AI response (Flask SSE / Server-Sent Events)
- [ ] Add a loading skeleton UI for better UX
- [ ] Write unit tests for the service layer (pytest)
- [ ] Deploy to Render / Railway / Vercel (Flask adapter)

### UI
- [ ] Dark/light mode toggle
- [ ] Animated funnel diagram using SVG
- [ ] Drag-and-drop reordering of funnel stages
- [ ] Inline editing of generated content before copying

---

## 📝 API Reference

### POST /generate

**Request body (JSON):**
```json
{
  "product": "Online Python Bootcamp",
  "persona": "Student"
}
```

**Success response:**
```json
{
  "success": true,
  "data": { ...full strategy JSON... }
}
```

**Error response:**
```json
{
  "success": false,
  "error": "Reason for failure"
}
```
