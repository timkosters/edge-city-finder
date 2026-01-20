# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Edge City Finder is a full-stack application that discovers "Minimum Viable Towns"—distressed institutional properties (colleges, camps, resorts) suitable for community activation. It uses a three-stage AI funnel: Discovery (Scout) → Verification (Analyst) → Manual Review (Portal).

## Tech Stack

- **Backend**: Python FastAPI with Supabase (PostgreSQL)
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **AI/Search**: Google Gemini 1.5 Flash, Exa.ai, Tavily

## Development Commands

### Backend
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Runs on http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # Runs on http://localhost:3000
npm run build  # Production build
npm run lint   # ESLint
```

## Architecture

### Three-Stage Funnel
1. **Scout Agent** (`backend/app/scout/agent.py`): Searches LoopNet, Crexi, Auction.com, news sites via Exa.ai and Tavily. Returns properties with `funnel_stage="discovered"`.

2. **Analyst Agent** (`backend/app/analyst/agent.py`): Verifies URLs are accessible, uses Gemini to analyze pages, classifies as "qualified" (real listings), "interesting" (news/potential), or "dismissed". Extracts price, beds, acreage and generates viability score (0-100).

3. **Portal** (`frontend/src/app/page.tsx`): Two-tab dashboard (Qualified Leads / Interesting Finds) for manual review. Users can star, dismiss with reasons, or run custom searches.

### Key Files
- `backend/app/main.py` - FastAPI app with all endpoints
- `backend/app/models.py` - Pydantic models (Property, SearchResult, VerificationResult)
- `backend/app/database.py` - Supabase CRUD operations
- `frontend/src/components/PropertyCard.tsx` - Property display component

### API Endpoints
- `POST /api/scout/run` - Run full Scout + Analyst pipeline
- `POST /api/scout/search?query=...` - Custom search query
- `GET /api/properties/qualified` - Qualified leads
- `GET /api/properties/interesting` - Interesting finds
- `PATCH /api/properties/{id}/status` - Update property status
- `POST /api/properties/{id}/dismiss` - Dismiss with reason

## Environment Setup

Copy `backend/.env.example` to `backend/.env` and configure:
- `EXA_API_KEY` - Exa.ai (web search)
- `TAVILY_API_KEY` - Tavily (alternative search)
- `GEMINI_API_KEY` - Google Gemini (verification)
- `SUPABASE_URL` / `SUPABASE_KEY` - Database

Frontend works without database (shows empty state gracefully).
