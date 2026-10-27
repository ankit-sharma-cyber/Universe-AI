# Universe AI

## Multi-Agent College Operations Assistant

Universe AI is a local-first college operations assistant. An orchestrator
understands each request, plans the required work, routes it to focused domain
agents, retrieves relevant college policies, calls mocked campus tools, and
merges the result into one grounded response.

The project is designed for academics, placements, events, and student
services. It includes a connected React workspace, a FastAPI API, local policy
retrieval, session conversation history, approval flows, and an observable
agent execution trace.

## Features

- Multi-agent request routing and orchestration
- Academic support for timetable, courses, attendance, assignments, and policies
- Placement eligibility and placement-policy support
- Upcoming events and mocked event registration/calendar actions
- Student services for FAQs, clubs, hostel, scholarships, and lost-and-found
- Retrieval-Augmented Generation (RAG) over local college policy documents
- Session-level conversation memory and saved conversation history
- Mock function calling for registration, calendar, notifications, and communication
- Approval steps for actions that require confirmation
- Agent plans, routes, specialist statuses, tool results, and execution traces
- Light responsive React interface with assistant and portal views
- Automatic demo login with seeded student data

## Technology stack

### Backend

- Python
- FastAPI and Uvicorn
- Pydantic
- LangGraph for orchestration and workflow state
- LangChain Core and LangChain OpenAI
- ChromaDB for local vector retrieval
- `python-dotenv` for environment configuration
- JSON and SQLite-backed local demo data

### Frontend

- React 18
- Vite
- React Router
- Lucide React icons
- Inter and Playfair Display typography
- CSS-based responsive light workspace UI

### Integrations

- Local policy documents and seeded ChromaDB index
- Optional OpenAI-compatible LLM provider
- Optional Ollama local model
- Mocked calendar, registration, notification, email, and communication tools

No real institutional integrations or production secrets are included.

## Requirements

Install the following before starting:

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Git

The application is intended for local development. The backend runs on
`127.0.0.1:8000` and the Vite frontend runs on `127.0.0.1:5173`.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/ankit-sharma-cyber/Universe-AI.git
cd Universe-AI
```

### 2. Create and activate a Python virtual environment

#### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, run the following once for your user
account and then activate the environment again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install backend dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure optional environment variables

The mock demo works without API keys. To use an OpenAI-compatible provider or
an external integration, copy `.env.example` to `.env` and fill in only the
values you need:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Available configuration includes:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `MODEL_NAME`
- `OLLAMA_MODEL`
- Optional calendar, registration, notification, email, and communication URLs
  and API keys

Keep `.env` private. Do not commit credentials or real institutional secrets.

### 5. Build the local policy index

Run this once after installing dependencies, and again whenever policy
documents under `data/policies/` change:

```bash
python -m rag.seed
```

### 6. Install frontend dependencies

Open a second terminal and run:

```bash
cd ui
npm install
```

## Run the project

Use two terminals from the repository root.

### Terminal 1: Start the FastAPI backend

Activate the virtual environment if it is not already active, then run:

```bash
python -m app
```

The backend is available at:

- API: <http://127.0.0.1:8000>
- Health check: <http://127.0.0.1:8000/health>
- Swagger API documentation: <http://127.0.0.1:8000/docs>

### Terminal 2: Start the React frontend

```bash
cd ui
npm run dev
```

Open the frontend at <http://127.0.0.1:5173>.

The Vite development server proxies `/api` requests to the FastAPI backend at
`http://localhost:8000`.

## Demo account

The local demo signs in automatically with the seeded student:

- Student ID: `S2023001`
- Email: `arjun.mehta@campus.edu`

The token is stored locally in the browser under `campus_token`.

## Useful commands

From the repository root:

```bash
# Rebuild the local policy index
python -m rag.seed

# Start the backend
python -m app
```

From `ui/`:

```bash
# Install frontend packages
npm install

# Start the development server
npm run dev

# Create a production frontend build
npm run build

# Preview the production build locally
npm run preview
```

## Example requests

Try these in the Assistant view:

- “Is my attendance enough according to the college policy?”
- “Am I eligible for the Google placement drive?”
- “Show upcoming AI and technology events.”
- “What student services can help with hostel or scholarship questions?”
- “Check my placement eligibility and recommend relevant upcoming events.”

## Project structure

```text
agents/         Academic, placement, events, student-services, and knowledge agents
app/            FastAPI application, authentication, chat, portal, and history APIs
data/           Seeded student, academic, event, placement, service, and policy data
docs/           Architecture documentation
llm/            LLM client and provider configuration
orchestrator/   Routing, planning, memory, approval, merging, and execution trace
rag/            ChromaDB policy indexing and retrieval
tools/          Mock calendar, email, registration, and notification tools
ui/             React/Vite frontend application
```

## API areas

The backend exposes local endpoints for:

- Authentication and current student information
- Chat and approval actions
- Conversation history and saved messages
- Dashboard, timetable, courses, attendance, and assignments
- Events and placements
- FAQs, policies, hostels, and lost-and-found

Use the interactive documentation at
<http://127.0.0.1:8000/docs> to inspect the available routes and request
schemas.

## Troubleshooting

### The frontend cannot reach the API

Confirm that the backend is running on port `8000`, then restart the Vite
development server. The frontend proxy is configured in
`ui/vite.config.js`.

### The policy index is missing

Run:

```bash
python -m rag.seed
```

### Port 8000 or 5173 is already in use

Stop the existing process or start the affected service on another port. If
you change the backend port, update the proxy target in `ui/vite.config.js`.

### The demo session is stale

Clear the `campus_token` value from browser local storage and reload the
frontend. The app will sign in with the seeded demo student again.

## Scope and deployment

This repository is a local development demonstration. Integrations are
mocked, the backend uses local data, and no deployment infrastructure is
included. Before production use, add real authentication, secure secret
management, persistent production storage, monitoring, rate limiting, and
institution-approved integrations.
