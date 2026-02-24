import json
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, AsyncGenerator
import dateparser
import pytz

from app.config import get_settings

settings = get_settings()

# Tool schemas for Smallest.ai Atom agent
TOOL_SCHEMAS = [
    {
        "name": "check_availability",
        "description": "Check calendar availability for meeting participants. Use this to find open time slots.",
        "parameters": {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of participant email addresses to check availability for",
                },
                "start_range": {
                    "type": "string",
                    "description": "Start of the search range in ISO 8601 format (UTC). Example: 2024-02-01T09:00:00+00:00",
                },
                "end_range": {
                    "type": "string",
                    "description": "End of the search range in ISO 8601 format (UTC). Example: 2024-02-07T17:00:00+00:00",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration of the meeting in minutes",
                },
            },
            "required": ["emails", "start_range", "end_range", "duration_minutes"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create a calendar event with a Google Meet link and send invites to all participants.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Title/summary of the meeting",
                },
                "start": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (UTC)",
                },
                "end": {
                    "type": "string",
                    "description": "End time in ISO 8601 format (UTC)",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses",
                },
                "description": {
                    "type": "string",
                    "description": "Optional meeting description/agenda",
                },
            },
            "required": ["summary", "start", "end", "attendees"],
        },
    },
]

SYSTEM_PROMPT = """You are an intelligent AI scheduling assistant. Your job is to help users schedule meetings efficiently.

You should:
1. Greet the user warmly and ask who they want to meet with and when
2. Extract: participant emails, preferred date/time range, meeting duration, and timezone
3. Use check_availability to find open slots for ALL participants
4. Propose exactly 3 time slots to the user in a friendly way
5. Handle natural responses like "earlier", "later", "next week", "after 3pm"
6. Confirm the final chosen slot clearly before creating the event
7. Use create_calendar_event once confirmed - include a Google Meet link
8. Confirm the booking with the event details and Meet link

Guidelines:
- Always work in UTC internally, but display times in the user's timezone
- When proposing times, format them nicely: "Monday, February 5th at 2:00 PM EST"
- If no slots are available, suggest a different date range
- Be conversational, friendly, and efficient
- Never hallucinate calendar results - always use the tools
- Ask for clarification if you're unsure about emails or times

Example flow:
User: "I need to schedule a call with john@company.com"
Assistant: "I'd be happy to help schedule a call with John! What date range works for you, and how long should the meeting be?"
"""

class AgentService:
    def __init__(self):
        self.api_key = settings.smallest_api_key
        self.base_url = "https://atoms.smallest.ai/v1"  # Smallest.ai Atom endpoint
        
    async def chat(
        self,
        messages: list[dict],
        tool_results: Optional[list[dict]] = None,
    ) -> dict:
        """Send messages to Smallest.ai Atom agent."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "atom-1",
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        
        if tool_results:
            payload["tool_results"] = tool_results
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    
    def parse_tool_call(self, response: dict) -> Optional[dict]:
        """Parse tool call from agent response."""
        choices = response.get("choices", [])
        if not choices:
            return None
        
        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        if not tool_calls:
            return None
        
        tool_call = tool_calls[0]
        return {
            "id": tool_call.get("id"),
            "name": tool_call["function"]["name"],
            "arguments": json.loads(tool_call["function"]["arguments"]),
        }
    
    def get_text_response(self, response: dict) -> Optional[str]:
        """Extract text response from agent."""
        choices = response.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        return message.get("content")
    
    def build_system_message(self) -> dict:
        return {"role": "system", "content": SYSTEM_PROMPT}
    
    def build_tool_result_message(self, tool_call_id: str, result: dict) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(result),
        }


agent_service = AgentService()
