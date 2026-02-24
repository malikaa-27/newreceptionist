"""
AI agent service using Smallest.ai Atom model with tool-calling.
Manages conversation history per session (in-memory; replace with Redis in production).
"""
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import httpx
from ..config import get_settings

settings = get_settings()

# In-memory session store: {session_id: [messages]}
# NOTE: This is suitable for development only. In production, replace with
# a shared store such as Redis to support multiple workers and persistence.
_sessions: Dict[str, List[Dict[str, Any]]] = {}

SYSTEM_PROMPT = """You are an AI scheduling assistant. Your job is to help users schedule meetings by:
1. Extracting intent, participants, duration, and preferred time range from the conversation.
2. Checking calendar availability for all participants.
3. Proposing up to 3 available time slots.
4. Handling user preferences like "earlier", "later", "next week", "after 3pm".
5. Confirming the selected slot before creating the event.
6. Creating the calendar event once confirmed.

When you need to check availability or create an event, use the provided tools.
Always respond in a friendly, conversational tone.
Always ask for the participant's email, preferred date range, time of day, and duration if not provided.
Never hallucinate calendar results - always use the check_availability tool.
Before creating an event, explicitly confirm the chosen time with the user."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check calendar availability for a list of email addresses within a time range and return available slots of the requested duration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of participant email addresses to check availability for.",
                    },
                    "start_range": {
                        "type": "string",
                        "description": "ISO 8601 UTC start of the search window (e.g. 2024-01-15T09:00:00Z).",
                    },
                    "end_range": {
                        "type": "string",
                        "description": "ISO 8601 UTC end of the search window (e.g. 2024-01-15T18:00:00Z).",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Required meeting duration in minutes.",
                    },
                },
                "required": ["emails", "start_range", "end_range", "duration_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a Google Calendar event with a Meet link and send invites to all attendees.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "ISO 8601 UTC start datetime (e.g. 2024-01-15T14:00:00Z).",
                    },
                    "end": {
                        "type": "string",
                        "description": "ISO 8601 UTC end datetime (e.g. 2024-01-15T15:00:00Z).",
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Email addresses of all attendees including organizer.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Meeting title.",
                    },
                },
                "required": ["start", "end", "attendees"],
            },
        },
    },
]

SMALLEST_API_URL = "https://atoms-api.smallest.ai/v1/chat/completions"


def get_or_create_session(session_id: Optional[str]) -> str:
    if not session_id or session_id not in _sessions:
        session_id = session_id or str(uuid.uuid4())
        _sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return session_id


def add_user_message(session_id: str, content: str) -> None:
    _sessions[session_id].append({"role": "user", "content": content})


def add_assistant_message(session_id: str, content: str) -> None:
    _sessions[session_id].append({"role": "assistant", "content": content})


def add_tool_result(session_id: str, tool_call_id: str, tool_name: str, result: Any) -> None:
    _sessions[session_id].append(
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps(result),
        }
    )


async def call_smallest_ai(session_id: str) -> Dict[str, Any]:
    """Call Smallest.ai API with the current session messages."""
    headers = {
        "Authorization": f"Bearer {settings.smallest_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "atom-1",
        "messages": _sessions[session_id],
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(SMALLEST_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    return _sessions.get(session_id, [])


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
