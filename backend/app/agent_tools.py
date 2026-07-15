from langchain_core.tools import tool
from app.database import SessionLocal, HCP, Interaction
import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

@tool
def search_hcp(query: str) -> str:
    """Search for healthcare professionals (HCPs) by name, specialty, or clinic name."""
    db = SessionLocal()
    try:
        hcps = db.query(HCP).filter(
            (HCP.name.like(f"%{query}%")) | 
            (HCP.specialty.like(f"%{query}%")) | 
            (HCP.clinic_name.like(f"%{query}%"))
        ).all()
        
        if not hcps:
            return f"No HCPs found matching query: '{query}'"
            
        results = []
        for h in hcps:
            results.append(
                f"ID: {h.id} | Name: {h.name} | Specialty: {h.specialty} | Clinic: {h.clinic_name} | Email: {h.email or 'N/A'} | Phone: {h.phone or 'N/A'} | Last Interaction: {h.last_interaction_date or 'None'}"
            )
        return "\n".join(results)
    except Exception as e:
        logger.error(f"Error in search_hcp tool: {e}")
        return f"Error searching for HCP: {str(e)}"
    finally:
        db.close()

@tool
def get_interaction_history(hcp_id: int) -> str:
    """Retrieve the interaction log history for a specific HCP using their ID."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return f"HCP with ID {hcp_id} not found."
            
        interactions = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.date.desc()).all()
        if not interactions:
            return f"No prior interactions found for {hcp.name} (ID: {hcp_id})."
            
        results = [f"Interaction History for {hcp.name} (Specialty: {hcp.specialty}):"]
        for i in interactions:
            results.append(
                f"- [{i.date}] via {i.channel} | Topics: {i.topics} | Sentiment: {i.sentiment}\n"
                f"  Notes: {i.notes}\n"
                f"  Next Step: {i.next_step or 'None'} (Follow-up: {i.follow_up_date or 'None'})"
            )
        return "\n".join(results)
    except Exception as e:
        logger.error(f"Error in get_interaction_history tool: {e}")
        return f"Error retrieving interaction history: {str(e)}"
    finally:
        db.close()

@tool
def log_interaction(
    hcp_id: int,
    date: str,
    channel: str,
    topics: str,
    sentiment: str,
    notes: str,
    follow_up_date: Optional[str] = None,
    next_step: Optional[str] = None,
    raw_text: Optional[str] = None
) -> str:
    """
    Log a new interaction with an HCP.
    
    Parameters:
    - hcp_id: The ID of the HCP.
    - date: Date of interaction (YYYY-MM-DD format, or 'today').
    - channel: Communication channel (In-Person, Video Call, Email, Phone).
    - topics: Key topics or products discussed (comma-separated, e.g., 'CardioSphere-10mg, Safety Data').
    - sentiment: Sentiment of the HCP (Positive, Neutral, Negative).
    - notes: Detailed summary notes of the discussion.
    - follow_up_date: Optional scheduled date for the next follow-up (YYYY-MM-DD format).
    - next_step: Optional description of the action items or next steps.
    - raw_text: Raw transcription or conversational input from the representative.
    """
    db = SessionLocal()
    try:
        # Validate HCP
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return f"Error: HCP with ID {hcp_id} does not exist. Please search for the HCP first."
            
        if date == "today" or not date:
            date = datetime.date.today().strftime("%Y-%m-%d")
            
        # Create interaction
        interaction = Interaction(
            hcp_id=hcp_id,
            date=date,
            channel=channel,
            topics=topics,
            sentiment=sentiment,
            notes=notes,
            follow_up_date=follow_up_date,
            next_step=next_step,
            raw_text=raw_text
        )
        
        db.add(interaction)
        
        # Update HCP last interaction date
        hcp.last_interaction_date = date
        
        db.commit()
        
        # Return success with data structured for extraction
        return (
            f"SUCCESS: Logged interaction for {hcp.name} on {date}.\n"
            f"Extracted Entities:\n"
            f"- HCP ID: {hcp_id}\n"
            f"- Channel: {channel}\n"
            f"- Topics: {topics}\n"
            f"- Sentiment: {sentiment}\n"
            f"- Notes: {notes}\n"
            f"- Follow-up: {follow_up_date or 'None'}\n"
            f"- Next Step: {next_step or 'None'}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error in log_interaction tool: {e}")
        return f"Error logging interaction: {str(e)}"
    finally:
        db.close()

@tool
def edit_interaction(
    interaction_id: int,
    date: Optional[str] = None,
    channel: Optional[str] = None,
    topics: Optional[str] = None,
    sentiment: Optional[str] = None,
    notes: Optional[str] = None,
    follow_up_date: Optional[str] = None,
    next_step: Optional[str] = None
) -> str:
    """
    Edit/Modify an existing logged interaction. Provide only the fields that need updating.
    
    Parameters:
    - interaction_id: The ID of the interaction log to edit.
    - date: Updated date (YYYY-MM-DD).
    - channel: Updated communication channel.
    - topics: Updated topics discussed.
    - sentiment: Updated sentiment.
    - notes: Updated notes.
    - follow_up_date: Updated follow-up date.
    - next_step: Updated next step notes.
    """
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return f"Error: Interaction with ID {interaction_id} not found."
            
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        
        updates = []
        if date:
            interaction.date = date
            updates.append(f"Date -> {date}")
            if hcp:
                hcp.last_interaction_date = date
        if channel:
            interaction.channel = channel
            updates.append(f"Channel -> {channel}")
        if topics:
            interaction.topics = topics
            updates.append(f"Topics -> {topics}")
        if sentiment:
            interaction.sentiment = sentiment
            updates.append(f"Sentiment -> {sentiment}")
        if notes:
            interaction.notes = notes
            updates.append(f"Notes -> updated")
        if follow_up_date:
            interaction.follow_up_date = follow_up_date
            updates.append(f"Follow-up Date -> {follow_up_date}")
        if next_step:
            interaction.next_step = next_step
            updates.append(f"Next Step -> {next_step}")
            
        if not updates:
            return f"No updates provided for interaction ID {interaction_id}."
            
        db.commit()
        return f"SUCCESS: Updated interaction ID {interaction_id} for {hcp.name if hcp else 'HCP'}. Changes: {', '.join(updates)}."
    except Exception as e:
        db.rollback()
        logger.error(f"Error in edit_interaction tool: {e}")
        return f"Error editing interaction: {str(e)}"
    finally:
        db.close()

@tool
def schedule_followup(hcp_id: int, follow_up_date: str, next_step: str) -> str:
    """
    Schedule a future follow-up task or meeting with an HCP.
    This creates or updates the follow-up details on the HCP's most recent interaction.
    """
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return f"Error: HCP with ID {hcp_id} not found."
            
        # Find latest interaction
        latest = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.date.desc()).first()
        if latest:
            latest.follow_up_date = follow_up_date
            latest.next_step = next_step
            db.commit()
            return f"SUCCESS: Scheduled follow-up with {hcp.name} on {follow_up_date} (updated latest interaction ID {latest.id}). Task: {next_step}"
        else:
            # If no prior interaction exists, create a placeholder/scheduled interaction
            today = datetime.date.today().strftime("%Y-%m-%d")
            interaction = Interaction(
                hcp_id=hcp_id,
                date=today,
                channel="Phone",
                topics="Scheduled Follow-up",
                sentiment="Neutral",
                notes=f"Scheduled future follow-up: {next_step}",
                follow_up_date=follow_up_date,
                next_step=next_step
            )
            db.add(interaction)
            db.commit()
            return f"SUCCESS: No prior interactions found. Created a scheduled follow-up record for {hcp.name} on {follow_up_date}. Task: {next_step}"
    except Exception as e:
        db.rollback()
        logger.error(f"Error in schedule_followup tool: {e}")
        return f"Error scheduling follow-up: {str(e)}"
    finally:
        db.close()


@tool
def get_hcp_profile(hcp_id: int) -> str:
    """
    Get the full profile details of a Healthcare Professional (HCP) by their ID.
    Use this tool to retrieve name, specialty, clinic, email, phone and last interaction date.
    """
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return f"Error: HCP with ID {hcp_id} not found."
        return (
            f"HCP Profile:\n"
            f"- ID: {hcp.id}\n"
            f"- Name: {hcp.name}\n"
            f"- Specialty: {hcp.specialty}\n"
            f"- Clinic: {hcp.clinic_name}\n"
            f"- Email: {hcp.email or 'N/A'}\n"
            f"- Phone: {hcp.phone or 'N/A'}\n"
            f"- Last Interaction: {hcp.last_interaction_date or 'No prior visits'}"
        )
    except Exception as e:
        logger.error(f"Error in get_hcp_profile tool: {e}")
        return f"Error retrieving HCP profile: {str(e)}"
    finally:
        db.close()

@tool
def suggest_next_best_action(hcp_id: int) -> str:
    """
    Analyze an HCP's interaction history and suggest the next best sales action.
    Returns a strategic recommendation for the sales representative based on past visits,
    sentiment trends, and outstanding follow-ups.
    """
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return f"Error: HCP with ID {hcp_id} not found."

        interactions = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp_id)
            .order_by(Interaction.date.desc())
            .limit(5)
            .all()
        )

        if not interactions:
            return (
                f"No prior interactions found for {hcp.name}. "
                f"Recommendation: Schedule an introductory in-person visit to introduce your product portfolio."
            )

        latest = interactions[0]
        sentiments = [i.sentiment for i in interactions]
        positive_count = sentiments.count("Positive")
        negative_count = sentiments.count("Negative")
        pending_followups = [i for i in interactions if i.follow_up_date and not i.next_step]

        suggestion_lines = [f"Next Best Action for {hcp.name} ({hcp.specialty} — {hcp.clinic_name}):"]

        # Pending follow-up check
        if latest.follow_up_date:
            suggestion_lines.append(
                f"• URGENT: Outstanding follow-up on {latest.follow_up_date} — '{latest.next_step or 'check-in'}'. Prioritize this."
            )

        # Sentiment-based strategy
        if positive_count >= len(interactions) * 0.6:
            suggestion_lines.append(
                "• Sentiment is consistently POSITIVE. Consider proposing a formal trial enrollment or co-pay program."
            )
        elif negative_count >= len(interactions) * 0.4:
            suggestion_lines.append(
                "• CAUTION: Mixed/negative sentiment detected. Recommend a relationship-rebuilding visit with updated clinical evidence."
            )
        else:
            suggestion_lines.append(
                "• Sentiment is NEUTRAL. Share new product data or case studies to increase engagement."
            )

        # Topic-based recommendation
        last_topics = latest.topics.lower() if latest.topics else ""
        if "trial" in last_topics or "enrollment" in last_topics:
            suggestion_lines.append("• Follow up specifically on clinical trial enrollment status.")
        if "brochure" in last_topics or "sample" in last_topics:
            suggestion_lines.append("• Ensure promised brochures/samples have been delivered.")

        suggestion_lines.append(f"• Last channel used: {latest.channel}. Consider alternating with a different channel for variety.")

        return "\n".join(suggestion_lines)
    except Exception as e:
        logger.error(f"Error in suggest_next_best_action tool: {e}")
        return f"Error generating next best action: {str(e)}"
    finally:
        db.close()



@tool
def create_hcp(
    name: str,
    specialty: str = "General Practice",
    clinic_name: str = "Unknown Clinic",
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> str:
    """
    Create and register a new Healthcare Professional (HCP) in the database.
    Use this tool when search_hcp returns no results for a doctor the representative mentions.

    Parameters:
    - name: Full name of the HCP (e.g. 'Dr. Pavan Nandikanti').
    - specialty: Medical specialty (e.g. 'Cardiology', 'General Practice').
    - clinic_name: Name of the clinic or hospital.
    - email: Optional email address.
    - phone: Optional phone number.

    Returns the new HCP's ID so it can be used immediately in log_interaction.
    """
    db = SessionLocal()
    try:
        # Check if already exists (avoid duplicates)
        existing = db.query(HCP).filter(HCP.name.ilike(f"%{name}%")).first()
        if existing:
            return (
                f"HCP '{existing.name}' already exists in the database.\n"
                f"ID: {existing.id} | Specialty: {existing.specialty} | Clinic: {existing.clinic_name}"
            )

        new_hcp = HCP(
            name=name,
            specialty=specialty,
            clinic_name=clinic_name,
            email=email,
            phone=phone,
            last_interaction_date=None,
        )
        db.add(new_hcp)
        db.commit()
        db.refresh(new_hcp)

        return (
            f"SUCCESS: New HCP created successfully.\n"
            f"- ID: {new_hcp.id}\n"
            f"- Name: {new_hcp.name}\n"
            f"- Specialty: {new_hcp.specialty}\n"
            f"- Clinic: {new_hcp.clinic_name}\n"
            f"You can now log interactions for this HCP using ID {new_hcp.id}."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_hcp tool: {e}")
        return f"Error creating HCP: {str(e)}"
    finally:
        db.close()


# List of all tools for LangGraph agent binding
sales_tools = [
    search_hcp,
    create_hcp,
    get_interaction_history,
    log_interaction,
    edit_interaction,
    schedule_followup,
    get_hcp_profile,
    suggest_next_best_action,
]
