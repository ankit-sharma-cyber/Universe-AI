# Universe AI Architecture

Universe AI implements the Multi-Agent College Operations Assistant assignment:

```text
Student request
      |
      v
Orchestrator: classify -> plan -> route -> merge
      |
      +--> Academic Agent ------+
      +--> Placement Agent ----+--> Knowledge/RAG + mock tools
      +--> Events Agent -------+
      +--> Student Services ---+
      |
      v
Grounded response + execution trace + session memory
```

The FastAPI layer provides localhost-only authentication, chat, approval, health, and domain
data endpoints. LangGraph executes one planned step at a time. Agents return structured
outputs with confidence and errors, allowing the orchestrator to continue with graceful
fallbacks. ChromaDB stores the local policy collection, while calendar, registration,
notification, and email integrations remain mocked.

The React/Vite interface is a single focused Assistant workspace. It exposes the specialist
agent rail, current route, plan, approval step, and execution trace so the orchestration is
observable during a demo.
