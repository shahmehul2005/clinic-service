# Frontend — Clinic Service

This directory contains the React + Vite frontend for the clinic-service application.

## What is included

- Marketing landing page and product messaging
- Staff login flow
- Protected dashboard for clinic operations
- Demo, privacy, terms, and deletion request pages
- Admin onboarding route
- i18n support for English and Hindi

## Tech stack

- React 19
- Vite
- React Router
- Supabase JS client
- i18next
- Lucide icons

## Local setup

```bash
cd frontend
npm install
npm run dev
```

## Production build

```bash
cd frontend
npm run build
```

## App routes

- `/`
- `/login`
- `/dashboard`
- `/demo`
- `/privacy`
- `/terms`
- `/data-deletion`
- `/secret-admin-onboard`

The frontend depends on backend APIs and Supabase configuration values passed through environment variables.

---

This frontend is part of the wider Clinic Service platform. See the repository root README for full setup and backend configuration.

