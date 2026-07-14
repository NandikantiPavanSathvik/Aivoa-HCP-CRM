import logging
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
        
        # 1. Inject contextual System Message if an HCP is active in UI
        if request.hcp_id:
            hcp = db.query(HCP).filter(HCP.id == request.hcp_id).first()
            if hcp:
                context_prompt = (
                    f"CONTEXT: The sales representative has currently selected HCP: {hcp.name} (ID: {hcp.id}, Specialty: {hcp.specialty}). "
                    f"If the user asks to log an interaction or schedule a follow-up, default to using this HCP ID ({hcp.id}) "
                    f"unless they explicitly refer to another HCP name."
                )
                lang_messages.append(SystemMessage(content=context_prompt))
        
        # 2. Map chat history from frontend to LangChain message models
        if request.history:
            for item in request.history:
                role = item.get("role")
                content = item.get("content", "")
                if role == "user":
                    lang_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    # Reconstruct mock or real tool calls if present in history
                    tool_calls = item.get("tool_calls", None)
                    if tool_calls:
                        lang_messages.append(AIMessage(content=content, tool_calls=tool_calls))
                    else:
                        lang_messages.append(AIMessage(content=content))
                elif role == "system":
                    lang_messages.append(SystemMessage(content=content))
                elif role == "tool":
                    lang_messages.append(ToolMessage(content=content, tool_call_id=item.get("tool_call_id", "")))
        
        # Append the new user message
        lang_messages.append(HumanMessage(content=request.message))
        
        # 3. Invoke LangGraph agent loop
        response = graph.invoke({"messages": lang_messages})
        
        # 4. Process response messages to extract agent's text and tool activities
        agent_reply = ""
        extracted_data = None
        tools_triggered = []
        
        # Search backwards to find the final text output and tool calls
        for msg in reversed(response["messages"]):
            if isinstance(msg, AIMessage):
                if not agent_reply and msg.content:
                    agent_reply = msg.content
                
                # Check for tool invocations
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tools_triggered.append({
                            "name": tc["name"],
                            "args": tc["args"],
                            "id": tc.get("id", "")
                        })
                        
                        # Capture arguments from logging/editing tools to sync with React form
                        if tc["name"] in ["log_interaction", "edit_interaction"]:
                            extracted_data = tc["args"]
                        elif tc["name"] == "schedule_followup":
                            # We can also populate scheduling details
                            extracted_data = {
                                "follow_up_date": tc["args"].get("follow_up_date"),
                                "next_step": tc["args"].get("next_step")
                            }
        
        # Fallback if no AIMessage found with text (unlikely)
        if not agent_reply:
            agent_reply = "I've processed your request."
            
        return schemas.ChatResponse(
            reply=agent_reply,
            extracted_data=extracted_data,
            tools_triggered=tools_triggered
        )
        
    except Exception as e:
        logger.error(f"Error in chat_with_agent endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Agent error: {str(e)}"
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
