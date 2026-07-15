import json
import re
import datetime
import logging
from typing import TypedDict, Annotated, Sequence, List, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from app.config import settings
from app.agent_tools import sales_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LangGraph Agent State
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# MockLLM — used only when GROQ_API_KEY is absent or Groq init fails
# CRITICAL FIX: Every branch MUST return an AIMessage with EITHER non-empty
# content OR at least one tool_call. Never both empty — LangGraph will crash.
# ---------------------------------------------------------------------------
class MockLLM:
    """Keyword-based fallback agent that mimics LLM tool-calling without a real API."""

    def bind_tools(self, tools):
        return self

    def __call__(self, messages: List[BaseMessage]) -> AIMessage:
        last_message = messages[-1] if messages else None

        # ── After tool execution: summarise results and return text ──────────
        if isinstance(last_message, ToolMessage):
            tool_output = last_message.content or ""

            # ── search_hcp returned results: extract ID and log the interaction ─
            if "ID:" in tool_output and "No HCPs found" not in tool_output and "SUCCESS:" not in tool_output:
                # Check if we were searching before a log (look at previous AI message)
                was_searching_for_log = False
                for msg in reversed(messages[:-1]):  # skip last ToolMessage
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in (msg.tool_calls or []):
                            if tc.get("name") == "search_hcp":
                                was_searching_for_log = True
                                break
                    if was_searching_for_log:
                        break

                if was_searching_for_log:
                    # Extract first HCP ID from search result
                    hcp_id_match = re.search(r"ID:\s*(\d+)", tool_output)
                    if hcp_id_match:
                        hcp_id = int(hcp_id_match.group(1))
                        raw_text = ""
                        for msg in reversed(messages):
                            if isinstance(msg, HumanMessage):
                                raw_text = msg.content
                                break
                        text_lower = raw_text.lower()
                        follow_up = self._extract_follow_up_date(raw_text)
                        return AIMessage(
                            content=f"Found the HCP! Now logging the interaction...",
                            tool_calls=[{
                                "name": "log_interaction",
                                "args": {
                                    "hcp_id": hcp_id,
                                    "date": self._extract_interaction_date(raw_text),
                                    "channel": self._extract_channel(text_lower),
                                    "topics": self._extract_topics(text_lower),
                                    "sentiment": self._extract_sentiment(text_lower),
                                    "notes": f"Interaction details: {raw_text}",
                                    "follow_up_date": follow_up,
                                    "next_step": "Follow up with HCP" if follow_up else None,
                                    "raw_text": raw_text,
                                },
                                "id": f"mock_log_after_search_{len(messages)}",
                                "type": "tool_call",
                            }]
                        )
                # Not logging — just display the search results
                return AIMessage(content=f"Here are the results:\n\n{tool_output}")

            # ── search_hcp found nothing → ask user for details first ───────────
            if "No HCPs found" in tool_output:
                doctor_name = "this doctor"
                for msg in reversed(messages):
                    if isinstance(msg, HumanMessage):
                        name_match = re.search(
                            r"dr\.?\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", msg.content, re.IGNORECASE
                        )
                        if name_match:
                            doctor_name = "Dr. " + name_match.group(1).title()
                        break
                return AIMessage(
                    content=(
                        f"I couldn't find **{doctor_name}** in the database. "
                        f"To create their profile, please provide the following details:\n\n"
                        f"1. 🏥 **Specialty** (e.g. Cardiology, Oncology, General Practice)\n"
                        f"2. 🏢 **Clinic / Hospital name**\n"
                        f"3. 📞 **Phone number** (optional)\n"
                        f"4. 📧 **Email address** (optional)\n\n"
                        f"Once you provide these, I'll create the profile and log today's interaction automatically."
                    )
                )

            if "SUCCESS:" in tool_output:
                # After create_hcp success, immediately log the interaction
                hcp_id_match = re.search(r"ID:\s*(\d+)", tool_output)
                if hcp_id_match and "New HCP created" in tool_output:
                    hcp_id = int(hcp_id_match.group(1))
                    raw_text = ""
                    for msg in reversed(messages):
                        if isinstance(msg, HumanMessage):
                            raw_text = msg.content
                            break
                    text_lower = raw_text.lower()
                    follow_up = self._extract_follow_up_date(raw_text)
                    return AIMessage(
                        content=f"New HCP created! Now logging the interaction...",
                        tool_calls=[{
                            "name": "log_interaction",
                            "args": {
                                "hcp_id": hcp_id,
                                "date": self._extract_interaction_date(raw_text),
                                "channel": self._extract_channel(text_lower),
                                "topics": self._extract_topics(text_lower),
                                "sentiment": self._extract_sentiment(text_lower),
                                "notes": f"Interaction details: {raw_text}",
                                "follow_up_date": follow_up,
                                "next_step": "Follow up with HCP" if follow_up else None,
                                "raw_text": raw_text,
                            },
                            "id": f"mock_log_after_create_{len(messages)}",
                            "type": "tool_call",
                        }]
                    )
                return AIMessage(
                    content=f"✅ Operation completed successfully!\n\n{tool_output}"
                )
            elif "ERROR" in tool_output.upper() or "Error" in tool_output:
                return AIMessage(
                    content=f"⚠️ The action encountered an issue:\n\n{tool_output}"
                )
            else:
                return AIMessage(
                    content=f"Here are the results:\n\n{tool_output}"
                )

        # ── Guard: stop loops ─────────────────────────────────────────────────
        if isinstance(last_message, AIMessage):
            content = (last_message.content or "").strip()
            if content:
                return AIMessage(content="Is there anything else I can help you with?")
            # If AIMessage is also empty (shouldn't happen) just give a safe reply
            return AIMessage(content="How can I help you manage your HCP interactions today?")

        # ── Only act on new user messages ─────────────────────────────────────
        if not isinstance(last_message, HumanMessage):
            return AIMessage(
                content="I'm your AI Sales Copilot. How can I assist you with HCP interactions today?"
            )

        text = last_message.content.lower()

        # ── Detect if user is providing HCP details after being asked ────────
        # Check if previous AI message was asking for specialty/clinic details
        prev_ai_asked_for_details = False
        pending_doctor_name = None
        pending_interaction_text = None
        for msg in reversed(messages[:-1]):  # Skip last HumanMessage
            if isinstance(msg, AIMessage):
                if "provide the following details" in (msg.content or "") or \
                   "couldn't find" in (msg.content or "").lower():
                    prev_ai_asked_for_details = True
                    # Find the original doctor name from older human messages
                    for older_msg in reversed(messages):
                        if isinstance(older_msg, HumanMessage) and older_msg != last_message:
                            nm = re.search(
                                r"dr\.?\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
                                older_msg.content, re.IGNORECASE
                            )
                            if nm:
                                pending_doctor_name = "Dr. " + nm.group(1).title()
                                pending_interaction_text = older_msg.content
                            break
                break

        if prev_ai_asked_for_details and pending_doctor_name:
            # Extract details from the user's response
            specialty_match = re.search(
                r"(cardio|oncol|neuro|general practice|pediatri|endocrin|surgery|orthop|dermatol|radiol|psychiatr|gynecol|urol|gastro|pulmo|nephrol|ophth)",
                text, re.IGNORECASE
            )
            clinic_match = re.search(r"(?:clinic|hospital|center|centre|institute|medical)\s+(?:is\s+)?([^\.,\n]+)", text, re.IGNORECASE)
            phone_match = re.search(r"[\+\d][\d\s\-\(\)]{8,}", last_message.content)
            email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", last_message.content)

            # Also try to extract clinic as anything after "clinic:" or "hospital:" or just the quoted text
            clinic_name = "Unknown Clinic"
            if clinic_match:
                clinic_name = clinic_match.group(1).strip().title()
            else:
                # Try "at X clinic" or "X hospital"
                at_match = re.search(r"\bat\s+([A-Za-z\s]+(?:clinic|hospital|center|institute|medical)?)", last_message.content, re.IGNORECASE)
                if at_match:
                    clinic_name = at_match.group(1).strip().title()
                elif len(last_message.content.split()) <= 8:
                    # Short answer — might be just the clinic name
                    clinic_name = last_message.content.strip().title()

            specialty = specialty_match.group(0).title() if specialty_match else "General Practice"
            phone = phone_match.group(0).strip() if phone_match else None
            email = email_match.group(0) if email_match else None

            create_args = {
                "name": pending_doctor_name,
                "specialty": specialty,
                "clinic_name": clinic_name,
            }
            if phone:
                create_args["phone"] = phone
            if email:
                create_args["email"] = email

            return AIMessage(
                content=f"Thank you! Creating **{pending_doctor_name}**'s profile now...",
                tool_calls=[{
                    "name": "create_hcp",
                    "args": create_args,
                    "id": f"mock_create_with_details_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Log interaction — ALWAYS search first, then log ───────────────────
        if any(kw in text for kw in ["log", "met", "visited", "called", "emailed",
                                      "had a call", "spoke to", "discussed", "talked to",
                                      "i met", "i visited", "i called"]):
            # Extract doctor name for search
            name_match = re.search(
                r"dr\.?\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", last_message.content, re.IGNORECASE
            )
            query = name_match.group(0).strip() if name_match else self._extract_name(text)

            return AIMessage(
                content=f"Let me look up {query} in the database first...",
                tool_calls=[{
                    "name": "search_hcp",
                    "args": {"query": query},
                    "id": f"mock_search_before_log_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Edit interaction ──────────────────────────────────────────────────
        if any(kw in text for kw in ["edit", "update", "modify", "change", "correct",
                                      "sorry", "mistake", "fix"]):
            id_match = re.search(r"id\s*[:#]?\s*(\d+)", text)
            interaction_id = int(id_match.group(1)) if id_match else 1
            sentiment = self._extract_sentiment(text) if any(
                s in text for s in ["positive", "negative", "neutral"]
            ) else None
            notes = None
            if "note" in text or "notes" in text:
                notes = "Updated notes from representative."

            args = {"interaction_id": interaction_id}
            if sentiment:
                args["sentiment"] = sentiment
            if notes:
                args["notes"] = notes

            return AIMessage(
                content=f"Understood — I'll update interaction #{interaction_id} with your corrections.",
                tool_calls=[{
                    "name": "edit_interaction",
                    "args": args,
                    "id": f"mock_edit_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Schedule follow-up ────────────────────────────────────────────────
        if any(kw in text for kw in ["schedule", "follow-up", "followup", "reminder", "remind"]):
            hcp_id = self._extract_hcp_id(text)
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
            follow_up = date_match.group(0) if date_match else (
                datetime.date.today() + datetime.timedelta(days=7)
            ).strftime("%Y-%m-%d")
            return AIMessage(
                content=f"Scheduling a follow-up for HCP ID {hcp_id} on {follow_up}.",
                tool_calls=[{
                    "name": "schedule_followup",
                    "args": {
                        "hcp_id": hcp_id,
                        "follow_up_date": follow_up,
                        "next_step": "Follow up with HCP to review products and next steps.",
                    },
                    "id": f"mock_followup_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Interaction history ───────────────────────────────────────────────
        if any(kw in text for kw in ["history", "past", "prior", "last time", "logs", "previous"]):
            hcp_id = self._extract_hcp_id(text)
            return AIMessage(
                content=f"Fetching interaction history for HCP ID {hcp_id}...",
                tool_calls=[{
                    "name": "get_interaction_history",
                    "args": {"hcp_id": hcp_id},
                    "id": f"mock_history_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── HCP Profile ───────────────────────────────────────────────────────
        if any(kw in text for kw in ["profile", "details of", "info", "information about"]):
            hcp_id = self._extract_hcp_id(text)
            return AIMessage(
                content=f"Retrieving profile for HCP ID {hcp_id}...",
                tool_calls=[{
                    "name": "get_hcp_profile",
                    "args": {"hcp_id": hcp_id},
                    "id": f"mock_profile_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Search HCP ────────────────────────────────────────────────────────
        if any(kw in text for kw in ["search", "find", "who is", "look up",
                                      "jenkins", "chen", "taylor", "patel", "cooper"]):
            query = self._extract_name(text)
            return AIMessage(
                content=f"Searching the HCP database for '{query}'...",
                tool_calls=[{
                    "name": "search_hcp",
                    "args": {"query": query},
                    "id": f"mock_search_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Next Best Action ──────────────────────────────────────────────────
        if any(kw in text for kw in ["suggest", "recommend", "next action", "best action", "what should"]):
            hcp_id = self._extract_hcp_id(text)
            return AIMessage(
                content=f"Analyzing interaction data to suggest next best action for HCP ID {hcp_id}...",
                tool_calls=[{
                    "name": "suggest_next_best_action",
                    "args": {"hcp_id": hcp_id},
                    "id": f"mock_suggest_{len(messages)}",
                    "type": "tool_call",
                }]
            )

        # ── Default response — ALWAYS non-empty ───────────────────────────────
        return AIMessage(
            content=(
                "👋 I'm your AI Sales Copilot. Here's what I can do:\n\n"
                "• **Log an interaction** — Tell me about a visit (e.g. 'I met Dr. Jenkins today, she was positive')\n"
                "• **Edit a log** — Correct a mistake (e.g. 'Change the sentiment to negative')\n"
                "• **Get history** — 'Show me Dr. Chen's past interactions'\n"
                "• **Schedule follow-up** — 'Schedule a follow-up with Dr. Taylor on 2026-08-01'\n"
                "• **Search HCP** — 'Find Dr. Patel'\n"
                "• **Get HCP profile** — 'Show me Dr. Cooper's profile'\n"
                "• **Next best action** — 'What should I do next with Dr. Jenkins?'\n\n"
                "Select an HCP on the left panel first, then describe what happened during your visit."
            )
        )

    # ── Helper methods ────────────────────────────────────────────────────────
    def _extract_hcp_id(self, text: str) -> int:
        id_match = re.search(r"hcp\s*(?:id)?\s*[:#]?\s*(\d+)", text)
        if id_match:
            return int(id_match.group(1))
        if "jenkins" in text or "sarah" in text:   return 1
        if "chen"    in text or "robert" in text:   return 2
        if "taylor"  in text or "emily"  in text:   return 3
        if "patel"   in text or "david"  in text:   return 4
        if "cooper"  in text or "lisa"   in text:   return 5
        return 1

    def _extract_channel(self, text: str) -> str:
        if any(w in text for w in ["phone", "called", "call"]):    return "Phone"
        if any(w in text for w in ["email", "emailed"]):           return "Email"
        if any(w in text for w in ["video", "zoom", "teams"]):     return "Video Call"
        return "In-Person"

    def _extract_topics(self, text: str) -> str:
        topics = []
        if "cardio"  in text: topics.append("CardioSphere-10mg")
        if "onco"    in text: topics.append("OncoShield-X")
        if "pedia"   in text: topics.append("PediaMelt Iron")
        if "trial"   in text: topics.append("Clinical Trial")
        if "brochure" in text or "sample" in text: topics.append("Product Literature")
        if "safety"  in text: topics.append("Safety Profile")
        return ", ".join(topics) if topics else "General Product Discussion"

    def _extract_sentiment(self, text: str) -> str:
        if any(w in text for w in ["positive", "great", "excited", "enthusiastic", "happy"]): return "Positive"
        if any(w in text for w in ["negative", "difficult", "unhappy", "concerned", "bad"]):  return "Negative"
        return "Neutral"

    def _extract_name(self, text: str) -> str:
        for name in ["Jenkins", "Chen", "Taylor", "Patel", "Cooper"]:
            if name.lower() in text:
                return name
        # Try to extract after "find/search/who is"
        match = re.search(r"(?:find|search|who is|look up)\s+(?:dr\.?\s+)?(\w+)", text)
        return match.group(1).capitalize() if match else "Jenkins"

    def _extract_interaction_date(self, text: str) -> str:
        """Extract the date of the interaction from user text."""
        today = datetime.date.today()
        tl = text.lower()
        if "yesterday" in tl:
            return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if "last monday" in tl:
            return (today - datetime.timedelta(days=(today.weekday() + 7) % 7 + 7)).strftime("%Y-%m-%d")
        # default to today
        return today.strftime("%Y-%m-%d")

    def _extract_follow_up_date(self, text: str) -> Optional[str]:
        """
        Extract follow-up/next-appointment date from user text.
        Returns YYYY-MM-DD string or None if no follow-up mentioned.
        """
        today = datetime.date.today()
        tl = text.lower()

        # "on 17", "on the 17th", "appointment on 17"
        m = re.search(r"(?:on|appointment|follow[- ]?up)(?:\s+(?:the|on))?\s+(\d{1,2})(?:st|nd|rd|th)?(?!\s*(?:am|pm|\d))", tl)
        if m:
            day = int(m.group(1))
            if 1 <= day <= 31:
                try:
                    target = today.replace(day=day)
                    if target < today:
                        target = today.replace(month=today.month % 12 + 1, day=day) if today.month < 12 \
                            else datetime.date(today.year + 1, 1, day)
                    return target.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # "in 2 weeks", "in 3 days", "in 1 month"
        weeks_m = re.search(r"in\s+(\d+)\s+weeks?", tl)
        days_m  = re.search(r"in\s+(\d+)\s+days?", tl)
        months_m = re.search(r"in\s+(\d+)\s+months?", tl)
        if weeks_m:
            return (today + datetime.timedelta(weeks=int(weeks_m.group(1)))).strftime("%Y-%m-%d")
        if days_m:
            return (today + datetime.timedelta(days=int(days_m.group(1)))).strftime("%Y-%m-%d")
        if months_m:
            import calendar
            months = int(months_m.group(1))
            m2 = today.month + months
            y2 = today.year + (m2 - 1) // 12
            m2 = ((m2 - 1) % 12) + 1
            d2 = min(today.day, calendar.monthrange(y2, m2)[1])
            return datetime.date(y2, m2, d2).strftime("%Y-%m-%d")

        # "next friday / monday etc."
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        for wname, wnum in weekday_map.items():
            if wname in tl:
                days_ahead = (wnum - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        # "July 17", "17 July" etc.
        month_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        for mname, mnum in month_map.items():
            if mname in tl:
                dm = re.search(r"(\d{1,2})", tl.split(mname)[-1] or tl.split(mname)[0])
                if dm:
                    day = int(dm.group(1))
                    try:
                        return datetime.date(today.year, mnum, day).strftime("%Y-%m-%d")
                    except ValueError:
                        pass

        return None  # No follow-up mentioned


# ---------------------------------------------------------------------------
# System prompt injected into every agent conversation
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an AI sales copilot for pharmaceutical sales representatives. You help log, edit, and retrieve HCP (Healthcare Professional) interaction records using the tools available to you.

CRITICAL RULES FOR TOOL CALLS:
- Each parameter key must appear EXACTLY ONCE in your tool call JSON. Never repeat keys.
- Always use the CURRENT year 2026 in all dates, not 2024 or 2025.
- Use YYYY-MM-DD format for all dates (e.g. 2026-07-18 for July 18th 2026).

BEHAVIOR RULES:
1. When the user mentions meeting, calling, emailing, or visiting a doctor:
   a. First call search_hcp to find the HCP by name.
   b. If FOUND: immediately call log_interaction with their ID.
   c. If NOT FOUND: ask the user for these details before registering:
      - Medical specialty (e.g. Cardiology, General Practice, Oncology)
      - Clinic or hospital name (if user says "location X", use X as clinic_name)
      - Phone number (optional)
      - Email address (optional)

2. When the user provides HCP details (specialty, clinic/location, phone, email):
   - Call create_hcp with all provided information.
   - "location X" means clinic_name=X. Map these correctly.
   - Then immediately call log_interaction to log the original interaction.

3. If a CONTEXT message at the start already gives you the HCP's ID, use it directly without searching.

4. For log_interaction, extract from the user's message:
   - channel: "met/visited" = In-Person, "called/phone" = Phone, "video call/zoom/teams" = Video Call, "email" = Email
   - sentiment: positive words = Positive, negative/difficult = Negative, otherwise = Neutral
   - topics: product names, procedures, or subjects discussed
   - notes: a professional one-sentence summary
   - date: exact date mentioned; convert to YYYY-MM-DD; default to today if not mentioned
   - follow_up_date: exact follow-up date; "on 18" or "on 18th" = 2026-07-18

5. For editing, only update the specific fields the user mentions.
6. Always reply concisely confirming what you did."""


# ---------------------------------------------------------------------------
# LLM Initialization
# ---------------------------------------------------------------------------
_mock_llm_instance = None
_groq_client = None   # Direct Groq client — bypasses LangChain message conversion
using_mock = False

# Build tool schemas for the Groq API (raw OpenAI-compatible format)
def _simplify_prop(prop: dict, defs: dict) -> dict:
    """
    Recursively simplify a Pydantic JSON schema property to a clean
    OpenAI-compatible format that Groq models can handle without confusion.
    - Resolves $ref references from $defs
    - Collapses anyOf:[str, null] -> {type: string}  (Optional[str] pattern)
    - Strips title, default, examples noise
    """
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        prop = defs.get(ref_name, {}).copy()

    prop = {k: v for k, v in prop.items() if k not in ("title", "default", "examples")}

    # Collapse Optional[X] → X  (anyOf with null)
    if "anyOf" in prop:
        non_null = [p for p in prop["anyOf"] if p.get("type") != "null"]
        if len(non_null) == 1:
            simplified = non_null[0].copy()
            if "description" in prop:
                simplified["description"] = prop["description"]
            prop = simplified
        # else keep anyOf as-is (union of real types)

    # Recurse into nested objects
    if prop.get("type") == "object" and "properties" in prop:
        prop["properties"] = {
            k: _simplify_prop(v, defs) for k, v in prop["properties"].items()
        }

    return prop


def _build_groq_tools():
    """Build clean OpenAI-compatible tool schemas from LangChain @tool functions."""
    schemas = []
    for fn in sales_tools:
        raw_schema = (
            fn.args_schema.model_json_schema()
            if hasattr(fn, "args_schema") and fn.args_schema
            else {}
        )
        defs = raw_schema.get("$defs", {})
        raw_props = raw_schema.get("properties", {})

        cleaned_props = {}
        for k, v in raw_props.items():
            prop = _simplify_prop(v, defs)
            # Prevent Groq type validation errors by allowing IDs to be sent as strings
            if k == "hcp_id" or k == "interaction_id" or k.endswith("_id"):
                prop["type"] = "string"
                prop["description"] = prop.get("description", "") + " (pass as string or number)"
            cleaned_props[k] = prop

        params = {
            "type": "object",
            "properties": cleaned_props,
            "required": raw_schema.get("required", []),
        }

        schemas.append({
            "type": "function",
            "function": {
                "name": fn.name,
                "description": (fn.description or "").split("\n")[0][:200],  # keep concise
                "parameters": params,
            }
        })
    return schemas


_groq_tools_schema = None

if settings.GROQ_API_KEY:
    try:
        from groq import Groq as GroqClient
        _groq_client = GroqClient(api_key=settings.GROQ_API_KEY)
        _groq_tools_schema = _build_groq_tools()
        logger.info(f"✅ Direct Groq client initialized: {settings.MODEL_NAME} with {len(_groq_tools_schema)} tools")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq client: {e}. Falling back to Mock LLM.")
        _mock_llm_instance = MockLLM()
        using_mock = True
else:
    logger.warning("⚠️ GROQ_API_KEY not set. Running in Mock Agent mode.")
    _mock_llm_instance = MockLLM()
    using_mock = True


def _lc_to_groq_messages(messages):
    """Convert LangChain message objects → raw dicts for the Groq API."""
    result = []
    for m in messages:
        if isinstance(m, SystemMessage):
            result.append({"role": "system", "content": str(m.content)})
        elif isinstance(m, HumanMessage):
            result.append({"role": "user", "content": str(m.content)})
        elif isinstance(m, AIMessage):
            msg: dict = {"role": "assistant", "content": str(m.content) if m.content else ""}
            # Include tool_calls if present (for multi-turn tool use)
            if getattr(m, "tool_calls", None):
                msg["tool_calls"] = [
                    {
                        "id": tc.get("id", f"tc_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"]) if isinstance(tc.get("args"), dict) else str(tc.get("args", "{}")),
                        }
                    }
                    for i, tc in enumerate(m.tool_calls)
                ]
            result.append(msg)
        elif isinstance(m, ToolMessage):
            result.append({
                "role": "tool",
                "tool_call_id": m.tool_call_id,
                "content": str(m.content),
            })
    return result


def _groq_to_lc_message(groq_msg) -> AIMessage:
    """Convert a Groq API response message → LangChain AIMessage."""
    content = groq_msg.content or ""
    tool_calls_raw = groq_msg.tool_calls or []
    if not tool_calls_raw:
        return AIMessage(content=content)

    lc_tool_calls = []
    for tc in tool_calls_raw:
        fn = tc.function
        try:
            args = json.loads(fn.arguments) if fn.arguments else {}
        except Exception:
            args = {}
        lc_tool_calls.append({
            "name": fn.name,
            "args": args,
            "id": tc.id,
            "type": "tool_call",
        })
    return AIMessage(content=content, tool_calls=lc_tool_calls)


def _invoke_llm(messages):
    """
    Unified LLM caller.
    - Uses the Groq API directly (no LangChain bind_tools) to avoid the
      <function=...> malformed XML tool call format caused by LangChain's
      message conversion layer.
    - For MockLLM fallback when no API key is available.
    """
    if _groq_client is not None:
        groq_messages = _lc_to_groq_messages(messages)
        response = _groq_client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=groq_messages,
            tools=_groq_tools_schema,
            tool_choice="auto",
            temperature=0,
        )
        return _groq_to_lc_message(response.choices[0].message)
    else:
        return _mock_llm_instance(messages)



# ---------------------------------------------------------------------------
# LangGraph Node: call_model
# ---------------------------------------------------------------------------
def call_model(state: AgentState):
    messages = list(state["messages"])

    # Inject system prompt at the very beginning if not already there
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    try:
        response = _invoke_llm(messages)
    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        # Return a safe fallback so LangGraph doesn't crash
        response = AIMessage(
            content=f"I encountered an error processing your request: {str(e)}. Please try again."
        )

    # Safety guard: ensure response is never empty content + no tool calls
    if isinstance(response, AIMessage):
        has_content   = bool(response.content and str(response.content).strip())
        has_toolcalls = bool(getattr(response, "tool_calls", None))
        if not has_content and not has_toolcalls:
            response = AIMessage(
                content="I've processed your request. Is there anything else you'd like me to help with?"
            )

    return {"messages": [response]}


# ---------------------------------------------------------------------------
# Build the LangGraph Workflow
# ---------------------------------------------------------------------------
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(sales_tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

# Compile
graph = workflow.compile()
logger.info("✅ LangGraph workflow compiled successfully.")
