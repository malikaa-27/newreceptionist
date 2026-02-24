"""
AI Agent endpoint: manages multi-turn conversation with tool calling.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.google_auth import get_credentials
from ..services import calendar_service
from ..services import agent_service
from ..schemas.schemas import AgentRequest, AgentResponse, CreateEventResponse

router = APIRouter(prefix="/agent", tags=["agent"])
_SESSION_KEY = "user_id"


def _require_user(request: Request):
    user_id = request.session.get(_SESSION_KEY)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


async def _execute_tool(
    tool_name: str,
    tool_args: dict,
    credentials,
) -> dict:
    """Execute a tool call and return a JSON-serialisable result."""
    if tool_name == "check_availability":
        start_range = datetime.fromisoformat(tool_args["start_range"].replace("Z", "+00:00"))
        end_range = datetime.fromisoformat(tool_args["end_range"].replace("Z", "+00:00"))
        slots = calendar_service.check_availability(
            credentials=credentials,
            emails=tool_args["emails"],
            start_range=start_range,
            end_range=end_range,
            duration_minutes=tool_args["duration_minutes"],
        )
        return {
            "available_slots": [
                {"start": s.start.isoformat(), "end": s.end.isoformat()} for s in slots
            ]
        }

    elif tool_name == "create_calendar_event":
        start = datetime.fromisoformat(tool_args["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(tool_args["end"].replace("Z", "+00:00"))
        event = calendar_service.create_calendar_event(
            credentials=credentials,
            start=start,
            end=end,
            attendees=tool_args["attendees"],
            title=tool_args.get("title", "Scheduled Meeting"),
        )
        return {
            "event_id": event.event_id,
            "meet_link": event.meet_link,
            "start": event.start.isoformat(),
            "end": event.end.isoformat(),
        }

    raise ValueError(f"Unknown tool: {tool_name}")


@router.post("/chat", response_model=AgentResponse)
async def chat(
    body: AgentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    creds = get_credentials(db, user_id)
    if not creds:
        raise HTTPException(status_code=401, detail="No credentials found. Please log in again.")

    session_id = agent_service.get_or_create_session(body.session_id)
    agent_service.add_user_message(session_id, body.message)

    meeting_confirmed = False
    confirmed_event: Optional[CreateEventResponse] = None
    tool_calls_made = []

    # Agentic loop: let the model call tools until it returns a final message
    for _ in range(5):  # guard against infinite loops
        response = await agent_service.call_smallest_ai(session_id)
        choice = response["choices"][0]
        finish_reason = choice.get("finish_reason")
        msg = choice["message"]

        if finish_reason == "tool_calls" or msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])
            # Append assistant message with tool_calls to history
            agent_service._sessions[session_id].append(msg)

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                tool_args = json.loads(tc["function"]["arguments"])
                tool_call_id = tc["id"]

                try:
                    result = await _execute_tool(tool_name, tool_args, creds)
                except Exception as exc:
                    result = {"error": str(exc)}

                agent_service.add_tool_result(session_id, tool_call_id, tool_name, result)
                tool_calls_made.append({"name": tool_name, "result": result})

                # Detect meeting confirmation
                if tool_name == "create_calendar_event" and "error" not in result:
                    meeting_confirmed = True
                    confirmed_event = CreateEventResponse(
                        event_id=result["event_id"],
                        meet_link=result["meet_link"],
                        start=datetime.fromisoformat(result["start"]),
                        end=datetime.fromisoformat(result["end"]),
                    )
        else:
            # Final assistant message
            content = msg.get("content", "")
            agent_service.add_assistant_message(session_id, content)
            return AgentResponse(
                message=content,
                session_id=session_id,
                tool_calls=tool_calls_made if tool_calls_made else None,
                meeting_confirmed=meeting_confirmed,
                meeting_details=confirmed_event,
            )

    # Fallback if loop exhausted
    return AgentResponse(
        message="I'm having trouble processing your request. Please try again.",
        session_id=session_id,
        tool_calls=None,
        meeting_confirmed=False,
    )
