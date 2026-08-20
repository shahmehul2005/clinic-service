# Clinic Service (Sanwariya Tech)

WhatsApp-first appointment system for clinics. Patients book, cancel, or take a walk-in token on WhatsApp. Reception sees the same queue on a web dashboard..

Live site: [clinic-service-tawny.vercel.app](https://clinic-service-tawny.vercel.app)

## What it does

- **Scripted WhatsApp receptionist** (English or Hindi): language → clinic → name → timed slot **or** token. Replies are templates. Groq is used only to parse messy phrasing into JSON when regex/keywords miss. The model never confirms a booking.
- **Two clinic modes**: scheduled 10-minute (configurable) slots, or same-day token queues with Call Next + WhatsApp notify.
- **No double-books at the database**: canonical `slot_start` unique index and `SELECT FOR UPDATE` token numbers (see `backend/reliability_migration.sql`).
- **Reception dashboard**: React + Supabase realtime. Auth-gated. Status updates send WhatsApp templates.
- **Ops**: HMAC webhook verify, `wamid` idempotency, persisted workflow state, 2-hour appointment reminders, monthly Groq usage cap.

## Stack

| Layer | Tech |
| --- | --- |
| WhatsApp | Meta Cloud API (webhooks + messages) |
| Backend | FastAPI on Render (`agent:app`) |
| LLM | Groq (`llama-3.3-70b-versatile`, fallback `llama-3.1-8b-instant`) as a JSON parser only |
| DB / Auth | Supabase Postgres + Auth (JWT). Optional RLS in `enable_rls.sql` for dashboard tenancy — slot integrity is the unique index, not RLS. |
| Frontend | React 19, Vite, React Router 7, i18next (EN/HI), Vercel |

## Repo layout

```
clinic-service/
├── backend/
│   ├── agent.py                    # FastAPI, webhooks, tools
│   ├── workflow.py                 # Rule-first booking state machine
│   ├── ops.py                      # Slot helpers, RPC wrappers
│   ├── reliability_migration.sql   # Atomic slots/tokens, reminders, wamid, chat
│   └── test_*.py
└── frontend/                       # Marketing site + dashboard
```

## Local setup

```bash
git clone https://github.com/shahmehul2005/clinic-service.git
cd clinic-service
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
uvicorn agent:app --reload
```

**Required:** run `backend/reliability_migration.sql` in the Supabase SQL editor before booking works.

```bash
cd backend
python -m pytest test_ops.py test_agent_tactics.py test_whatsapp_webhook.py test_reliability.py test_workflow.py -q
```

CI runs the same tests on push (`.github/workflows/backend-tests.yml`).

## Environment

Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`

Backend: `SUPABASE_URL`, `SUPABASE_KEY` (service role), `GROQ_API_KEY`, `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_VERIFY_TOKEN`, `META_CLIENT_SECRET`, `ADMIN_PIN`

Set `ENABLE_BACKGROUND_JOBS=0` to disable the reminder poller (CI does this).

## License

Sanwariya Tech. All rights reserved. Data deletion / support: `support@sanwariyatech.dev`
