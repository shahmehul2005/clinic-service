# Clinic Service

WhatsApp-first clinic operations platform for appointment booking, queue management, and reception workflows.

Live app: https://clinic-service-tawny.vercel.app

## Overview

This codebase powers a clinic scheduling system that lets patients interact through WhatsApp and lets staff manage the intake queue from a web dashboard.

Key flows in the project include:

- WhatsApp-based appointment and token booking
- Natural-language parsing for patient requests and clinic selection
- Slot-based scheduling and same-day token queue workflows
- Real-time reception dashboard with Supabase
- Notification and reminder flows for patients and staff
- Admin-only configuration and operational tooling

## Stack

| Layer | Technology |
| --- | --- |
| API / orchestration | FastAPI |
| LLM parsing | Groq |
| Database | Supabase Postgres |
| Auth | Supabase Auth |
| Frontend | React + Vite + React Router |
| Internationalization | i18next |
| Messaging | Meta WhatsApp Cloud API |
| Deployment | Vercel (frontend), Render / hosting for backend |

## Repository layout

```text
clinic-service/
├── .github/
│   └── workflows/
├── backend/
│   ├── __init__.py
│   ├── agent.py                    # FastAPI app, webhook handlers, API routes
│   ├── workflow.py                 # Booking workflow and state transitions
│   ├── ops.py                      # Slot/token helper functions and DB operations
│   ├── database_migration.sql      # Base schema and clinic data initialization
│   ├── reliability_migration.sql   # Slot and token integrity, reminder tracking
│   ├── reports_reviews_migration.sql
│   ├── advanced_settings_migration.sql
│   ├── enable_rls.sql
│   ├── cleanup_cron.sql
│   ├── requirements.txt
│   ├── conftest.py
│   ├── local_llm_test.py
│   ├── test_*.py
│   └── *.sql
├── frontend/
│   ├── public/
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json
│   └── README.md
├── .gitignore
├── README.md
└── LICENSE (if added later)
```

## Frontend app structure

The frontend is a Vite React app with multiple routes for both marketing and operational pages.

Main app routes:

- `/` — landing page with hero and product overview
- `/login` — staff sign-in
- `/dashboard` — protected clinic dashboard
- `/demo` — product demo page
- `/privacy` — privacy policy
- `/terms` — terms and conditions
- `/data-deletion` — data deletion workflow
- `/secret-admin-onboard` — admin onboarding flow

## Backend responsibilities

The backend is the operational core of the system. It handles:

- WhatsApp webhook verification and message processing
- conversation/booking state tracking
- clinic selection, slot validation, and token queue logic
- Supabase queries and mutation logic
- reminder jobs and operational automation
- webhook security and request validation

## Local development

### Backend

```bash
git clone https://github.com/shahmehul2005/clinic-service.git
cd clinic-service/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn agent:app --reload
```

### Frontend

```bash
cd clinic-service/frontend
npm install
npm run dev
```

## Required database setup

Before booking and queue flows work correctly, apply the required SQL migrations in your Supabase SQL editor.

Recommended order:

```sql
-- run these in order when setting up a new database
-- backend/database_migration.sql
-- backend/reliability_migration.sql
-- backend/reports_reviews_migration.sql
-- backend/advanced_settings_migration.sql
```

Additional operational scripts such as `cleanup_cron.sql` and `enable_rls.sql` are also included for maintenance and database security.

## Test commands

```bash
cd backend
pytest -q
```

The project includes focused tests for workflow logic, webhook handling, reliability constraints, and operational tools.

## Environment variables

Frontend:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

Backend:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_API_KEY`
- `META_ACCESS_TOKEN`
- `META_PHONE_NUMBER_ID`
- `META_VERIFY_TOKEN`
- `META_CLIENT_SECRET`
- `ADMIN_PIN`

Optional:

- `ENABLE_BACKGROUND_JOBS=0` to disable reminder polling in local/CI environments

## Notes

This repository contains both the operational backend and the customer-facing frontend, so local setup requires running both services together for the full clinic workflow experience.

---

Sanwariya Tech
