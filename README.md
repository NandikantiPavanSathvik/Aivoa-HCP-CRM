# Aivoa.ai — AI-First HCP CRM (Healthcare Professional CRM)

> **Round 1 Technical Assignment** — AI-First CRM system for pharmaceutical sales representatives, focusing on the Healthcare Professional (HCP) module with a natural-language Log Interaction screen powered by **LangGraph** and **Groq LLM**.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Architecture Diagram](#architecture-diagram)
4. [Project Structure](#project-structure)
5. [Backend — File-by-File Explanation](#backend--file-by-file-explanation)
6. [Frontend — File-by-File Explanation](#frontend--file-by-file-explanation)
7. [AI Agent — How It Works](#ai-agent--how-it-works)
8. [LangGraph Tools](#langgraph-tools)
9. [Database Schema](#database-schema)
10. [API Endpoints](#api-endpoints)
11. [Setup and Running Locally](#setup-and-running-locally)
12. [Environment Variables](#environment-variables)
13. [Key Features](#key-features)

---

## Project Overview

Aivoa.ai is an **AI-First CRM** designed for pharmaceutical field representatives. Instead of filling out forms manually, reps simply describe their interactions in plain English to the AI copilot, which:

- Automatically searches for the HCP (doctor) in the database
- Creates a new HCP profile if not found (asking for details first)
- Logs the interaction with correct date, channel, sentiment, and topics
- Schedules follow-up appointments
- Provides next-best-action suggestions

The system uses **LangGraph** to orchestrate a stateful, multi-step AI agent and **Groq's LLM API** (`llama-3.3-70b-versatile`) for language understanding and tool use.

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework |
| **LangGraph** | Stateful AI agent workflow orchestration |
| **Groq API** (llama-3.3-70b-versatile) | LLM for natural language understanding and tool calling |
| **LangChain Core** | Message types, tool decorators |
| **SQLAlchemy** | ORM for database access |
| **SQLite** (fallback) / **MySQL** | Database storage |
| **Pydantic** | Request/response schema validation |
| **Python 3.14** | Runtime |

### Frontend

| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool and dev server |
| **Redux Toolkit** | Global state management |
| **Vanilla CSS** | Styling (glassmorphism dark theme) |
| **Lucide React** | Icon library |

---

## Architecture Diagram

```
+------------------------------------------------------------------+
|                     FRONTEND (React + Vite)                      |
|                                                                  |
|  +-------------+  +--------------------+  +-----------------+   |
|  | HCP Sidebar |  |  AI Chat Copilot   |  | Interaction Form|   |
|  | (list/select|  | (natural language  |  | (auto-populated |   |
|  |  HCP cards) |  |  input + output)   |  |  from AI output)|   |
|  +------+------+  +--------+-----------+  +--------+--------+   |
|         +--------------------+--------------------+             |
|                           Redux Store                            |
+----------------------------------+-------------------------------+
                                   | HTTP (REST)
                                   v
+------------------------------------------------------------------+
|                      BACKEND (FastAPI)                           |
|                                                                  |
|  POST /api/chat  -->  LangGraph Agent Graph                      |
|                              |                                   |
|                    +---------v----------+                        |
|                    |  call_model node   | <-- Groq LLM           |
|                    | (llama-3.3-70b)    |     (direct API)       |
|                    +---------+----------+                        |
|                    +---------v----------+                        |
|                    |   tools node       |                        |
|                    | (ToolNode, 8 tools)|                        |
|                    +---------+----------+                        |
|                              |                                   |
|                    +---------v----------+                        |
|                    |  SQLAlchemy ORM    |                        |
|                    |  SQLite / MySQL    |                        |
|                    +--------------------+                        |
+------------------------------------------------------------------+
```

---

## Project Structure

```
Aivoa.ai/
|-- README.md                    # This file — full project documentation
|-- .gitignore                   # Git ignore rules (.env, __pycache__, node_modules)
|-- hcp_crm.db                   # SQLite database (auto-created fallback)
|
|-- backend/                     # FastAPI Python backend
|   |-- .env                     # Environment variables (API keys, DB URL)
|   |-- requirements.txt         # Python package dependencies
|   |-- test_tool_call.py        # Groq API diagnostic/test script
|   +-- app/
|       |-- __init__.py          # Package init
|       |-- config.py            # Settings loader (reads .env using Pydantic)
|       |-- database.py          # SQLAlchemy models + DB connection + seeding
|       |-- schemas.py           # Pydantic request/response schemas
|       |-- agent_tools.py       # All 8 LangGraph tool definitions
|       |-- agent.py             # LangGraph agent, MockLLM, SYSTEM_PROMPT
|       +-- main.py              # FastAPI app, all API endpoints, lifespan
|
+-- frontend/                    # React + Vite frontend
    |-- package.json             # Node dependencies
    |-- vite.config.js           # Vite config + /api proxy to backend
    |-- index.html               # HTML entry point
    +-- src/
        |-- main.jsx             # React entry point, Redux Provider
        |-- App.jsx              # Root layout, HCP data fetching, 3-panel layout
        |-- App.css              # App-level styles
        |-- index.css            # Global design system (all CSS variables and styles)
        |-- store/
        |   +-- index.js         # Redux store: hcpsSlice + chatSlice
        +-- components/
            |-- ChatCopilot.jsx  # AI chat interface component
            |-- HCPInsights.jsx  # HCP profile card + interaction history table
            +-- InteractionForm.jsx  # Log interaction form (auto-filled by AI)
```

---

## Backend — File-by-File Explanation

### `backend/.env`

Stores all sensitive configuration. Not committed to git in production.

```
GROQ_API_KEY=gsk_...                         # Groq LLM API key
MODEL_NAME=llama-3.3-70b-versatile           # LLM model to use
DATABASE_URL=mysql+pymysql://root:pwd@...    # MySQL connection (optional)
```

---

### `backend/requirements.txt`

All Python package dependencies with minimum version pins:

| Package | Purpose |
|---|---|
| `fastapi>=0.110.0` | Web API framework |
| `uvicorn>=0.28.0` | ASGI server |
| `sqlalchemy>=2.0.0` | ORM |
| `pymysql>=1.1.0` | MySQL driver |
| `cryptography>=42.0.0` | MySQL SSL support |
| `python-dotenv>=1.0.1` | Load .env file |
| `groq>=0.9.0` | Groq API client (direct, no LangChain wrapper) |
| `langchain-core>=0.3.0` | Message types, @tool decorator |
| `langchain-groq>=0.3.0` | ChatGroq (kept for LangGraph compatibility) |
| `langgraph>=0.2.0` | Agent graph orchestration |
| `pydantic>=2.6.0` | Data validation |

---

### `backend/app/config.py`

Loads environment variables into a `Settings` Pydantic class using `python-dotenv`.

- Reads `GROQ_API_KEY`, `MODEL_NAME`, `DATABASE_URL` from `.env`
- Provides `SQLITE_FALLBACK_URL = "sqlite:///./hcp_crm.db"` as hardcoded fallback
- A global `settings` singleton is imported by all other backend modules

---

### `backend/app/database.py`

Defines all **SQLAlchemy database models** and the DB connection/initialization logic.

**Models:**

**HCP table (`hcps`)**
- `id` — auto-increment primary key
- `name`, `specialty`, `clinic_name`, `email`, `phone`, `last_interaction_date`
- One-to-many relationship to `Interaction`

**Interaction table (`interactions`)**
- `id` — auto-increment primary key
- `hcp_id` — foreign key to HCP
- `date`, `channel`, `topics`, `sentiment`, `notes`, `follow_up_date`, `next_step`, `raw_text`, `created_at`

**Connection Strategy (automatic fallback):**
1. Tries MySQL first using `DATABASE_URL` from `.env`
2. If MySQL fails (wrong credentials, not installed), falls back to SQLite automatically
3. `create_tables()` — creates tables if they don't exist
4. `seed_sample_data()` — inserts 5 demo HCPs on first startup:
   - Dr. Sarah Jenkins (Cardiology, Metro Heart Clinic)
   - Dr. Robert Chen (Oncology, City Cancer Center)
   - Dr. Emily Taylor (Pediatrics, Children's Health Hospital)
   - Dr. David Patel (Neurology, Brain and Spine Institute)
   - Dr. Lisa Cooper (Endocrinology, Diabetes Care Center)

---

### `backend/app/schemas.py`

Pydantic models for API request/response validation:

- `ChatRequest` — `{message: str, history: list, hcpId: Optional[int]}`
- `ChatResponse` — `{reply: str, tool_calls: list, extracted_data: dict}`
- `HCPOut`, `InteractionOut` — serialization of DB models for API responses
- `InteractionCreate`, `InteractionUpdate` — for POST/PUT endpoints

---

### `backend/app/agent_tools.py`

Contains all **8 LangGraph tools** registered with the `@tool` decorator.
These are the functions the LLM can call during its reasoning loop:

| Tool | Parameters | What It Does |
|---|---|---|
| `search_hcp` | `query: str` | Searches HCPs by name, specialty, or clinic. Returns ID + full profile. |
| `create_hcp` | `name, specialty, clinic_name, email, phone` | Creates a new HCP. Returns the new ID. |
| `log_interaction` | `hcp_id, date, channel, topics, sentiment, notes, follow_up_date, next_step, raw_text` | Saves a new interaction record. Updates `last_interaction_date` on HCP. |
| `edit_interaction` | `interaction_id, date, channel, topics, sentiment, notes, follow_up_date, next_step` | Updates specific fields of an existing log entry. |
| `get_interaction_history` | `hcp_id: int` | Returns all past interactions for the given HCP. |
| `schedule_followup` | `hcp_id, follow_up_date, notes` | Saves a follow-up date on the most recent interaction. |
| `get_hcp_profile` | `hcp_id: int` | Returns full profile details for a specific HCP. |
| `suggest_next_best_action` | `hcp_id: int` | Analyzes history and returns a recommended next action. |

All tools are collected into `sales_tools = [search_hcp, create_hcp, ...]` at the bottom.

---

### `backend/app/agent.py`

The **core AI agent file** — the most complex module in the project.

**`AgentState` (TypedDict)**
LangGraph state container. Holds `messages: Sequence[BaseMessage]` — the full conversation including tool calls and tool results.

**`MockLLM` class**
Keyword-based fallback when no Groq API key is present. Implements `__call__(messages)` and pattern-matches user text to generate appropriate tool calls. Helper methods:
- `_extract_channel(text)` — "met/visited" = In-Person, "called" = Phone, etc.
- `_extract_sentiment(text)` — positive/negative/neutral keyword detection
- `_extract_topics(text)` — extracts product names and medical topics
- `_extract_interaction_date(text)` — "today", "yesterday", "last Monday"
- `_extract_follow_up_date(text)` — "on 17", "next Friday", "in 2 weeks"

**`SYSTEM_PROMPT`**
Instructions given to the LLM at the start of every conversation:
- Rule 1: Search before creating — always look up the doctor first
- Rule 2: If doctor not found, ask for specialty/clinic/phone/email before creating
- Rule 3: If HCP ID is already in context (selected from sidebar), use it directly
- Rule 4: How to extract date, channel, sentiment, topics from user text
- Critical rules: each JSON key appears exactly once, always use year 2026, YYYY-MM-DD format

**`_simplify_prop(prop, defs)`**
Recursively cleans a Pydantic JSON schema property:
- Resolves `$ref` references from `$defs`
- Collapses `anyOf: [string, null]` (Optional[str] pattern) to `{type: string}`
- Strips `title`, `default`, `examples` metadata noise

**`_build_groq_tools()`**
Builds clean OpenAI-compatible tool schemas from LangChain `@tool` functions by running `_simplify_prop` on every field.

**`_lc_to_groq_messages(messages)`**
Converts LangChain message objects (SystemMessage, HumanMessage, AIMessage, ToolMessage) to raw `{"role": ..., "content": ...}` dicts for the Groq API.

**`_groq_to_lc_message(groq_msg)`**
Converts a Groq API response back to a LangChain `AIMessage` (with `tool_calls` if present).

**`_invoke_llm(messages)`**
Unified LLM caller:
- With API key: calls Groq directly with cleaned schemas
- Without API key: delegates to MockLLM

**`call_model(state)` — LangGraph Node**
1. Injects SYSTEM_PROMPT if not already in messages
2. Calls `_invoke_llm(messages)`
3. Returns `{"messages": [response]}`

**LangGraph Graph**
```python
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)       # LLM reasoning
workflow.add_node("tools", ToolNode(sales_tools))  # Tool execution
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)  # tool calls? -> tools, else END
workflow.add_edge("tools", "agent")          # loop back after each tool run
graph = workflow.compile()
```

---

### `backend/app/main.py`

The **FastAPI application** with all endpoints and core request handling.

**`normalize_date(date_str)` helper**
Converts any date string the LLM produces into `YYYY-MM-DD`:

| Input | Output |
|---|---|
| `"today"`, `"now"` | today's date |
| `"yesterday"` | yesterday |
| `"tomorrow"` | tomorrow |
| `"17"`, `"17th"`, `"on 17"` | 17th of current/next month |
| `"next Friday"` | upcoming Friday's date |
| `"July 17"`, `"17 July"` | 2026-07-17 |
| `"in 2 weeks"`, `"in 3 days"` | relative future dates |
| Unrecognised string | `None` (form not overwritten) |

**`/api/chat` endpoint — step by step:**
1. Receives `{message, history, hcpId}` from frontend
2. If `hcpId` provided, prepends a SystemMessage: `"Active HCP: Dr. X (ID: N, Specialty: ...)"`
3. Maps history messages to LangChain objects (strips old tool_calls to prevent model confusion)
4. Appends the new HumanMessage
5. Runs `graph.invoke({"messages": lang_messages})` — LangGraph agent loop executes
6. Scans all messages in final state to find tool calls made
7. Extracts `extracted_data` from `log_interaction` args: date, channel, topics, sentiment, notes, follow_up_date, next_step
8. Normalizes all date fields with `normalize_date()`
9. Returns `{reply, tool_calls, extracted_data}` to frontend

---

### `backend/test_tool_call.py`

Standalone diagnostic to verify the Groq API works with tool calling:
- Creates a minimal `search_hcp` tool schema
- Sends a test message: "I met Dr. Jenkins today"
- Prints whether the API returns a proper structured tool call
- Run with: `python backend/test_tool_call.py` from project root

---

## Frontend — File-by-File Explanation

### `frontend/src/main.jsx`

React DOM entry point. Wraps the entire app in `<Provider store={store}>` and renders `<App />` into `#root`.

---

### `frontend/src/App.jsx`

Root component that:
- Dispatches `fetchHcps()` and `fetchInteractions()` on mount
- Renders the 3-column layout:
  - **Left column**: Scrollable HCP cards sidebar
  - **Center column**: AI Chat Copilot
  - **Right column**: HCP profile (top) + Interaction Form (bottom)
- Shows selected HCP name as active context badge in the chat header
- Handles the "select HCP" action (dispatches Redux `setSelectedHcp`)

---

### `frontend/src/index.css`

The complete **design system** in a single file:

- **CSS custom properties**: `--bg-primary` (dark navy), `--bg-card`, `--accent` (purple #a855f7), `--text-primary`, `--text-secondary`, `--text-muted`, `--border`, `--positive-green`, `--negative-red`
- **Google Fonts**: Inter (300, 400, 500, 600, 700 weights)
- **Layout**: 3-column CSS grid (250px | 1fr | 400px)
- **Glassmorphism panels**: `backdrop-filter: blur(20px)` with subtle border + glow
- **All component styles**: HCP cards, specialty badges, sentiment toggles, chat bubbles, tool badges, form inputs with AI-fill glow highlight, recent visits table
- **Animations**: typing indicator (3-dot bounce), pulse, wave bars for voice recording

---

### `frontend/src/store/index.js`

Redux store with **two slices**:

**`hcpsSlice`**
- State: `hcps[]`, `selectedHcp`, `interactions[]`, `loading`, `error`
- `fetchHcps()` — GET /api/hcps
- `fetchInteractions()` — GET /api/interactions
- `saveInteraction(data)` — POST or PUT /api/interactions
- `setSelectedHcp(hcp)` — selects HCP, triggers interaction fetch for that HCP

**`chatSlice`**
- State: `messages[]` (each `{role, content, tool_calls}`), `loading`, `lastToolsTriggered[]`
- `sendChatMessage({message, history, hcpId})`:
  1. Adds user message to `messages` immediately
  2. Calls POST /api/chat
  3. Adds assistant reply with tool_calls to `messages`
  4. Dispatches `updateFormFromAI(extracted_data)` to hcpsSlice to populate form
- `clearChat()` — resets messages to welcome message only

---

### `frontend/src/components/ChatCopilot.jsx`

The AI chat interface rendered in the center panel:

- **Welcome state**: 6 pre-written prompt chips the user can click to auto-fill the input
- **Message bubbles**: user messages on right (blue-tinted), assistant on left (glass)
- **Tool badge**: subtle `AI used: search_hcp, log_interaction` in muted italic — no raw JSON shown
- **Typing indicator**: 3 animated dots while `loading` is true
- **Voice button (mic icon)**: Simulates voice-to-text by auto-filling the input with a realistic transcript based on selected HCP
- **Send button + Enter key**: Dispatches `sendChatMessage`
- **Trash button**: Dispatches `clearChat()`
- **History window**: Sends last 6 messages only; `tool_calls` stripped from history to prevent model confusion

---

### `frontend/src/components/HCPInsights.jsx`

Right panel top section — HCP profile + interaction history:

- **Empty state**: "Select an HCP from the list to view their profile" placeholder
- **Profile header**: HCP name, specialty badge, clinic, email, phone, last interaction date
- **All Recent HCP Visits table**: Shows all interactions for selected HCP with:
  - Date (formatted as DD-MM-YYYY)
  - Channel with icon (In-Person / Phone / Video Call / Email)
  - Topics discussed
  - Sentiment badge (green/orange/red)
  - Visit summary notes

---

### `frontend/src/components/InteractionForm.jsx`

Right panel bottom section — the Log Interaction form:

- **Disabled state**: Placeholder shown when no HCP is selected
- **Fields**:
  - Date picker (populated by AI or today's date by default)
  - Channel dropdown (In-Person, Phone, Video Call, Email)
  - Discussion Topics (text field)
  - Sentiment toggle (3 buttons: Positive / Neutral / Negative)
  - Visit Summary / Notes (textarea)
  - Follow-up Date (optional date picker)
  - Action / Next Step (optional text field)
- **AI-fill highlight**: Fields populated by AI response glow purple with subtle border animation
- **Save button**: Submits via `saveInteraction()` Redux action; shows success/error feedback

---

## AI Agent — How It Works

### Conversation Flow

```
User: "today I met Dr. Jenkins, discussed CardioSphere-10mg, she was positive"
                              |
                              v
            FastAPI POST /api/chat
                              |
                              v
            LangGraph graph.invoke(messages)
                              |
          +---------+---------v---------+---------+
          |                                        |
          v                                        |
  [call_model node]                                |
  Groq LLM: decides to call search_hcp            |
          |                                        |
          v                                        |
  [tools node]                                     |
  search_hcp("Dr. Jenkins") -> ID: 1 found        |
          |                                        |
          v                                        |
  [call_model node]                                |
  Groq LLM: calls log_interaction(hcp_id=1, ...)  |
          |                                        |
          v                                        |
  [tools node]                                     |
  log_interaction saves to DB, returns SUCCESS     |
          |                                        |
          v                                        |
  [call_model node]                                |
  Groq LLM: generates final reply text            |
          |                                        |
          +----> END                               |
                              |
          "Logged interaction with Dr. Jenkins."   |
          extracted_data: {date, channel, ...}     |
                              |
          Form auto-populated <-------------------+
```

### New Doctor Flow

1. User: "today I met Dr. Sathvik and discussed fever treatment"
2. `search_hcp("Dr. Sathvik")` returns "No HCPs found"
3. LLM replies: "I couldn't find Dr. Sathvik. Please provide: specialty, clinic/location, phone, email"
4. User: "He's a General Practitioner at Apollo Hospital, phone: 9999999999"
5. LLM calls `create_hcp("Dr. Sathvik", "General Practice", "Apollo Hospital", phone="9999999999")`
6. LLM immediately calls `log_interaction` with the new HCP's ID
7. Form is populated with the logged interaction details

---

## LangGraph Tools

### Why Direct Groq API (not LangChain bind_tools)

LangChain's `ChatGroq.bind_tools().invoke()` was generating malformed tool calls in old text format (`<function=search_hcp{"query": "..."}`) due to a bug in LangChain's message conversion layer when using complex Optional schemas. The definitive fix was bypassing LangChain entirely for the API call:

```python
# FIXED: Call Groq API directly with manually cleaned schemas
response = groq_client.chat.completions.create(
    model=settings.MODEL_NAME,
    messages=_lc_to_groq_messages(messages),   # manual LangChain -> dict conversion
    tools=_groq_tools_schema,                  # cleaned schemas (no anyOf/null)
    tool_choice="auto",
    temperature=0,
)
```

LangGraph still manages the conversation state and tool routing — only the LLM call itself bypasses LangChain.

---

## Database Schema

### `hcps` table

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `name` | VARCHAR(100) | Doctor's full name |
| `specialty` | VARCHAR(100) | Medical specialty |
| `clinic_name` | VARCHAR(150) | Clinic or hospital name |
| `email` | VARCHAR(100) | Optional |
| `phone` | VARCHAR(30) | Optional |
| `last_interaction_date` | VARCHAR(50) | Updated on each log |

### `interactions` table

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `hcp_id` | INTEGER FK | References hcps.id |
| `date` | VARCHAR(50) | YYYY-MM-DD format |
| `channel` | VARCHAR(50) | In-Person / Phone / Video Call / Email |
| `topics` | VARCHAR(255) | Comma-separated |
| `sentiment` | VARCHAR(50) | Positive / Neutral / Negative |
| `notes` | TEXT | Visit summary |
| `follow_up_date` | VARCHAR(50) | Optional, YYYY-MM-DD |
| `next_step` | VARCHAR(255) | Optional recommended action |
| `raw_text` | TEXT | Original user message |
| `created_at` | DATETIME | Auto UTC timestamp |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/hcps` | List all HCPs |
| GET | `/api/hcps/{id}` | Get single HCP |
| GET | `/api/interactions` | All interactions (filter with `?hcp_id=N`) |
| POST | `/api/interactions` | Create new interaction |
| PUT | `/api/interactions/{id}` | Update interaction |
| POST | `/api/chat` | Main AI endpoint — full LangGraph agent |

### POST /api/chat

**Request:**
```json
{
  "message": "today I met Dr. Jenkins, discussed CardioSphere-10mg",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "hcpId": 1
}
```

**Response:**
```json
{
  "reply": "Logged interaction with Dr. Jenkins. Sentiment: Positive.",
  "tool_calls": [
    {"name": "search_hcp", "args": {"query": "Dr. Jenkins"}},
    {"name": "log_interaction", "args": {"hcp_id": 1, "date": "2026-07-15", ...}}
  ],
  "extracted_data": {
    "date": "2026-07-15",
    "channel": "In-Person",
    "topics": "CardioSphere-10mg",
    "sentiment": "Positive",
    "notes": "Met Dr. Jenkins and discussed CardioSphere-10mg trial results.",
    "follow_up_date": "2026-07-29",
    "next_step": "Follow up on prescription uptake"
  }
}
```

---

## Setup and Running Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API key — free tier at [console.groq.com](https://console.groq.com)

### 1. Clone the repository

```bash
git clone https://github.com/NandikantiPavanSathvik/Aivoa-HCP-CRM.git
cd Aivoa-HCP-CRM
```

### 2. Backend setup

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
# Edit backend/.env with your GROQ_API_KEY
```

`.env` minimum configuration:
```
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama-3.3-70b-versatile
DATABASE_URL=sqlite:///./hcp_crm.db
```

```bash
# Start the backend
python -m uvicorn app.main:app --reload
# Server starts at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
# Dev server starts at http://localhost:5173
```

### 4. Open the app

Go to **http://localhost:5173** — the app loads with 5 pre-seeded HCPs ready to use.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq LLM API key |
| `MODEL_NAME` | Yes | `llama-3.3-70b-versatile` | LLM model ID |
| `DATABASE_URL` | No | SQLite fallback | MySQL connection string |

---

## Key Features

| Feature | How It Works |
|---|---|
| Natural Language Logging | User types in plain English; LLM extracts all structured fields |
| Auto-form Population | `extracted_data` from AI response auto-fills the interaction form |
| New HCP Creation Flow | AI asks for details before creating unknown doctors |
| Smart Date Parsing | "on 17", "next Friday", "in 2 weeks" all correctly resolved to YYYY-MM-DD |
| Sentiment Detection | Positive / Neutral / Negative auto-classified from user text |
| Follow-up Scheduling | AI extracts and stores follow-up dates from natural language |
| Voice Dictation Simulation | Mock voice-to-text fills in realistic transcripts per selected HCP |
| Interaction History | Full visit log visible per HCP in the right panel |
| Next Best Action | AI suggests next steps based on past interaction patterns |
| MockLLM Fallback | Keyword-based agent works without any API key |
| SQLite Fallback | Works without MySQL — uses local SQLite file automatically |
| Rate Limit Handling | Graceful error messages when Groq API quota exceeded |
| Tool Schema Cleaning | Optional fields simplified from anyOf/null to avoid model confusion |

---

## Author

**Pavan Sathvik Nandikanti**
AI-First HCP CRM — Aivoa.ai Technical Assignment (Round 1)
