# Aivoa CRM — AI-First HCP Interaction Module

Welcome to the **AI-First CRM Healthcare Professional (HCP) Module**. This project implements a modern **Log Interaction Screen** designed for life science field representatives. It offers two fully synchronized logging flows: a natural-language **Conversational Chat Copilot** (powered by a LangGraph AI Agent) on the left, and a **Dynamic Structured Form** on the right.

The user interface uses premium glassmorphic styling, custom glowing badge colors, Google Inter typography, and micro-animations—such as a visual flash pulse that highlights form fields populated by the AI's entity extraction.

---

## Key Features

1. **AI-First Architecture**: Log visits or phone calls in plain English. The AI agent extracts parameters and populates the structured form.
2. **LangGraph Agentic Workflow**: The conversational copilot compiles state graphs and determines when to execute sales-related tools.
3. **Structured Form Sync**: Manually log, review, or edit details directly. The form highlights inputs when synchronized from chat.
4. **Dual DB Backend Engine**: Connects to MySQL. If MySQL is not configured or fails to connect, it automatically falls back to an SQLite database (`hcp_crm.db`), making it run out-of-the-box.
5. **Mock Agent Fallback**: Run and demo the application with zero external keys. If `GROQ_API_KEY` is not provided in `.env`, the agent invokes a simulated LLM that replicates tool paths.

---

## Tech Stack

- **Frontend**: React (Vite), Redux Toolkit (state management), Lucide Icons, Google Inter Font, Vanilla CSS (Glassmorphism & animations).
- **Backend**: Python (FastAPI), SQLAlchemy (ORM).
- **AI Agent**: LangGraph, LangChain Core, ChatGroq.
- **LLM**: Groq `gemma2-9b-it`.
- **Database**: MySQL (falls back to local SQLite).

---

## LangGraph Sales Tools

The agent utilizes **five (5) specific tools** to support sales activities:
1. `search_hcp(query)`: Search HCPs in the database by name, clinic, or specialty.
2. `get_interaction_history(hcp_id)`: Retrieve prior visit logs and sentiments for a specific HCP.
3. `log_interaction(hcp_id, date, channel, topics, sentiment, notes, follow_up_date, next_step, raw_text)`: Extract entities from discussion notes, summarize, and save logs.
4. `edit_interaction(interaction_id, ...)`: Modify details of existing logs.
5. `schedule_followup(hcp_id, follow_up_date, next_step)`: Schedule next actions or meetings associated with an HCP.

---

## Setup & Running the Application

### 1. Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)
- **Groq API Key** (Optional: if not supplied, the app runs in Mock Agent mode for zero-setup demonstration).

---

### 2. Run Backend (FastAPI)

1. Navigate to the `backend` directory:
   ```powershell
   cd backend
   ```
2. (Optional) Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   ```
3. Install Python dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Configure environment variables in `backend/.env`:
   - Paste your Groq API Key: `GROQ_API_KEY="your_groq_key_here"`
   - Modify the `DATABASE_URL` if you want to connect to a specific MySQL instance:
     `DATABASE_URL="mysql+pymysql://root:password@localhost:3306/hcp_crm"`
5. Start the FastAPI server:
   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The server starts on http://127.0.0.1:8000 and automatically creates and seeds the database (mock HCPs and histories) on startup.*

---

### 3. Run Frontend (Vite + React)

1. Navigate to the `frontend` directory:
   ```powershell
   cd frontend
   ```
2. Install npm packages:
   ```powershell
   npm install
   ```
3. Launch the Vite development server:
   ```powershell
   npm run dev
   ```
   *The client starts on http://localhost:5173. Open this URL in your web browser.*

---

## Demonstrating & Testing the App

1. **Select an HCP**: Click on **Dr. Sarah Jenkins** on the left panel. Her contact card, KPIs, and past visits load.
2. **Form Interaction**: Fill out the right-hand form manually and click **Save Interaction Log**. It appears in the history log at the bottom.
3. **AI Chat Logging**: In the chat panel, click the **microphone** icon to simulate dictation (or write a message):
   `"I just visited Dr. Sarah Jenkins today, we discussed CardioSphere-10mg and the trial. She was very positive. Schedule a follow-up for next Friday."`
4. **Tool Execution**: Press Enter. Watch the chat stream display the LangGraph node path (e.g. running `log_interaction` with arguments).
5. **Redux Sync Highlight**: Watch as the structured form fields on the right instantly populate with the extracted date, channel, topics, sentiment, and follow-up data, pulsing with a cyan glow to indicate AI-agent synchronization!
6. **Edit Action**: Select any row in the visit history table at the bottom and click **Edit**. The form shifts into edit mode, allowing updates.
