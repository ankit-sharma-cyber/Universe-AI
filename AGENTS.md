# AGENTS.md — Universe AI

## Project

**Universe AI — Multi-Agent College Operations Assistant.** Keep this project focused on
academics, placement, events, and student services.

## Architecture

User request → **Orchestrator Agent** (intent, planning, routing) → **specialized agents**
(domain reasoning, RAG, tools) → merged response with memory and an observable trace.

- Academic, Placement, Events, Student Services, and Knowledge/RAG agents are modular.
- RAG uses local college policy documents.
- Calendar, registration, notification, and email integrations are mocked.
- The backend and frontend run on localhost only.

## Technology

- LangGraph for orchestration
- ChromaDB for local RAG
- FastAPI backend
- React/Vite frontend
- JSON/SQLite seed data

## Required behavior

1. Multi-agent routing and orchestration
2. Retrieval-Augmented Generation
3. Mock tool/function calling
4. Session-level memory
5. Graceful agent/tool fallbacks
6. Observable plans, routes, and execution traces

## Conventions

- Keep domain agents single-purpose and avoid circular imports.
- Keep mocked integrations behind thin tool interfaces.
- Do not add secrets or real institutional integrations.
- Keep the UI limited to Assistant, Academics, Events, Placements, and Student Services.

## Local verification

```bash
python -m rag.seed
python -m app
cd ui
npm run dev
```

Before finishing a change, smoke-run academic, placement, events, and student-services
requests through the local Assistant.
