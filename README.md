# Campus Marketplace

A listing + discovery site for a closed community (a college / hostel) where members post items, browse & search, and contact sellers through a **Telegram redirect**. No payments, no in-app chat, no shipping, no escrow — every deal closes face-to-face, off-platform.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-4-38B2AC?logo=tailwindcss&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> Screenshots go in `docs/screenshots/` — add them after your first run (reviewers judge these first).

## Features

- **Browse, search & filter publicly** — no login needed to window-shop (full-text-ish search, category/price/condition filters, sorting, pagination)
- **Password-less login via Telegram** — the bot DMs a one-time 6-digit code to your account; no passwords or sensitive account access granted
- **Community trust layer** — the bot checks membership in your campus Telegram group; only verified members can list items or see the *Message Seller* button
- **Telegram contact redirect** — `t.me/<username>?text=…` with a prefilled message; deals close face-to-face
- **Safe image pipeline** — client-side compression, server-side re-encode, **EXIF/GPS stripping**, WebP output with size caps
- **Moderation** — prohibited-keyword blocklist at creation, per-listing reporting, admin queue, ban with instant session revocation
- **Anti-abuse** — per-route rate limiting, CSRF header check, locked-down CORS, anti-spam caps (10 active listings/user, 5/day)
- **Runs locally with zero external services** — SQLite + local disk storage + a dev login, all behind env flags

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19 + Vite 7 + Tailwind 4 |
| Backend | FastAPI (auto Swagger docs at `/docs`) |
| Database | SQLAlchemy — SQLite locally, PostgreSQL in prod via `DATABASE_URL` |
| Auth | Bot-delivered OTP code + community-group membership check, opaque session tokens in HttpOnly cookies |
| Images | Pillow (validate → strip EXIF → re-encode WebP); local disk or cloud storage |

## Quick start (working model, no Telegram needed)

Prereqs: Python 3.11+, Node 20+.

```bash
# 1. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload   # → http://localhost:8000  (docs at /docs)

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                     # → http://localhost:5173
```

Open http://localhost:5173, click **Log in → Continue as dev user** (dev mode), and list an item. The Vite dev server proxies API calls to the backend, so cookies just work.

> The default `.env` ships with `DEV_MODE=true` so you can try everything without a Telegram bot. **Set `DEV_MODE=false` before deploying.**

### Run the tests

```bash
cd backend
pytest tests -v    # 34 tests: auth/HMAC, listings, gating, admin, image pipeline
```

## Project layout

```
campus-marketplace/
├── frontend/            # React SPA (Vite + Tailwind)
│   └── src/{components,pages,context}/
├── backend/             # FastAPI app
│   ├── app/{routers,services}/  # auth, listings, uploads, admin
│   └── tests/           # pytest suite (34 tests)
├── docs/screenshots/    # UI screenshots for reviewers
├── .env.example         # every config knob, documented (no secrets)
├── docker-compose.yml   # optional one-command run
└── LICENSE              # MIT
```

## Configuration

Copy `.env.example` → `.env` and fill in. Key knobs:

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` | From `@BotFather` |
| `TELEGRAM_WEBHOOK_SECRET` | Shared secret for the webhook endpoint (setWebhook `secret_token`) |
| `COMMUNITY_GROUP_CHAT_ID` | Group the bot admins; empty = skip membership check (dev) |
| `DATABASE_URL` | `sqlite:///./campus_marketplace.db` locally; Postgres URL in prod |
| `FRONTEND_ORIGIN` | CORS-allowed origin (never `*`) |
| `DEV_MODE` | Enables the password-less dev login — **false in production** |
| `COMMUNITY_NAME` | Branding shown in the UI — keep it config, not hardcoded |

## Going to production (free tiers)

1. **Telegram**: create a bot via `@BotFather`, add it as admin to your community group, set `TELEGRAM_BOT_*` + `COMMUNITY_GROUP_CHAT_ID`. Then set the webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<BACKEND_URL>/telegram/webhook&secret_token=<YOUR_SECRET>"
   ```
   Add `TELEGRAM_WEBHOOK_SECRET=<YOUR_SECRET>` to your backend env vars.
2. **Backend** → Render free web service; **DB** → Neon or Supabase Postgres (set `DATABASE_URL`); **images** → Supabase Storage or Cloudinary.
3. **Frontend** → Vercel Hobby (non-commercial use), set `VITE_API_URL` to the backend URL.
4. **Edge** → put both domains behind Cloudflare free (DDoS mitigation, rate limiting, Turnstile on login + listing forms).
5. Set `DEV_MODE=false`, `SESSION_SECRET` to a long random string, and use HTTPS everywhere (cookies become `Secure; SameSite=None` cross-site).

## API overview

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/code/request` · `/auth/code/verify` | none | OTP login: request code → verify code → session issued |
| POST | `/auth/logout` · GET `/auth/me` | session | session lifecycle |
| GET | `/categories` · `/listings` · `/listings/{id}` | none | public browse/search/detail |
| POST | `/listings` · PUT `/listings/{id}` | verified member / owner | create / edit |
| POST | `/listings/{id}/mark-sold` · DELETE `/listings/{id}` | owner | lifecycle |
| POST | `/listings/{id}/report` | member | flag for moderation |
| POST | `/uploads/image` | verified member | validate + strip EXIF + re-encode |
| GET | `/admin/reports` · POST `/admin/listings/{id}/remove` · POST `/admin/users/{id}/ban` | admin | moderation |

Full interactive docs: run the backend and open **`http://localhost:8000/docs`**.

## Security notes (short version)

- No passwords anywhere → nothing to brute-force. Login is via a one-time 6-digit code that the bot DMs to your account; codes are HMAC-hashed, single-use, and expire in 10 minutes.
- Sessions are opaque tokens, stored **hashed** in the DB, delivered as `HttpOnly` cookies — revocation is deleting a row.
- Seller usernames never leave the server for anonymous visitors (contact is gated behind login).
- Photos are re-encoded from decoded pixels, which strips EXIF/GPS metadata by construction.
- Per-route rate limits (tighter on writes), CSRF custom-header check, CORS locked to one origin, Pydantic validation everywhere, ORM-only queries.

## License

[MIT](LICENSE) — use it as a template for your own campus.
