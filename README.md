# UFTB Boys Hostel Meal Exchange

A full-stack marketplace where UFTB Boys Hostel students can offer unused lunch or dinner meals and buyers can contact sellers directly on WhatsApp.

## Features

- JWT registration and login with bcrypt password hashing
- Student and protected meal-manager roles
- Manager-controlled meal membership; only active members can sell
- Public weekly payment board with manager-only paid/unpaid updates
- Once-per-meal daily lunch and dinner attendance
- Live remaining-member lists and seven-card manager dashboard
- Seven-day manager cycles with per-cycle payments and notices
- APScheduler daily cleanup plus manual cycle reset
- Bangladesh WhatsApp number validation (`8801XXXXXXXXX`)
- Today's lunch and dinner menus, notice, and available meal board
- Lunch/dinner meal publishing, owner-only sold/delete controls
- Pre-filled WhatsApp buyer messages
- In-app meal-provided popups plus optional mobile/browser push alerts
- Weekly skip option for members who do not want meals in the current cycle
- Automatic deletion of meal posts older than seven days
- PostgreSQL in production with automatic SQLite fallback locally
- Responsive navy/green interface with custom hostel-food artwork

## Project Structure

```text
backend/                 FastAPI + SQLAlchemy API
  app/routes/            Auth, meal, and menu routes
  app/utils/cleanup.py   Seven-day weekly-data cleanup
  alembic/               Production database migrations
  tests/                 API permission and cleanup tests
frontend/                React + Vite single-page app
  src/pages/             Marketplace, auth, sell, manager pages
  src/components/        Layout, meal cards, route protection
  src/api/               API and session helpers
```

## Local Setup

Requirements: Python 3.10+, Node.js 20+, and npm.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The default `DATABASE_URL` uses `sqlite:///./uftb_meals.db`, so PostgreSQL is not required locally. The API runs at `http://localhost:8000`; interactive docs are at `http://localhost:8000/docs`.

The app reads environment variables from the shell. To load `backend/.env` automatically before starting:

```bash
set -a
source .env
set +a
uvicorn app.main:app --reload
```

### Frontend

In another terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

### Manager Account

Set a private `MANAGER_REGISTRATION_CODE` in the backend environment. Choose **Meal manager** during registration and enter that code. Students do not need a code. Do not expose this value in the frontend environment.

## Environment Variables

Backend (`backend/.env`):

```env
DATABASE_URL=sqlite:///./uftb_meals.db
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://localhost:5173
MANAGER_REGISTRATION_CODE=replace-with-a-private-manager-code
VAPID_PUBLIC_KEY=<web-push-public-key>
VAPID_PRIVATE_KEY=<web-push-private-key>
VAPID_SUBJECT=mailto:admin@example.com
```

Frontend (`frontend/.env`):

```env
VITE_API_URL=http://localhost:8000
```

Generate strong secrets with `openssl rand -hex 32`.

### Mobile Push Notifications

Push alerts can notify a phone even when the website is closed, but each user must first sign in and tap **Enable alerts** in the header. Real mobile push requires HTTPS in production. On iPhone/iOS, Web Push normally works after the user installs the site to the home screen as a PWA.

Generate VAPID keys for Web Push:

```bash
cd backend
python scripts/generate_vapid_keys.py
```

Copy the generated keys into `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY`, set `VAPID_SUBJECT` to an admin email such as `mailto:admin@example.com`, then restart the backend.

## API

| Method | Path | Access |
| --- | --- | --- |
| POST | `/auth/register` | Public |
| POST | `/auth/login` | Public |
| GET | `/me` | Authenticated |
| POST | `/meals` | Authenticated |
| GET | `/meals` | Public |
| GET | `/meals/today` | Public |
| PATCH | `/meals/{id}/mark-sold` | Seller only |
| DELETE | `/meals/{id}` | Seller only |
| GET | `/menu/today` | Public |
| POST | `/manager/menu` | Meal manager only |
| POST | `/admin/cleanup-old-posts` | Meal manager only |
| GET/PATCH | `/members`, `/members/{user_id}` | Public / manager |
| GET/PATCH | `/payments`, `/payments/{user_id}` | Public / manager |
| POST | `/attendance/lunch`, `/attendance/dinner` | Meal member |
| GET | `/attendance/today` | Authenticated |
| GET | `/attendance/remaining` | Meal manager |
| GET | `/cycle` | Public |
| POST | `/manager/start-new-cycle` | Meal manager |
| GET | `/dashboard/stats` | Meal manager |
| GET | `/push/public-key` | Public |
| POST/DELETE | `/push/subscribe` | Authenticated |
| GET | `/me/week-status` | Authenticated |
| POST/DELETE | `/me/skip-week` | Meal member |

## Tests and Build

```bash
cd backend
python3 -m pytest -q

cd ../frontend
npm run build
```

## Deploy with Render + Neon

The fastest production setup is:

1. Push this project to GitHub.
2. Deploy the backend on Render with PostgreSQL.
3. Deploy the frontend on Vercel.
4. Put the Vercel frontend URL into the backend `CORS_ORIGINS`.

This repository includes:

- `render.yaml` for the Render backend and PostgreSQL database.
- `frontend/vercel.json` for React Router refresh support on Vercel.
- `frontend/.env.production.example` for the production API URL.

### 1. Create Neon PostgreSQL

1. Create a Neon project and open **Connect** in its dashboard.
2. Copy the pooled PostgreSQL connection string. It should start with `postgresql://` and include `sslmode=require`.
3. Keep this string private; it becomes the backend `DATABASE_URL`.

### 2. Deploy the FastAPI backend on Render

Create a **Web Service** from the repository with:

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Add these environment variables:

```env
DATABASE_URL=<your Neon pooled connection string>
SECRET_KEY=<a long random value>
ACCESS_TOKEN_EXPIRE_MINUTES=10080
MANAGER_REGISTRATION_CODE=<a private random value>
CORS_ORIGINS=https://your-frontend-name.onrender.com
VAPID_PUBLIC_KEY=<web-push-public-key>
VAPID_PRIVATE_KEY=<web-push-private-key>
VAPID_SUBJECT=mailto:admin@example.com
```

Deploy and copy the backend URL, such as `https://uftb-meals-api.onrender.com`.

Alternative: use the included `render.yaml` blueprint from Render. In Render, choose **Blueprint**, connect the GitHub repository, and select this repo. Render will create:

- `uftb-meals-api`
- `uftb-meals-db`

After the first blueprint deploy, open the backend service environment page and set:

```env
MANAGER_REGISTRATION_CODE=<a private random value>
CORS_ORIGINS=https://your-frontend-url.vercel.app
VAPID_PUBLIC_KEY=<optional web-push-public-key>
VAPID_PRIVATE_KEY=<optional web-push-private-key>
```

### 3. Deploy the Vite frontend on Vercel

Import the same repository into Vercel with:

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Add this build-time environment variable:

```env
VITE_API_URL=https://uftb-meals-api.onrender.com
```

`frontend/vercel.json` already rewrites React Router paths to `index.html`. After Vercel assigns the frontend URL, set backend `CORS_ORIGINS` to that exact URL and redeploy Render.

### Public User Link Checklist

Before sharing the website with students:

1. Visit the backend health URL: `https://your-api.onrender.com/health`.
2. Visit the frontend URL from Vercel.
3. Register the first manager using `MANAGER_REGISTRATION_CODE`.
4. In the manager dashboard, set today's menu and registration rules.
5. Ask members who want mobile reminders to sign in and tap **Enable alerts**.

### Docker

Both services include Dockerfiles:

```bash
docker build -t uftb-api backend
docker build -t uftb-web frontend
```

The backend image runs `alembic upgrade head` before starting Uvicorn. Supply production environment variables at container runtime.

## Cleanup Behavior

APScheduler runs every day at 3:00 AM Asia/Dhaka and removes meal listings, attendance, weekly notices, and weekly payment data older than seven days. User accounts, room numbers, and WhatsApp numbers remain. Starting a new weekly cycle also clears the current weekly records immediately and creates fresh unpaid payment entries for active members.

## Production Notes

- Replace all example secrets before deployment.
- Keep the manager registration code restricted to hostel administration.
- Use Neon's pooled connection string for normal web-service traffic.
- Run `alembic upgrade head` during every backend deployment.
