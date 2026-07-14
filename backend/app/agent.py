import json
import re
import datetime
from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from app.config import settings
from app.agent_tools import sales_tools

# Define graph state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Custom Mock LLM for fallback when GROQ_API_KEY is not set
class MockLLM:
    def __init__(self):
        pass
        
    def bind_tools(self, tools):
        return self
        
    def __call__(self, messages: List[BaseMessage]):
        # Get the very last message in the conversation
        last_message = messages[-1]
        
        # If the last message is a ToolMessage, summarize the results and end
        if isinstance(last_message, ToolMessage):
            tool_output = last_message.content
            if "SUCCESS:" in tool_output:
                return AIMessage(
                    content=f"Operation successful! I've updated the database log. Here is the confirmation:\n\n{tool_output}"
                )
            else:
                return AIMessage(
                    content=f"I ran the action, but received the following status:\n\n{tool_output}"
                )
                
        # If the last message is already an AI Message, stop
        if isinstance(last_message, AIMessage):
            return AIMessage(content="Is there anything else I can help you with?")
            
        # Only parse HumanMessages for new tool execution decisions
        if not isinstance(last_message, HumanMessage):
            return AIMessage(content="How can I help you manage your HCP interactions?")
            
        last_msg = last_message.content.lower()
        
        # Check for log interaction
        if any(kw in last_msg for kw in ["log", "met", "visited", "called", "emailed", "had a call", "spoke to"]):
            hcp_id = 1
            if "jenkins" in last_msg or "sarah" in last_msg: hcp_id = 1
            elif "chen" in last_msg or "robert" in last_msg: hcp_id = 2
            elif "taylor" in last_msg or "emily" in last_msg: hcp_id = 3
            
            channel = "In-Person"
            if "call" in last_msg or "phone" in last_msg: channel = "Phone"
            elif "email" in last_msg: channel = "Email"
            elif "video" in last_msg or "zoom" in last_msg: channel = "Video Call"
            
            topics = "General Products"
            if "cardio" in last_msg: topics = "CardioSphere-10mg, Trial Results"
            elif "onco" in last_msg: topics = "OncoShield-X, Patient Enrollment"
            elif "pedia" in last_msg: topics = "PediaMelt Iron drops"
            
            sentiment = "Positive"
            if "neutral" in last_msg or "okay" in last_msg: sentiment = "Neutral"
            elif "negative" in last_msg or "difficult" in last_msg: sentiment = "Negative"
            
            notes = f"Visit details extracted: {last_message.content}"
            follow_up_date = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
            next_step = "Deliver brochures as requested"
            
            tool_call = {
                "name": "log_interaction",
                "args": {
                    "hcp_id": hcp_id,
                    "date": datetime.date.today().strftime("%Y-%m-%d"),
                    "channel": channel,
                    "topics": topics,
                    "sentiment": sentiment,
                    "notes": notes,
                    "follow_up_date": follow_up_date,
                    "next_step": next_step,
                    "raw_text": last_message.content
                },
                "id": "mock_call_log_" + str(len(messages))
            }
            return AIMessage(
                content="Mock LLM extracted details and is now logging the interaction.",
                tool_calls=[tool_call]
            )

        # Check for edit interaction
        if any(kw in last_msg for kw in ["edit", "update", "modify", "change"]):
            # Find an ID
            interaction_id = 1
            id_match = re.search(r"id\s*(\d+)", last_msg)
            if id_match:
                interaction_id = int(id_match.group(1))
                
            sentiment = "Positive" if "positive" in last_msg else ("Negative" if "negative" in last_msg else "Neutral")
            notes = "Updated details based on sales rep request"
            
            tool_call = {
                "name": "edit_interaction",
                "args": {
                    "interaction_id": interaction_id,
                    "sentiment": sentiment,
                    "notes": notes
                },
                "id": "mock_call_edit_" + str(len(messages))
            }
            return AIMessage(
                content=f"Updating interaction ID {interaction_id}...",
                tool_calls=[tool_call]
            )

        # Check for scheduling follow-up
        if any(kw in last_msg for kw in ["schedule", "followup", "follow-up", "reminder"]):
            hcp_id = 1
            if "jenkins" in last_msg or "sarah" in last_msg: hcp_id = 1
            elif "chen" in last_msg or "robert" in last_msg: hcp_id = 2
            elif "taylor" in last_msg or "emily" in last_msg: hcp_id = 3
            
            follow_up_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            next_step = "Follow up with HCP to review products"
            
            # Simple regex to find dates like 2026-07-20
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", last_msg)
            if date_match:
                follow_up_date = date_match.group(0)
                
            tool_call = {
                "name": "schedule_followup",
                "args": {
                    "hcp_id": hcp_id,
                    "follow_up_date": follow_up_date,
                    "next_step": next_step
                },
                "id": "mock_call_follow_" + str(len(messages))
            }
            return AIMessage(
                content=f"Scheduling follow-up task with HCP ID {hcp_id}...",
                tool_calls=[tool_call]
            )

        # Check for interaction history
        if any(kw in last_msg for kw in ["history", "past", "prior", "last time", "logs"]):
            hcp_id = 1
            if "jenkins" in last_msg or "sarah" in last_msg: hcp_id = 1
            elif "chen" in last_msg or "robert" in last_msg: hcp_id = 2
            elif "taylor" in last_msg or "emily" in last_msg: hcp_id = 3
            elif "patel" in last_msg or "david" in last_msg: hcp_id = 4
            elif "cooper" in last_msg or "lisa" in last_msg: hcp_id = 5
            
            tool_call = {
                "name": "get_interaction_history",
                "args": {"hcp_id": hcp_id},
                "id": "mock_call_history_" + str(len(messages))
            }
            return AIMessage(
                content=f"Fetching interaction history for HCP ID {hcp_id}...",
                tool_calls=[tool_call]
            )

        # Check for search HCP
        if any(kw in last_msg for kw in ["search", "find", "who is", "jenkins", "chen", "taylor", "patel", "cooper"]):
            # Extract query name
            query = "Jenkins"
            if "jenkins" in last_msg: query = "Jenkins"
            elif "chen" in last_msg: query = "Chen"
            elif "taylor" in last_msg: query = "Taylor"
            elif "patel" in last_msg: query = "Patel"
            elif "cooper" in last_msg: query = "Cooper"
            
            tool_call = {
                "name": "search_hcp",
                "args": {"query": query},
                "id": "mock_call_search_" + str(len(messages))
            }
            return AIMessage(
                content="Let me search the database for that healthcare professional.",
                tool_calls=[tool_call]
            )
            
        # Default response (No tools)
        return AIMessage(
            content="I am your AI Sales Copilot. You can tell me about your HCP interactions (e.g. 'I just called Dr. Sarah Jenkins, she was positive and we discussed CardioSphere. Follow up next week') and I will log it for you. You can also search HCPs, review histories, or schedule tasks."
        )

# Initialize LLM
system_prompt = (
    "You are an expert AI sales copilot for life science representatives in the pharmaceutical and medical device industries.\n"
    "Your primary goal is to help representatives quickly log and edit interaction logs (visit details) with Healthcare Professionals (HCPs).\n\n"
    "Available Actions / Tools:\n"
    "1. `search_hcp(query)`: Search for an HCP's ID and details by name, specialty, or clinic.\n"
    "2. `get_interaction_history(hcp_id)`: Retrieve previous logs for a specific HCP.\n"
    "3. `log_interaction(hcp_id, date, channel, topics, sentiment, notes, follow_up_date, next_step, raw_text)`: Register a new interaction. Auto-extract fields from user input. Default date to today if not mentioned.\n"
    "4. `edit_interaction(interaction_id, ...)`: Modify field values on an existing log.\n"
    "5. `schedule_followup(hcp_id, follow_up_date, next_step)`: Schedule next actions.\n\n"
    "GUIDELINES:\n"
    "- If the representative says they visited/called/met a doctor but you don't know their HCP ID, ALWAYS search for their name first using `search_hcp` to obtain the correct ID.\n"
    "- Extract values for `channel` (In-Person, Video Call, Email, Phone), `sentiment` (Positive, Neutral, Negative), and `topics` carefully from the conversation.\n"
    "- Once you execute a tool, report the results clearly and summarize the action. Keep replies concise and professional."
)

llm = None
if settings.GROQ_API_KEY:
    try:
        # Initialize Groq LLM
        llm = ChatGroq(
            temperature=0.1,
            model_name=settings.MODEL_NAME,
            groq_api_key=settings.GROQ_API_KEY
        )
        llm = llm.bind_tools(sales_tools)
        print("Using Groq LLM agent")
    except Exception as e:
        print(f"Error starting Groq Chat: {e}. Falling back to mock LLM.")
        llm = MockLLM().bind_tools(sales_tools)
else:
    print("GROQ_API_KEY not found. Starting backend in Mock Agent mode.")
    llm = MockLLM().bind_tools(sales_tools)

# Define agent logic
def call_model(state: AgentState):
    messages = state["messages"]
    
    # Inject system message if not present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=system_prompt)] + list(messages)
        
    response = llm(messages)
    return {"messages": [response]}

# Define Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(sales_tools))

# Add Edges
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)
workflow.add_edge("tools", "agent")

# Compile
graph = workflow.compile()
