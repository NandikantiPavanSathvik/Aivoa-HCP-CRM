from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# HCP Schemas
class HCPBase(BaseModel):
    name: str
    specialty: str
    clinic_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    last_interaction_date: Optional[str] = None

class HCPCreate(HCPBase):
    pass

class HCP(HCPBase):
    id: int

    class Config:
        from_attributes = True

# Interaction Schemas
class InteractionBase(BaseModel):
    hcp_id: int
    date: str
    channel: str
    topics: str
    sentiment: str
    notes: str
    follow_up_date: Optional[str] = None
    next_step: Optional[str] = None
    raw_text: Optional[str] = None

class InteractionCreate(InteractionBase):
    pass

class InteractionUpdate(BaseModel):
    date: Optional[str] = None
    channel: Optional[str] = None
    topics: Optional[str] = None
    sentiment: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    next_step: Optional[str] = None
    raw_text: Optional[str] = None

class Interaction(InteractionBase):
    id: int
    created_at: datetime
    hcp: Optional[HCPBase] = None

    class Config:
        from_attributes = True

# Chat Schemas
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    hcp_id: Optional[int] = None # Current context HCP if selected
    history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    reply: str
    # If the agent extracted data to pre-populate or update the form, return it here:
    extracted_data: Optional[dict] = None
    # Details of tools triggered
    tools_triggered: Optional[List[dict]] = None
