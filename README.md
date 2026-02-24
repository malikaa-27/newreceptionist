# AI Scheduling Agent

A production-grade AI scheduling agent built with FastAPI, Next.js, and Google Calendar integration. Talk to the AI to schedule meetings — it checks availability, negotiates times, and creates Google Calendar events with Meet links.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Next.js Frontend (Port 3000)                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │   │
│  │  │  Login Page  │  │  Chat UI    │  │  Confirmation  │  │   │
│  │  │  (Google     │  │  (Messages, │  │  Card          │  │   │
│  │  │  OAuth)      │  │  Time Slots)│  │  (Meet Link)   │  │   │
│  │  └─────────────┘  └─────────────┘  └────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (REST API)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Port 8000)                     │
│                                                                 │
│  ┌────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ /api/auth  │  │ /api/agent  │  │    /api/calendar         │ │
│  │            │  │             │  │                          │ │
│  │ - /login   │  │ - /chat     │  │  - /availability         │ │
│  │ - /callback│  │             │  │  - /events               │ │
│  │ - /me      │  │             │  │                          │ │
│  └────────────┘  └──────┬──────┘  └──────────────────────────┘ │
│                         │                                       │
│              ┌──────────▼──────────┐                           │
│              │   Agent Service     │                           │
│              │                     │                           │
│              │  - Smallest.ai API  │                           │
│              │  - Tool Calling     │                           │
│              │  - check_avail.     │                           │
│              │  - create_event     │                           │
│              └──────────┬──────────┘                           │
└─────────────────────────┼───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │ Google OAuth │  │ Smallest.ai  │
│  Database    │  │   + Calendar │  │  Atom Agent  │
│              │  │     API      │  │              │
│  - users     │  │              │  │  - LLM       │
│  - tokens    │  │  - freebusy  │  │  - Tools     │
│  - meetings  │  │  - events    │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Scheduling Flow

```
User                 Frontend              Backend               Google Calendar
 │                      │                     │                        │
 │  "Schedule call       │                     │                        │
 │   with alice@..."     │                     │                        │
 │──────────────────────►│                     │                        │
 │                       │  POST /api/agent/   │                        │
 │                       │  chat               │                        │
 │                       │────────────────────►│                        │
 │                       │                     │  [AI: extract intent]  │
 │                       │                     │  tool: check_avail     │
 │                       │                     │────────────────────────►
 │                       │                     │  freebusy.query()      │
 │                       │                     │◄────────────────────────
 │                       │  "Here are 3 slots" │                        │
 │                       │◄────────────────────│                        │
 │  Propose 3 slots      │                     │                        │
 │◄──────────────────────│                     │                        │
 │                       │                     │                        │
 │  "Monday 2pm works"   │                     │                        │
 │──────────────────────►│                     │                        │
 │                       │  POST /api/agent/   │                        │
 │                       │  chat               │                        │
 │                       │────────────────────►│                        │
 │                       │                     │  tool: create_event    │
 │                       │                     │────────────────────────►
 │                       │                     │  events.insert()       │
 │                       │                     │◄────────────────────────
 │                       │  Meeting confirmed! │                        │
 │                       │◄────────────────────│                        │
 │  Confirmation card    │                     │                        │
 │◄──────────────────────│                     │                        │
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Google Cloud Console project with Calendar API enabled
- Smallest.ai API key

### 1. Clone and configure
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create/select a project
3. Enable Google Calendar API and OAuth2 API
4. Create OAuth 2.0 credentials (Web application type)
5. Add `http://localhost:8000/api/auth/callback` to Authorized redirect URIs
6. Copy Client ID and Client Secret to `.env`

### 3. Run with Docker
```bash
docker-compose up --build
```

### 4. Access
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/api/docs (debug mode)

## Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Database
```bash
# With PostgreSQL running locally:
psql -c "CREATE DATABASE scheduling_agent;"
# Tables are auto-created on first backend startup
```

### Run Tests
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## Production Deployment

### Security Checklist
- [ ] Set `secure=True` on cookies (requires HTTPS)
- [ ] Update `CORS_ORIGINS` to your domain
- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY` (32+ random chars)
- [ ] Update `GOOGLE_REDIRECT_URI` to production URL
- [ ] Use managed PostgreSQL (not the Docker container)
- [ ] Set up SSL/TLS termination (nginx, load balancer)
- [ ] Enable rate limiting

### Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | ✅ |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `SECRET_KEY` | JWT signing key (32+ chars) | ✅ |
| `SMALLEST_API_KEY` | Smallest.ai API key | ✅ |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL | Optional |
| `CORS_ORIGINS` | Allowed frontend origins | Optional |
| `DEBUG` | Enable debug mode | Optional |

## Example Conversation

```
AI: Hi! I'm your scheduling assistant. Who would you like to meet with, and when?

User: Schedule a 30-minute call with alice@company.com next week

AI: I'd be happy to help! Let me check availability for you and Alice next week.
    [checking calendar...]
    
    Here are 3 available times that work for both of you:
    
    1. 📅 Monday, Feb 5 at 10:00 AM EST
    2. 📅 Tuesday, Feb 6 at 2:00 PM EST  
    3. 📅 Wednesday, Feb 7 at 11:30 AM EST
    
    Which works best for you?

User: Tuesday at 2pm

AI: Perfect! Just to confirm:
    - Meeting with Alice (alice@company.com)
    - Tuesday, February 6th at 2:00 PM EST
    - Duration: 30 minutes
    
    Shall I go ahead and create the event?

User: Yes, go ahead!

AI: 🎉 Meeting scheduled! Here are the details:
    
    ✅ Calendar invite sent to alice@company.com
    📅 Tuesday, February 6 at 2:00 PM EST
    🔗 Google Meet: https://meet.google.com/abc-defg-hij
    
    You're all set! The invite should arrive in both inboxes shortly.
```

## Tool Schemas

### check_availability
```json
{
  "name": "check_availability",
  "parameters": {
    "emails": ["string"],
    "start_range": "ISO8601 datetime (UTC)",
    "end_range": "ISO8601 datetime (UTC)",
    "duration_minutes": "integer"
  }
}
```

### create_calendar_event
```json
{
  "name": "create_calendar_event",
  "parameters": {
    "summary": "string",
    "start": "ISO8601 datetime (UTC)",
    "end": "ISO8601 datetime (UTC)",
    "attendees": ["email strings"],
    "description": "string (optional)"
  }
}
```
