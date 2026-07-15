import json
import logging
import datetime
import re
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.config import settings
from app.database import get_db, create_tables, HCP, Interaction
from app import schemas
from app.agent import graph


def normalize_date(date_str: str) -> Optional[str]:
    """
    Convert any date string the LLM might produce → YYYY-MM-DD.
    Returns None (no update) rather than falling back to today for
    unrecognised strings — avoids overwriting the form with wrong dates.
    """
    if not date_str:
        return None
    s = date_str.strip()
    sl = s.lower()

    today = datetime.date.today()

    # ── Relative keywords ─────────────────────────────────────────────────────
    if sl in ("today", "now"):
        return today.strftime("%Y-%m-%d")
    if sl == "yesterday":
        return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if sl in ("tomorrow", "next day"):
        return (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # ── Already ISO format ────────────────────────────────────────────────────
    if re.match(r"^\d{4}-\d{2}-\d{2}$", sl):
        return sl

    # ── Bare day-of-month: "17", "17th", "20 this month", "on the 17th of this month" ─
    # User says "next appointment is on 17" → resolve to 17th of current month
    day_only = re.match(
        r"^(?:on\s+)?(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?(?:\s+(?:of\s+)?this\s+month)?$", sl
    )
    if day_only:
        day = int(day_only.group(1))
        if 1 <= day <= 31:
            try:
                target = today.replace(day=day)
                # If that day has already passed this month, use next month
                if target < today:
                    if today.month == 12:
                        target = datetime.date(today.year + 1, 1, day)
                    else:
                        target = datetime.date(today.year, today.month + 1, day)
                return target.strftime("%Y-%m-%d")
            except ValueError:
                pass  # e.g. Feb 30 — fall through

    # ── Named-month patterns: "July 17", "17 July", "17th July", "July 17th" ─
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9,
        "oct": 10, "nov": 11, "dec": 12,
    }
    for mname, mnum in month_map.items():
        if mname in sl:
            dm = re.search(r"(\d{1,2})", sl)
            ym = re.search(r"\b(20\d{2})\b", sl)
            if dm:
                day = int(dm.group(1))
                year = int(ym.group(1)) if ym else today.year
                try:
                    target = datetime.date(year, mnum, day)
                    if target < today and not ym:
                        target = datetime.date(today.year + 1, mnum, day)
                    return target.strftime("%Y-%m-%d")
                except ValueError:
                    pass

    # ── "next <weekday>" e.g. "next Friday" ──────────────────────────────────
    weekday_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    for wname, wnum in weekday_map.items():
        if wname in sl:
            days_ahead = (wnum - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # "next Friday" when today is Friday → next week
            return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # ── Explicit format parsing ───────────────────────────────────────────────
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
                "%m-%d-%Y", "%m/%d/%Y",
                "%B %d %Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # ── Relative numeric offsets ──────────────────────────────────────────────
    days_m  = re.search(r"(\d+)\s+days?", sl)
    weeks_m = re.search(r"(\d+)\s+weeks?", sl)
    months_m = re.search(r"(\d+)\s+months?", sl)

    if days_m:
        base = today
        if "yesterday" in sl:
            base = today - datetime.timedelta(days=1)
        elif "tomorrow" in sl:
            base = today + datetime.timedelta(days=1)
        return (base + datetime.timedelta(days=int(days_m.group(1)))).strftime("%Y-%m-%d")

    if weeks_m:
        return (today + datetime.timedelta(weeks=int(weeks_m.group(1)))).strftime("%Y-%m-%d")

    if months_m:
        months = int(months_m.group(1))
        m = today.month + months
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        import calendar
        d = min(today.day, calendar.monthrange(y, m)[1])
        return datetime.date(y, m, d).strftime("%Y-%m-%d")

    # ── No match — return None so form is NOT incorrectly overwritten ─────────
    return None



# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    try:
        create_tables()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    yield

app = FastAPI(
    title="AI-First CRM HCP Module API",
    description="Backend API for managing HCP interactions with LangGraph agent integration.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local testing, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- HCP Endpoints -----------------

@app.get("/api/hcps", response_model=List[schemas.HCP])
def get_hcps(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(HCP)
    if search:
        query = query.filter(
            (HCP.name.like(f"%{search}%")) |
            (HCP.specialty.like(f"%{search}%")) |
            (HCP.clinic_name.like(f"%{search}%"))
        )
    return query.all()

@app.get("/api/hcps/{hcp_id}", response_model=schemas.HCP)
def get_hcp_by_id(hcp_id: int, db: Session = Depends(get_db)):
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
    return hcp

# ----------------- Interaction Endpoints -----------------

@app.get("/api/interactions", response_model=List[schemas.Interaction])
def get_interactions(hcp_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Interaction)
    if hcp_id:
        query = query.filter(Interaction.hcp_id == hcp_id)
    return query.order_by(Interaction.date.desc()).all()

@app.post("/api/interactions", response_model=schemas.Interaction, status_code=status.HTTP_201_CREATED)
def create_interaction(interaction_in: schemas.InteractionCreate, db: Session = Depends(get_db)):
    # Validate HCP exists
    hcp = db.query(HCP).filter(HCP.id == interaction_in.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
        
    db_interaction = Interaction(**interaction_in.dict())
    db.add(db_interaction)
    
    # Update HCP last interaction date
    hcp.last_interaction_date = interaction_in.date
    
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

@app.put("/api/interactions/{interaction_id}", response_model=schemas.Interaction)
def update_interaction(interaction_id: int, interaction_in: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    db_interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
        
    update_data = interaction_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_interaction, field, value)
        
    # If date is updated, synchronize HCP last interaction date
    if "date" in update_data:
        hcp = db.query(HCP).filter(HCP.id == db_interaction.hcp_id).first()
        if hcp:
            hcp.last_interaction_date = update_data["date"]
            
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

# ----------------- AI Agent Chat Endpoint -----------------

@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat_with_agent(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    try:
        lang_messages = []

        # 1. Inject contextual System Message when an HCP is selected in the UI
        if request.hcp_id:
            hcp = db.query(HCP).filter(HCP.id == request.hcp_id).first()
            if hcp:
                context_prompt = (
                    f"CONTEXT: The sales representative has currently selected HCP: {hcp.name} "
                    f"(ID: {hcp.id}, Specialty: {hcp.specialty}, Clinic: {hcp.clinic_name}). "
                    f"If the user asks to log an interaction or schedule a follow-up, "
                    f"use this HCP ID ({hcp.id}) directly — do NOT search for the HCP again unless they explicitly name a different doctor."
                )
                lang_messages.append(SystemMessage(content=context_prompt))

        # 2. Map frontend chat history → LangChain message models
        # NOTE: We intentionally exclude tool_calls from history messages.
        # Re-injecting old tool call schemas confuses the model and causes
        # it to generate malformed <function=...> XML instead of JSON tool calls.
        if request.history:
            for item in request.history:
                role    = item.get("role")
                content = item.get("content", "")
                if role == "user":
                    lang_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    # Always append as plain text — no tool_calls in history
                    lang_messages.append(AIMessage(content=content))
                elif role == "system":
                    lang_messages.append(SystemMessage(content=content))
                # Skip "tool" role messages from history — they are part of the old turn

        # 3. Append the new user message
        lang_messages.append(HumanMessage(content=request.message))

        # 4. Invoke LangGraph agent
        logger.info(f"Invoking LangGraph agent with {len(lang_messages)} messages.")
        response = graph.invoke({"messages": lang_messages})

        # 5. Process only response messages from the current turn
        new_messages = response.get("messages", [])[len(lang_messages):]
        
        agent_reply    = ""
        extracted_data = None
        tools_triggered = []

        # Collect tool calls only from new messages in this turn
        for msg in new_messages:
            if isinstance(msg, AIMessage):
                # Capture the last non-empty text reply
                if msg.content and str(msg.content).strip():
                    agent_reply = str(msg.content).strip()

                # Collect every tool call
                for tc in (getattr(msg, "tool_calls", None) or []):
                    tool_name = tc.get("name") or tc.get("function", {}).get("name", "")
                    tool_args = tc.get("args") or tc.get("function", {}).get("arguments", {})
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except Exception:
                            tool_args = {}
                    tool_id = tc.get("id", "")
                    tools_triggered.append({"name": tool_name, "args": tool_args, "id": tool_id})

                    # ── Map tool args → form fields ────────────────────────────
                    if tool_name == "log_interaction":
                        # Direct 1-to-1 mapping with form schema
                        log_data = {
                            "hcp_id":        tool_args.get("hcp_id"),
                            "date":          normalize_date(tool_args.get("date")),
                            "channel":       tool_args.get("channel"),
                            "topics":        tool_args.get("topics"),
                            "sentiment":     tool_args.get("sentiment"),
                            "notes":         tool_args.get("notes"),
                            "follow_up_date": normalize_date(tool_args.get("follow_up_date")),
                            "next_step":     tool_args.get("next_step"),
                        }
                        # Remove None/empty values so we only update what's present
                        log_data = {k: v for k, v in log_data.items() if v is not None}
                        extracted_data = {**(extracted_data or {}), **log_data}

                    elif tool_name == "edit_interaction":
                        # For edits, only send the fields that were actually changed
                        edit_fields = {}
                        field_map = {
                            "date": "date",
                            "channel": "channel",
                            "topics": "topics",
                            "sentiment": "sentiment",
                            "notes": "notes",
                            "follow_up_date": "follow_up_date",
                            "next_step": "next_step",
                        }
                        for arg_key, form_key in field_map.items():
                            val = tool_args.get(arg_key)
                            if val is not None:
                                if form_key in ["date", "follow_up_date"]:
                                    edit_fields[form_key] = normalize_date(val)
                                else:
                                    edit_fields[form_key] = val
                        if edit_fields:
                            # Merge with existing extracted_data if any
                            extracted_data = {**(extracted_data or {}), **edit_fields}

                    elif tool_name == "schedule_followup":
                        sched_fields = {}
                        if tool_args.get("follow_up_date"):
                            sched_fields["follow_up_date"] = normalize_date(tool_args["follow_up_date"])
                        if tool_args.get("next_step"):
                            sched_fields["next_step"] = tool_args["next_step"]
                        if sched_fields:
                            extracted_data = {**(extracted_data or {}), **sched_fields}

        # Fallback reply so it's never empty
        if not agent_reply:
            agent_reply = "I've processed your request. Is there anything else you need?"

        logger.info(
            f"Chat response: {len(tools_triggered)} tools triggered, "
            f"extracted_data={'yes' if extracted_data else 'no'}"
        )

        return schemas.ChatResponse(
            reply=agent_reply,
            extracted_data=extracted_data,
            tools_triggered=tools_triggered,
        )

    except Exception as e:
        logger.error(f"Error in chat_with_agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Agent error: {str(e)}",
        )

# ----------------- DB Maintenance Endpoints -----------------

@app.post("/api/seed", status_code=status.HTTP_200_OK)
def reset_and_seed_db(db: Session = Depends(get_db)):
    try:
        from app.database import seed_data
        # Clean current interactions and hcps
        db.query(Interaction).delete()
        db.query(HCP).delete()
        db.commit()
        # Seed
        seed_data(db)
        return {"status": "success", "message": "Database reset and seeded."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to seed database: {str(e)}")

# Run command handler (usually managed by uvicorn command line)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
