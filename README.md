# Universe AI

## Multi-Agent College Operations Assistant

Universe AI is a focused AI/ML, GenAI, and Agentic AI project. A central orchestrator routes
college requests to specialized agents, which use local RAG knowledge, mocked tools, and
session memory to produce a grounded response.

## Core scope

- **Academic Agent** — timetable, attendance, and academic-policy questions
- **Placement Agent** — placement eligibility and placement-policy questions
- **Events Agent** — upcoming events and mocked event registration/calendar tools
- **Student Services Agent** — FAQs, clubs, and student-service policies
- **Knowledge Agent** — retrieval from local college policy documents
- **Orchestrator** — intent routing, multi-agent plans, merging, fallbacks, and execution trace

The project intentionally does not include deployment infrastructure, cloud integrations, or
automated test tooling. All integrations are local or mocked for a simple demonstration.

## Run locally

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Build the local policy index once:

```bash
python -m rag.seed
```

Start the backend:

```bash
python -m app
```

In another terminal, start the frontend:

```bash
cd ui
npm install
npm run dev
```

Open http://127.0.0.1:5173. The FastAPI backend runs at http://127.0.0.1:8000 and the
interactive API documentation is available at http://127.0.0.1:8000/docs.

The demo logs in with the seeded student automatically. No API key is required; optional
OpenAI-compatible or local model settings are documented in `.env.example`.

## Example requests

- “Is my attendance enough according to the college policy?”
- “Am I eligible for the Google placement drive?”
- “Show upcoming AI and technology events.”
- “What student services can help with hostel or scholarship questions?”
- “Check my placement eligibility and recommend relevant upcoming events.”

The Assistant view shows the selected route, specialist agents, tools, retrieved knowledge,
approval steps, fallback errors, and final merged response.

## Project layout

```text
orchestrator/   routing, planning, memory, approval, and response merging
agents/         academic, placement, events, student services, and knowledge agents
tools/          mocked calendar, email, registration, and notification tools
rag/            local policy indexing and retrieval
app/            localhost-only FastAPI API
data/           seeded college data and policy documents
ui/             React/Vite interface
```
