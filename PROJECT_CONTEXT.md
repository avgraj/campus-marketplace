# Campus Marketplace — Full Project Context

> Feed this file to any AI coding assistant to give it complete context about
> this project: what's built, what's decided, what's running, and why.

---

## 1. One-line pitch

A listing + discovery site for a closed campus community: members post items,
browse/search, and contact sellers via a **Telegram DM redirect** (the bot
delivers a one-time login code). No payments, no in-app chat, no shipping,
no escrow — every deal closes face-to-face.

---

## 2. Stack

| Layer | Choice | Hosted on | Notes |
|---|---|---|---|
| Frontend | React 19 + Vite 7 + Tailwind 4 | **Vercel** → https://campus-marketplace-ochre.vercel.app | `frontend/` dir |
| Backend | Python 3.13 + FastAPI + SQLAlchemy 2.0 | **Render** → https://campus-marketplace-zrw9.onrender.com | `backend/` dir |
| Database | PostgreSQL 18 (Neon, Singapore region) | `neondb_owner` → `postgresql://neondb_owner:npg_wbdvCEy76kaX@ep-wandering-dawn-azmambgr.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require` | Tables: users, categories, listings, listing_images, reports, sessions, login_codes |
| Image storage | Local disk (ephemeral on Render) | Renders from `backend/uploads/` served via FastAPI StaticFiles | **Will not survive redeploys** — Cloudinary/Supabase Storage needed for real use |
| Auth | Bot-delivered OTP code | 6-digit code, HMAC-stored, single-use, 10-min expiry | Custom — **not** Telegram OAuth widget |
| Bot | `@cmpmarketplace_bot` | Webhook set to backend `/telegram/webhook` | Token: `8853918977:AAELGqaa1Q2e1nOsOLcw859jdFIVEz2Anmc` (needs **revocation after this session**) |
| Edge | None yet | Plan §11 recommends Cloudflare free plan + Turnstile | Not implemented |
| Tests | pytest | 37 tests, run from `backend/` | `pytest tests -v` |

---

## 3. Repo root files

```
campus-marketplace/
├── backend/                     # FastAPI app
│   ├── app/
│   │   ├── config.py            # Settings via pydantic-settings (reads .env + env vars)
│   │   ├── database.py          # SQLAlchemy engine, session, Base
│   │   ├── models.py            # ORM: User, Category, Listing, ListingImage, Report, Session, LoginCode
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── security.py          # OTP code generation/hashing, session tokens
│   │   ├── deps.py              # Auth dependencies (get_current_user, verified_member, admin, csrf_check)
│   │   ├── rate_limit.py        # slowapi Limiter + per-route constants
│   │   ├── seed.py              # 10 seed categories (data, not hardcoded strings)
│   │   ├── main.py              # FastAPI app factory (lifespan, CORS, routers, /health, /config/public)
│   │   ├── routers/
│   │   │   ├── auth.py          # POST /auth/code/request, /code/verify, /dev-login, /logout, /me, /session-check
│   │   │   ├── categories.py    # GET /categories
│   │   │   ├── listings.py      # Full CRUD + search/filter/sort/paginate + report
│   │   │   ├── uploads.py       # POST /uploads/image (Pillow pipeline)
│   │   │   ├── admin.py         # GET /admin/reports, POST /admin/reports/{id}/dismiss, /admin/listings/{id}/remove, /admin/users/{id}/ban
│   │   │   └── telegram_webhook.py  # POST /telegram/webhook — registers users on /start
│   │   └── services/
│   │       ├── images.py        # Pillow: verify→thumbnail→strip EXIF→WebP ≤300KB
│   │       └── telegram.py      # Bot API: send_message, send_login_code, check_community_membership
│   ├── tests/
│   │   ├── conftest.py          # Fixtures, helpers (dev_login, create_listing, webhook_start, etc.)
│   │   ├── test_auth.py         # OTP flow (webhook→request→verify), dev login, session lifecycle
│   │   ├── test_listings.py     # CRUD, search/filters, gating, caps, report, CSRF
│   │   ├── test_admin.py        # Moderation queue, remove, ban, dismiss
│   │   └── test_images.py       # Image pipeline, EXIF stripping, validation
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                     #  Local dev — GITIGNORED. Current values:
│                                #   DEV_MODE=true, COMMUNITY_NAME=BIT MESRA,
│                                #   FRONTEND_ORIGIN=http://localhost:5173
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx             # Entry point
│   │   ├── App.jsx              # Routes + layout (Navbar, Footer, AuthProvider)
│   │   ├── api.js               # Fetch wrapper (credentials:"include", X-Requested-With header)
│   │   ├── format.js            # formatPrice (₹), formatDate, CONDITION_LABELS
│   │   ├── context/
│   │   │   └── AuthContext.jsx  # user, config, requestCode, verifyCode, devLogin, logout
│   │   ├── components/
│   │   │   ├── Navbar.jsx       # Sticky top nav + user menu
│   │   │   ├── Footer.jsx       # Meetup safety + ToS (plan §12)
│   │   │   ├── ProtectedRoute.jsx  # Login gate / verified gate / admin gate
│   │   │   ├── EmptyState.jsx   # Fallback for no-data, errors
│   │   │   ├── ListingCard.jsx  # Cover image, title, price, condition badge
│   │   │   ├── ListingGrid.jsx  # Responsive grid (2–4 columns)
│   │   │   ├── FilterBar.jsx    # Search + category/condition/price/sort dropdowns
│   │   │   ├── ImageUploader.jsx    # Client-side compress → server validate (plan §7)
│   │   │   └── SafetyNote.jsx   # Amber-200 box, visible on listing detail
│   │   └── pages/
│   │       ├── Home.jsx         # Browse with filters + pagination
│   │       ├── ListingDetail.jsx    # Gallery, detail, Telegram redirect, owner controls, report
│   │       ├── Sell.jsx         # Create/edit form with ImageUploader
│   │       ├── MyListings.jsx   # Owner's listing grid
│   │       ├── Login.jsx        # Two-step OTP: username→code + dev login box
│   │       └── Admin.jsx        # Moderation queue list
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js           # React + Tailwind plugins, Vite proxy to :8000
│   ├── Dockerfile               # Nginx multi-stage build
│   └── nginx.conf               # SPA fallback + API proxy
│
├── docs/screenshots/            # Drop UI screenshots here (plan §14)
├── .env.example                 # All config knobs documented
├── .gitignore                   # .env, .venv, node_modules, __pycache__, *.db, uploads/
├── docker-compose.yml           # Optional: backend + frontend
├── PROJECT_CONTEXT.md           # ← you are here
├── LICENSE                      # MIT
└── README.md                    # In-depth setup, production guide
```

---

## 4. Auth flow (the most important thing to understand)

**There are TWO auth paths. DO NOT confuse them.**

### A) PRODUCTION PATH — Bot-delivered OTP (plan deviation)

**Why this exists:** Users were uncomfortable with the Telegram OAuth widget
("give access to my account" consent popup). We replaced it with a bot-DM
code flow.

**Full flow:**
1. **First time only:** User opens `@cmpmarketplace_bot` in Telegram and
   presses **Start** (one tap). The bot sends no code yet — just a
   "You're registered" confirmation. Our webhook stores their
   `username → telegram_id` mapping (bots can't resolve usernames to IDs
   otherwise; this is the only way).
2. **Every login (on the site):**
   a. User types their Telegram @username on the login page and clicks
      "Send code via Telegram".
   b. Backend looks up the user by lowercased username. If not found
      → "open the bot and press Start".
   c. Backend generates a 6-digit code (secrets.randbelow(900000)+100000),
      HMAC-hashes it with SESSION_SECRET, stores it in `login_codes` table
      with 10-min expiry.
   d. Backend calls `sendMessage` via Bot API → code arrives as a DM
      from the bot. If the bot can't DM (user hasn't pressed Start) → same
      message.
   e. User enters the 6-digit code → backend verifies HMAC, checks expiry
      and attempt count (max 5 per code). On success: burns the code (all
      codes for that user), checks `getChatMember` on the community group
      → sets `is_verified_member`, issues HttpOnly session cookie.
3. **Rate limits (slowapi):** 10 requests/min on both request and verify.
   Code request also creates at most 1 active code per user — requesting
   a new one deletes the old.

**Database table:** `login_codes` (id, telegram_id, code_hash, attempts,
created_at, expires_at). Code_hash is HMAC-SHA256 of the 6-digit string.

**Important constraint:** Telegram bots CANNOT DM a user who hasn't pressed
Start, and CANNOT look up a user by phone number or resolve a username to
an ID without the user interacting first. This is a Telegram platform rule,
not a bug. The webhook `/start` registration is the unavoidable workaround.

### B) DEV PATH — Dev login (DEVELOPMENT ONLY)

Gated behind `DEV_MODE=true` env var. On the login page, a "Dev mode" box
appears. Username + optional admin flag →
`POST /auth/dev-login` creates/via pseudo telegram_id (negative hash),
always sets `is_verified_member=true`, if as_admin=true → `is_admin=true`.
No Telegram interaction needed.

**This must NEVER be enabled in production.** The hosted site has
`DEV_MODE=false` and the dev login box is hidden.

---

## 5. Database schema (7 tables)

See `backend/app/models.py` for the full SQLAlchemy definition.

```
users:       id, telegram_id (BIGINT unique), telegram_username (nullable),
             first_name, last_name, photo_url, is_verified_member, is_admin,
             is_banned, created_at, last_login_at

categories:  id, name, slug (unique)
             10 seeded rows — data, not hardcoded (plan §6)

listings:    id, seller_id FK→users, category_id FK→categories,
             title(120), description, price(NUMERIC 10,2), is_negotiable,
             condition CHECK(new|like_new|used|for_parts), 
             status CHECK(active|sold|expired|removed),
             created_at, updated_at, expires_at(14 days default)

listing_images:  id, listing_id FK→listings CASCADE, url, position

reports:     id, listing_id FK→listings, reported_by FK→users, reason,
             status CHECK(pending|reviewed|dismissed), created_at

sessions:    id (SHA-256 hash of opaque token — raw token stored only in
             browser HttpOnly cookie), user_id FK→users, ip_address,
             user_agent, created_at, expires_at(30 days)

login_codes: id, telegram_id(BIGINT indexed), code_hash, attempts,
             created_at, expires_at(10 min)
```

**Key deviation from the original plan:** The plan's `search_vector TSVECTOR`
column is omitted. We use portable `ILIKE` search (works on SQLite +
Postgres). Swap it in when scaling past ~10k listings.

---

## 6. API endpoints

| Method | Path | Auth | Rate limit | Notes |
|---|---|---|---|---|
| POST | `/auth/code/request` | None | 10/min | Body: `{username}`. DM's 6-digit code. |
| POST | `/auth/code/verify` | None | 10/min | Body: `{username, code}`. Issues session cookie. |
| POST | `/auth/dev-login` | DEV_MODE | — | Dev only. |
| POST | `/auth/logout` | Session | — | Clears cookie + deletes session row. |
| GET | `/auth/me` | Session | — | Returns current user or 401. |
| GET | `/auth/session-check` | None | — | `{logged_in: bool}` — no 401, SPA uses this. |
| GET | `/categories` | None | — | 10 categories sorted by name. |
| GET | `/listings` | None | 120/min | Query params: q, category, min_price, max_price, condition, sort(newest|price_asc|price_desc), page, page_size(≤50). Only active + not expired. |
| GET | `/listings/mine` | Session | — | Owner's listings except removed. |
| GET | `/listings/{id}` | None | — | Public detail — seller username hidden for anonymous. is_mine if requester is owner. Owner sees sold. |
| POST | `/listings` | Verified | 10/min | CSRF. Body: title(5-120), description(20-1000), price(>0), category_id, condition, is_negotiable, image_urls[1-5]. Username required. Keyword blocklist. Anti-spam caps (10 active, 5/day). |
| PUT | `/listings/{id}` | Owner | 10/min | CSRF. Partial update. Re-checks keyword blocklist. Replaces images if provided. |
| POST | `/listings/{id}/mark-sold` | Owner | — | CSRF. Sets status → sold. |
| DELETE | `/listings/{id}` | Owner or admin | — | CSRF. Soft delete → removed. |
| POST | `/listings/{id}/report` | Session | 10/min | CSRF. Body: `{reason}`. Creates pending report. |
| POST | `/uploads/image` | Verified | 20/min | CSRF. Multipart file. Returns `{url}`. 5MB raw cap. Pillow pipeline. |
| POST | `/telegram/webhook` | Secret header | — | Telegram sends updates here. Only processes /start messages. Returns 200 quickly. |
| GET | `/admin/reports` | Admin | — | CSRF. Pending reports with listing + reporter. |
| POST | `/admin/reports/{id}/dismiss` | Admin | — | CSRF. Sets status → dismissed. |
| POST | `/admin/listings/{id}/remove` | Admin | — | CSRF. Sets listing → removed, its pending reports → reviewed. |
| POST | `/admin/users/{id}/ban` | Admin | — | CSRF. Bans user, destroys all sessions. Cannot ban self. |
| GET | `/health` | None | — | `{"status":"ok"}` |
| GET | `/config/public` | None | — | `{community_name, telegram_bot_username, dev_mode, frontend_origin}` |

---

## 7. Config (env vars)

| Key | Default | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `""` | Bot token from @BotFather |
| `TELEGRAM_BOT_USERNAME` | `""` | Bot @username (no @) |
| `TELEGRAM_WEBHOOK_SECRET` | `""` | Shared secret for webhook endpoint — set in Render, used in setWebhook |
| `COMMUNITY_GROUP_CHAT_ID` | `""` | Group where bot is admin; empty → skip membership check (dev) |
| `DATABASE_URL` | `sqlite:///./campus_marketplace.db` | SQLite locally, Postgres in production |
| `SESSION_SECRET` | `change-me-to...` | Used for HMAC of session tokens AND OTP codes |
| `UPLOAD_DIR` | `uploads` | Local disk path for processed images |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS allow_origin |
| `DEV_MODE` | `false` | Enables dev-login endpoint — **never true in production** |
| `COMMUNITY_NAME` | `"My Campus"` | Branding in UI + bot messages |
| `COOKIE_SECURE` | `false` | True in production (HTTPS → SameSite=None) |
| `RATE_LIMIT_ENABLED` | `true` | Disable in tests |
| `LISTING_TTL_DAYS` | `14` | Auto-expire inactive listings |
| `MAX_ACTIVE_LISTINGS_PER_USER` | `10` | Anti-spam cap |
| `MAX_LISTINGS_PER_DAY` | `5` | Anti-spam cap |
| `MAX_IMAGES_PER_LISTING` | `5` | Enforced at listing creation |
| `MAX_UPLOAD_BYTES` | `5MB` | Raw upload cap |
| `MAX_IMAGE_DIMENSION` | `1600px` | Downsize to this max side |
| `TARGET_IMAGE_BYTES` | `300KB` | Re-encode until ≤ this size |
| `LOGIN_CODE_TTL_MINUTES` | `10` | OTP expiry |
| `LOGIN_CODE_MAX_ATTEMPTS` | `5` | Before code is burned |

---

## 8. Key design decisions and plan deviations

| Plan says | What we built | Why |
|---|---|---|
| Telegram Login Widget (OAuth) | Bot-DM OTP (username + 6-digit code) | Users were uncomfortable with "grant access" consent screen |
| `/auth/telegram/callback` HMAC endpoint | `/auth/code/request` + `/auth/code/verify` | Replaced with OTP flow |
| `/setdomain` in BotFather | Webhook URL + secret_token | Widget needed domain whitelist; OTP uses webhook instead |
| `search_vector TSVECTOR` | Portable ILIKE search | Works on SQLite + Postgres; swap at scale |
| Cloudflare / Turnstile | Not implemented | Recommended but not built (plan §11) |
| Image storage via Supabase/Cloudinary | Local disk (`uploads/`) | Working model → ephemeral on Render redeploy. Fix with Cloudinary. |
| Postgres in production only | Postgres on Neon in production already | Deployed in Singapore region |
| Admin ban includes session grid? | Ban destroys all sessions | Minor improvement for immediate effect |
| Optional *contact_clicks counter* (§8) | Not implemented | Keep scope minimal |

---

## 9. Image pipeline (plan §7)

Sequential steps when `POST /uploads/image` is called:
1. **Client-side** (in the browser before upload): `browser-image-compression`
   reduces to max 1MB and max 1600px.
2. **Server-side** receipts raw bytes; rejects if > 5MB.
3. `PIL.Image.open()` + `.verify()` to confirm it's really an image.
4. Re-open the file (verify leaves it unusable).
5. Convert to RGB if not already.
6. `.thumbnail((1600, 1600))` — preserves aspect ratio.
7. **EXIF is STRIPPED by design.** Thumbnailing + re-encoding from decoded
   pixels discards all metadata (GPS coordinates, camera model, etc.).
   This is not optional (plan §7).
8. Quality-loop: saves as WebP at quality 80, 70, 60, 50, 40; stops when
   file ≤ 300KB. Fallback to JPEG if WebP unavailable.
9. Random hex filename, saved to `UPLOAD_DIR/` (gitignored).
10. Server returns `/uploads/<hash>.webp`.

---

## 10. Security model (per plan §11, adapted for OTP)

- **No passwords.** Codes are 6-digit, single-use, 10-min expiry,
  HMAC-stored.
- **Bot DM** proves control of the Telegram account. The webhook /start
  registration is the minimum necessary step.
- **Community gate:** after code verify, `getChatMember` checks the user is
  in the group. Gating is server-side — cannot be bypassed from the frontend.
- **Session tokens:** opaque random (32 bytes url-safe), stored as SHA-256 in
  the sessions table. Delivered only as HttpOnly cookies. Revocation =
  DELETE row. No JWT to invalidate.
- **CORS:** single origin, locked to FRONTEND_ORIGIN. Never `*`.
- **CSRF:** all mutations require `X-Requested-With: fetch` header (browsers
  refuse to send this cross-origin without a CORS preflight we'd reject).
- **Rate limiting:** slowapi — tighter on writes (10/min) than reads (120/min).
- **Keyword blocklist:** weapons, drugs, counterfeit, etc. — enforced at
  listing creation with clear rejection message.
- **Webhook secret:** Telegram posts updates to `/telegram/webhook` with a
  `X-Telegram-Bot-Api-Secret-Token` header that matches our env var.
  Protects against spoofed updates.

**Current credentials in the clear (must rotate after this session):**
- Bot token: `8853918977:AAELGqaa1Q2e1nOsOLcw859jdFIVEz2Anmc`
- DB password: `npg_wbdvCEy76kaX`
Rotation: @BotFather → /revoke → new token; Neon → Roles → reset password.
Then update both on Render.

---

## 11. Deployment state (current, live)

- **Backend:** Render web service (free, Singapore)
  - URL: https://campus-marketplace-zrw9.onrender.com
  - Env vars set: DATABASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME,
    COMMUNITY_GROUP_CHAT_ID (-5491848137), FRONTEND_ORIGIN, COOKIE_SECURE,
    DEV_MODE=false, COMMUNITY_NAME="BIT MESRA", SESSION_SECRET, webhook secret
  - ⚠️ TELEGRAM_WEBHOOK_SECRET env var may still need to be added on Render
- **Frontend:** Vercel (imported from GitHub, root frontend/)
  - URL: https://campus-marketplace-ochre.vercel.app
  - Env vars: VITE_API_URL=https://campus-marketplace-zrw9.onrender.com
- **Database:** Neon Postgres (Singapore, free tier)
  - `postgresql://neondb_owner:npg_wbdvCEy76kaX@ep-wandering-dawn-azmambgr.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
- **GitHub:** https://github.com/avgraj/campus-marketplace (private/public?)

---

## 12. Quick start (local development)

```bash
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload   # :8000, /docs has Swagger

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # :5173, proxies API to :8000
```

Open http://localhost:5173 → Log in (dev mode box at bottom) → Sell.

---

## 13. Testing

```bash
cd backend
.\.venv\Scripts\activate
pytest tests -v   # 37 tests
```

Tests use: isolated SQLite DB, temp upload dir, rate limiting disabled,
DEV_MODE=true, webhook secret set. No external services needed.

The `test_otp_full_flow` test monkeypatches `send_login_code` to capture
the generated code instead of actually sending it via Telegram. This is
the pattern for testing the OTP auth path.

---

## 14. Things to finish / known issues

1. **Webhook secret on Render** — Add `TELEGRAM_WEBHOOK_SECRET` env var.
2. **Rotate credentials** — New bot token + new DB password after this session.
3. **Persistent image storage** — Render's disk is wiped on redeploy.
   Wire Cloudinary or Supabase Storage (`services/images.py` is the only file
   that needs to change — it returns a URL).
4. **Cloudflare + Turnstile** — Plan §11 recommends it (free DDoS + bot
   filtering on login & sell forms). Needs widget code + server verify.
5. **Backups** — Weekly `pg_dump` via GitHub Actions (Neon free tier has no
   auto-backups).
6. **Postgres `tsvector`** — Replace ILIKE search with full-text when
   listings exceed ~10k.
7. **OG tags** — `ListingDetail.jsx` sets them client-side via
   `useEffect`. Server-side rendering (SSR) would be better for share links
   in WhatsApp/Telegram — but SSG/SSR is a big lift. Fine for now.
8. **Screenshots** — Drop UI screenshots into `docs/screenshots/` and
   link them near the top of `README.md`.

---

## 15. Commands reference (CI / one-off)

```bash
# Set Telegram webhook (run once)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<RENDER_URL>/telegram/webhook&secret_token=<SECRET>"

# Check webhook status
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Test the backend is alive
curl https://campus-marketplace-zrw9.onrender.com/health

# Check bot config
curl https://campus-marketplace-zrw9.onrender.com/config/public

# Make a user admin (run from repo root, adjust telegram_id)
cd backend
.\.venv\Scripts\activate
python -c "
from app.database import SessionLocal
from app.models import User
from sqlalchemy import select
db = SessionLocal()
user = db.scalar(select(User).where(User.telegram_id == <TELEGRAM_ID>))
if user: user.is_admin = True; db.commit(); print('done')
"
```

---

## 16. Original plan document

The full technical plan is at:
`C:\Users\rajde\OneDrive\Desktop\plan\plan.md`

This project follows that plan except for the OTP auth change (documented
above in §8). All plan sections §1–§16 are implemented or deferred as
noted.
