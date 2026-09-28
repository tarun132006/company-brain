# Company Brain

**Organizational memory for AI agents.** Company Brain gives separate AI agents (Support, Engineering, Sales) their own long-term memory, lets them draw on each other's knowledge, and adds an **Arbiter** that checks a proposed customer commitment against what the company actually knows, before someone promises something the product can't deliver.

Built with **[Hindsight](https://hindsight.vectorize.io/)** for persistent memory and **[Groq](https://groq.com/)** for reasoning, served by a **FastAPI** backend with a plain HTML/CSS/JS chat frontend.

---

## The problem it solves

Sales promises a customer a 1 million row CSV export. Engineering already knows the current architecture can't reliably do that. Support has seen a customer's 300,000 row export time out. Nobody connected the dots.

Company Brain keeps each team's knowledge in its own memory bank, retrieves the relevant facts per question, and forces the model to answer **only from retrieved memory**, with no invented ETAs, roadmaps, or capabilities.

---

## Agents

| Agent | Endpoint | Memory it reads | Behavior |
|---|---|---|---|
| **Support** | `POST /api/chat` | Support bank | Answers customer issues from past incidents. **Learns:** extracts new facts the customer states and stores them back to memory. |
| **Engineering** | `POST /api/engineering` | Engineering bank | Reports known limitations and planned work, without turning "planned" into "in progress" or "done". |
| **Sales** | `POST /api/sales` | Support + Engineering banks | Cross-team answer to "can I promise this?", separating confirmed capability, known limitation, planned work, and unknown. |
| **Arbiter** | `POST /api/arbiter` | Support + Engineering banks | Evaluates a proposed commitment and returns `CONFLICT`, `NO CONFLICT`, or `INSUFFICIENT INFORMATION` with evidence and a recommended action. |

Every response includes `memories_used`, so you can see exactly which memories grounded the answer. The UI shows them in a collapsible "N memories used" section.

---

## Architecture

```
┌──────────────┐   POST /api/*    ┌───────────────────┐
│  Frontend    │ ───────────────▶ │  FastAPI (main.py)│
│ HTML/CSS/JS  │ ◀─────────────── │                   │
└──────────────┘   JSON answer    └───────┬─────┬─────┘
                                          │     │
                            recall/retain │     │ chat completions
                                          ▼     ▼
                                   ┌──────────┐ ┌──────────┐
                                   │Hindsight │ │   Groq   │
                                   │ (memory) │ │(reasoning)│
                                   └──────────┘ └──────────┘
```

Request flow for the Support agent:

1. **Recall** relevant memories from Hindsight
2. **Answer** with Groq, constrained to the retrieved memories
3. **Extract** a new fact from the customer's message (or `NO_NEW_MEMORY`)
4. **Retain** that fact in Hindsight for future conversations

**Memory banks**

| Bank ID | Purpose |
|---|---|
| `support-agent-clean` | Customer-reported problems, workarounds, solutions |
| `engineering-agent` | Verified engineering limits, decisions, roadmap |
| `sales-agent` | Created by `setup_sales.py` (not yet read by `/api/sales`) |

**Model:** `openai/gpt-oss-120b` via Groq.

---

## Project structure

```
company-brain/
├── main.py                 # FastAPI app: all four agents + CORS + health check
├── frontend/
│   ├── index.html          # Chat UI with agent sidebar
│   ├── script.js           # Agent switching, API calls, message rendering
│   └── style.css
├── setup_memory.py         # Create the Support memory bank
├── setup_engineering.py    # Create the Engineering memory bank
├── setup_sales.py          # Create the Sales memory bank
├── seed_engineering.py     # Seed Engineering with the demo facts
├── support_agent.py        # Original standalone CLI prototype of the Support agent
├── test_hindsight.py       # Quick recall smoke test
└── .env                    # API keys (never commit this)
```

---

## Getting started

### Prerequisites

- Python 3.10+ (developed on 3.14)
- A [Hindsight](https://hindsight.vectorize.io/) account: API key and base URL
- A [Groq](https://console.groq.com/) API key

### 1. Install dependencies

There's no `requirements.txt` yet, so install directly:

```bash
python -m venv .venv
# Windows:   .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install fastapi uvicorn python-dotenv pydantic hindsight-client groq
```

### 2. Configure environment

Create a `.env` file in `company-brain/`:

```env
HINDSIGHT_API_KEY=your_hindsight_key
HINDSIGHT_BASE_URL=your_hindsight_base_url
GROQ_API_KEY=your_groq_key
```

### 3. Create the memory banks and seed data

Run once:

```bash
python setup_memory.py
python setup_engineering.py
python setup_sales.py
python seed_engineering.py
```

`seed_engineering.py` stores these two facts, which drive the demo:

> Engineering confirmed that the current CSV export architecture does not reliably support 1 million rows as a single export.
> A capacity rewrite is planned for Q3.

### 4. Run the backend

```bash
uvicorn main:app --reload --port 8000
```

Check it's up: <http://127.0.0.1:8000/> should return `{"status": "online", ...}`. Interactive API docs are at <http://127.0.0.1:8000/docs>.

### 5. Open the frontend

The frontend calls `http://127.0.0.1:8000`. Serve it from any static server:

```bash
cd frontend
python -m http.server 5500
```

Then open <http://127.0.0.1:5500>.

---

## Try the demo

1. **Support** → tell it: *"Acme's 300,000 row CSV export timed out, but smaller batches worked."* The agent stores that as a new memory.
2. **Engineering** → ask: *"What are the known limits of CSV export?"*
3. **Sales** → ask: *"Can I promise Acme a 1 million row CSV export?"* It should say this is not a confirmed capability and that a Q3 rewrite being *planned* doesn't make it available.
4. **Arbiter** → submit: *"We'll deliver a reliable 1 million row single CSV export to Acme."* Expect a `CONFLICT` with the Engineering memory as evidence.

---

## API reference

All agent endpoints accept the same body:

```json
{ "customer": "Acme", "message": "Can I promise a 1M row export?" }
```

`customer` is only used by the Support agent; the others ignore it.

**Response (all agents)**

```json
{
  "agent": "Sales",
  "question": "...",
  "answer": "...",
  "memories_used": ["[Engineering Memory] ...", "[Support Memory] ..."]
}
```

Extra fields:

- **Support:** `customer`, `new_memory`, `memory_stored`
- **Arbiter:** `proposal`, `conflict` (boolean)

---

## Design notes

- **Grounded by prompt.** Each agent's prompt states that retrieved memory is the only source of company facts, and lists explicit prohibitions (no invented ETAs, thresholds, or "engineering is investigating").
- **Learning is restricted.** The Support agent only stores facts the *customer* stated. It never learns from the model's own answer, which prevents hallucinations from being written back into memory.
- **Low temperature** (0 to 0.1) for consistency.

---

## Known limitations / roadmap

- **Arbiter conflict flag is unreliable.** `conflict` is computed as `"CONFLICT" in answer.upper()`, which is also true for `NO CONFLICT`. It should parse the `Decision:` line instead.
- **`sales-agent` bank is unused.** `/api/sales` reads the Support and Engineering banks, not `SALES_BANK_ID`.
- **Hardcoded demo prompts.** The Sales and Arbiter prompts contain rules specific to the 1M-row CSV scenario. Generalize them before using other topics.
- **Stale scripts.** `support_agent.py` and `test_hindsight.py` use the old `support-agent` bank rather than `support-agent-clean`.
- **Sidebar controls.** `index.html` includes "New conversation" and mobile menu buttons that `script.js` doesn't wire up yet.
- **CORS is wide open** (`allow_origins=["*"]`). Restrict it before deploying.
- **No auth, tests, or `requirements.txt`.**

---

## Security

Never commit `.env` or share it in archives. If your keys have been shared (for example in a zip), rotate them in the Hindsight and Groq dashboards. Add a `.gitignore`:

```
.env
.venv/
__pycache__/
```

---

## Tech stack

FastAPI · Uvicorn · Hindsight (`hindsight-client`) · Groq (`groq`) · Pydantic · python-dotenv · Vanilla JS/HTML/CSS