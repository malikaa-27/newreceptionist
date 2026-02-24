# AI Scheduling Agent

A production-ready AI scheduling assistant that lets users schedule meetings via natural conversation. The agent checks Google Calendar availability for all participants, negotiates times conversationally, and creates events with Google Meet links.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Browser (Next.js)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Login Page  │  │  Chat UI     │  │  Meeting Confirm Card │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────────┘
          │ OAuth redirect  │ REST /agent/chat
          ▼                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                            │
│  ┌──────────┐  ┌─────────────────┐  ┌────────────────────────┐ │
│  │ /auth/*  │  │  /agent/chat    │  │  /calendar/*           │ │
│  │ OAuth2   │  │  Tool-calling   │  │  availability / events │ │
│  └──────────┘  └────────┬────────┘  └──────────┬─────────────┘ │
└───────────────────────── ┼ ──────────────────── ┼ ─────────────┘
                           │                       │
          ┌────────────────┘                       │
          ▼                                        ▼
┌──────────────────────┐              ┌────────────────────────┐
│   Smallest.ai Atom   │              │   Google Calendar API  │
│   (LLM + tools)      │              │   freebusy / events    │
└──────────────────────┘              └────────────────────────┘
          │
          ▼
┌──────────────────────┐
│  PostgreSQL (Docker) │
│  Users / Tokens /    │
│  Meetings            │
└──────────────────────┘
```

---

## Scheduling Flow Sequence

```
User        Frontend       Backend         Smallest.ai     Google Calendar
 │               │              │                │                 │
 │  "Schedule    │              │                │                 │
 │  call with    │   POST       │                │                 │
 │  Alice"──────►│  /agent/chat►│                │                 │
 │               │              │ call_smallest──►                 │
 │               │              │                │ asks: email?    │
 │               │              │◄───────────────│                 │
 │◄──────────────│◄─────────────│                │                 │
 │  "What's      │              │                │                 │
 │  Alice's      │              │                │                 │
 │  email?"      │              │                │                 │
 │ "alice@x.com" │   POST       │                │                 │
 │──────────────►│  /agent/chat►│                │                 │
 │               │              │ call_smallest──►                 │
 │               │              │                │tool: check_avail│
 │               │              │◄───────────────│                 │
 │               │              │ freebusy.query─────────────────► │
 │               │              │◄───────────────────────────────  │
 │               │              │ call_smallest──►                 │
 │               │              │                │ proposes 3 slots│
 │               │              │◄───────────────│                 │
 │◄──────────────│◄─────────────│                │                 │
 │  "Option 1:   │              │                │                 │
 │  Tue 2pm..."  │              │                │                 │
 │  [Select]     │              │                │                 │
 │ clicks slot   │   POST       │                │                 │
 │──────────────►│  /agent/chat►│                │                 │
 │               │              │ call_smallest──►                 │
 │               │              │                │tool:create_event│
 │               │              │◄───────────────│                 │
 │               │              │ events.insert──────────────────► │
 │               │              │◄───────────────────────────────  │
 │               │              │ call_smallest──►                 │
 │               │              │                │ confirms booking│
 │               │              │◄───────────────│                 │
 │◄──────────────│◄─────────────│                │                 │
 │  [Meeting     │              │                │                 │
 │   Card + Meet │              │                │                 │
 │   link]       │              │                │                 │
```

---

## Folder Structure

```
newreceptionist/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic settings (env vars)
│   │   ├── database.py        # SQLAlchemy engine + session
│   │   ├── main.py            # FastAPI app, middleware, routers
│   │   ├── models.py          # User, OAuthToken, Meeting models
│   │   ├── routers/
│   │   │   ├── auth.py        # /auth/login, /callback, /me, /logout
│   │   │   ├── calendar.py    # /calendar/availability, /calendar/events
│   │   │   └── agent.py       # /agent/chat (agentic loop)
│   │   ├── schemas/
│   │   │   └── schemas.py     # Pydantic request/response models
│   │   └── services/
│   │       ├── agent_service.py     # Smallest.ai integration + session mgmt
│   │       ├── calendar_service.py  # freebusy + event creation
│   │       ├── encryption.py        # Fernet token encryption/decryption
│   │       └── google_auth.py       # OAuth token storage + refresh
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── globals.css
│   │   │   ├── page.tsx            # Login page
│   │   │   └── chat/
│   │   │       └── page.tsx        # Chat interface
│   │   ├── components/
│   │   │   ├── MeetingConfirmationCard.tsx
│   │   │   ├── TimeSlotButtons.tsx
│   │   │   └── TypingIndicator.tsx
│   │   └── lib/
│   │       └── api.ts              # Axios client + API helpers
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   └── Dockerfile
├── tests/
│   ├── test_availability.py   # Unit tests for availability intersection logic
│   └── test_event_creation.py # Integration tests with mocked Google API
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- A Google Cloud project with OAuth 2.0 credentials and Calendar API enabled
- A Smallest.ai API key

### 1. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable **Google Calendar API** and **Google OAuth2 API**.
4. Create OAuth 2.0 credentials (Web application type).
5. Add `http://localhost:8000/auth/callback` to **Authorized redirect URIs**.

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual values
```

Generate the encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate the secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Run with Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 4. Run Backend Locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Run Frontend Locally (without Docker)

```bash
cd frontend
npm install
npm run dev
```

### 6. Run Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Production Deployment

1. Set `ENVIRONMENT=production` in your `.env`.
2. Configure a reverse proxy (nginx/Caddy) with TLS termination.
3. Update `FRONTEND_URL` and `BACKEND_URL` to your production domains.
4. Add the production callback URL to Google OAuth credentials.
5. Use managed PostgreSQL (Cloud SQL, RDS, etc.) and update `DATABASE_URL`.
6. Deploy with:

```bash
docker compose -f docker-compose.yml up -d --build
```

---

## Tool Schema Definitions

### `check_availability`

```json
{
  "type": "function",
  "function": {
    "name": "check_availability",
    "description": "Check calendar availability for a list of emails within a time range.",
    "parameters": {
      "type": "object",
      "properties": {
        "emails": { "type": "array", "items": { "type": "string" } },
        "start_range": { "type": "string", "description": "ISO 8601 UTC start" },
        "end_range":   { "type": "string", "description": "ISO 8601 UTC end" },
        "duration_minutes": { "type": "integer" }
      },
      "required": ["emails", "start_range", "end_range", "duration_minutes"]
    }
  }
}
```

### `create_calendar_event`

```json
{
  "type": "function",
  "function": {
    "name": "create_calendar_event",
    "description": "Create a Google Calendar event with Meet link and send invites.",
    "parameters": {
      "type": "object",
      "properties": {
        "start":     { "type": "string", "description": "ISO 8601 UTC start" },
        "end":       { "type": "string", "description": "ISO 8601 UTC end" },
        "attendees": { "type": "array", "items": { "type": "string" } },
        "title":     { "type": "string" }
      },
      "required": ["start", "end", "attendees"]
    }
  }
}
```

---

## Example Conversation

```
User:  I need to schedule a 30-minute call with alice@example.com next week.

Agent: Great! What time of day works best for you — morning, afternoon, or evening?
       Also, what timezone are you in?

User:  Afternoon, I'm in EST.

Agent: Got it! Let me check availability for both of you next week (Mon–Fri, 12pm–6pm EST)...
       [calls check_availability]

Agent: Here are 3 slots that work for both of you:

       ▸  Mon, Jan 20  –  2:00 PM – 2:30 PM EST
       ▸  Tue, Jan 21  –  3:00 PM – 3:30 PM EST
       ▸  Wed, Jan 22  –  1:00 PM – 1:30 PM EST

       Which one works for you?

User:  Can you show me something later on Tuesday?

Agent: Sure! How about Tuesday, Jan 21 at 4:30 PM – 5:00 PM EST?

User:  Perfect, let's go with that.

Agent: Confirming: Tuesday, Jan 21 at 4:30 PM – 5:00 PM EST with alice@example.com.
       Shall I create this event?

User:  Yes!

Agent: [calls create_calendar_event]
       ✅ Done! Your meeting is scheduled.
       📅 Tuesday, Jan 21 · 4:30–5:00 PM EST
       🎥 [Join Google Meet]
       Calendar invites have been sent to both attendees.
```

---

## Security Notes

- OAuth tokens are encrypted with Fernet (AES-128-CBC) before storage.
- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- CORS is restricted to the configured frontend URL.
- All secrets are sourced from environment variables — nothing is hardcoded.
- Token refresh is handled automatically when credentials expire.