from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import json

from app.database import get_db
from app.api.auth import get_current_user
from app.services.agent import agent_service, SYSTEM_PROMPT
from app.services.oauth import get_credentials_for_user
from app.services.google_calendar import check_availability, create_calendar_event
from app.models.meeting import Meeting, MeetingStatus

router = APIRouter(prefix="/api/agent", tags=["agent"])

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    tool_called: Optional[str] = None
    meeting_created: Optional[dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the AI scheduling agent."""
    credentials = get_credentials_for_user(db, current_user["user_id"])
    
    # Build messages with system prompt
    messages = [agent_service.build_system_message()]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add current user context
    from app.models.user import User
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if user:
        context_msg = f"[Context: The current user is {user.name} ({user.email}), timezone: {user.timezone}]"
        messages[0]["content"] += f"\n\n{context_msg}"
    
    max_iterations = 5  # Prevent infinite loops
    tool_called = None
    meeting_created = None
    
    for _ in range(max_iterations):
        try:
            response = await agent_service.chat(messages)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
        
        # Check for tool call
        tool_call = agent_service.parse_tool_call(response)
        
        if tool_call:
            tool_called = tool_call["name"]
            tool_result = await _execute_tool(
                tool_call, credentials, db, current_user["user_id"]
            )
            
            # Track if meeting was created
            if tool_call["name"] == "create_calendar_event" and "event_id" in tool_result:
                meeting_created = tool_result
            
            # Add tool call and result to messages
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": json.dumps(tool_call["arguments"]),
                    },
                }],
            })
            messages.append(
                agent_service.build_tool_result_message(tool_call["id"], tool_result)
            )
            continue
        
        # Got a text response
        text = agent_service.get_text_response(response)
        if text:
            return ChatResponse(
                message=text,
                tool_called=tool_called,
                meeting_created=meeting_created,
            )
    
    return ChatResponse(
        message="I'm sorry, I encountered an issue processing your request. Please try again.",
        tool_called=tool_called,
    )

async def _execute_tool(
    tool_call: dict,
    credentials,
    db: Session,
    user_id: int,
) -> dict:
    """Execute a tool call and return the result."""
    name = tool_call["name"]
    args = tool_call["arguments"]
    
    if name == "check_availability":
        if not credentials:
            return {"error": "Google Calendar not connected. Please connect your Google account first."}
        try:
            from datetime import datetime
            start_range = datetime.fromisoformat(args["start_range"].replace("Z", "+00:00"))
            end_range = datetime.fromisoformat(args["end_range"].replace("Z", "+00:00"))
            slots = check_availability(
                credentials=credentials,
                emails=args["emails"],
                start_range=start_range,
                end_range=end_range,
                duration_minutes=args["duration_minutes"],
            )
            return {
                "available_slots": slots[:10],  # Return top 10 slots
                "total_found": len(slots),
            }
        except Exception as e:
            return {"error": f"Calendar check failed: {str(e)}"}
    
    elif name == "create_calendar_event":
        if not credentials:
            return {"error": "Google Calendar not connected."}
        try:
            from datetime import datetime
            start = datetime.fromisoformat(args["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(args["end"].replace("Z", "+00:00"))
            result = create_calendar_event(
                credentials=credentials,
                summary=args["summary"],
                start=start,
                end=end,
                attendees=args["attendees"],
                description=args.get("description", ""),
            )
            
            # Save meeting to DB
            meeting = Meeting(
                organizer_id=user_id,
                participant_email=args["attendees"][1] if len(args["attendees"]) > 1 else args["attendees"][0],
                start_time=start,
                end_time=end,
                google_event_id=result["event_id"],
                meet_link=result.get("meet_link"),
                status=MeetingStatus.CONFIRMED,
            )
            db.add(meeting)
            db.commit()
            
            return result
        except Exception as e:
            return {"error": f"Event creation failed: {str(e)}"}
    
    return {"error": f"Unknown tool: {name}"}
