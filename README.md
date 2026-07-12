# Sanwariya Tech

![Sanwariya Tech Banner](https://via.placeholder.com/1200x400.png?text=Sanwariya+Tech+-+AI+WhatsApp+Automation)

Sanwariya Tech is a next-generation AI-powered automation and booking platform built for local businesses. It allows clinics, schools, coaching centers, and exporters to fully automate their customer inquiries and appointment scheduling 24/7 directly through the official Meta WhatsApp Business API.

## 🚀 Key Features

- **Conversational AI Agent**: A natural language processing bot (supporting English and Hinglish) that understands patient/client intent, answers FAQs, and handles bookings without human intervention.
- **Multilingual Support**: Fully translated user interface supporting English and Hindi (via `react-i18next`).
- **Real-Time Dashboard**: Instant sync between the WhatsApp bot and the receptionist's secure web dashboard.
- **Bulletproof Architecture**: Built on PostgreSQL with strict Row-Level Security (RLS) and unique constraints to guarantee zero double-bookings.
- **B2B SaaS Ready**: Fully equipped with "White-Glove Sandbox Trial" funnels, Meta-compliant legal pages (Privacy, Terms, Data Deletion), and domain-agnostic architecture.

## 🛠️ Technology Stack

### Frontend (Deployed on Vercel)
- **Framework**: React 19 + Vite
- **Routing**: React Router DOM (v7)
- **Styling**: Vanilla CSS with modern UI/UX design (Glassmorphism, custom CSS variables)
- **Internationalization**: `i18next` & `react-i18next`
- **Icons**: Lucide React

### Backend (Deployed on Render)
- **Framework**: FastAPI (Python)
- **Integration**: Meta WhatsApp Cloud API (Webhooks & Messaging)
- **Security**: HMAC SHA-256 Signature Validation for Webhooks

### Database & Auth (Supabase)
- **Database**: PostgreSQL
- **Authentication**: Supabase Auth (JWT)

## 📁 Project Structure

```
clinic/
├── backend/               # FastAPI Python application
│   ├── main.py            # API routes and WhatsApp webhook handlers
│   └── requirements.txt   # Python dependencies
└── frontend/              # React application
    ├── src/
    │   ├── components/    # Reusable UI components (Navbar, Hero, Features, etc.)
    │   ├── context/       # React Context providers (AuthContext)
    │   ├── locales/       # i18n translation dictionaries (en.json, hi.json)
    │   └── pages/         # Route pages (Home, Demo, Login, Legal docs)
    ├── index.html
    └── package.json
```

## ⚙️ Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/shahmehul2005/clinic-service.git
cd clinic-service
```

### 2. Setup the Frontend
```bash
cd frontend
npm install
npm run dev
```
The frontend will run at `http://localhost:5173`.

### 3. Setup the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
The backend will run at `http://localhost:8000`.

### 4. Environment Variables
You will need to set up the following environment variables across your `.env` files for Supabase and the Meta API:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `WHATSAPP_API_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WEBHOOK_VERIFY_TOKEN`

## 📄 License & Legal
This project belongs to **Sanwariya Tech**. All rights reserved.
For data deletion or support inquiries, please contact `support@sanwariyatech.dev`.
