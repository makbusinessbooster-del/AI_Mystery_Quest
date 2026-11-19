# AI Mystery Quest — MAK Prime Edition

A Flask-based, browser-playable detective mystery game starter with fictional cases, Groq-powered case generation and Detective AI chat, guest play, accounts, XP, case history, admin tools, and invite-code multiplayer rooms.

## Important scope notes

- This is a functional first release / MVP foundation, not a finished commercial-scale game.
- Multiplayer currently supports account-based invite rooms, up to four players, room status polling, and score comparison. It is **not** yet synchronized real-time co-op gameplay or a complete global matchmaking system.
- Guest play is session-based; guest progress is not permanently stored.
- The answer checker uses case-specific keywords for this starter release. For production, replace it with structured accepted answers and stronger validation.
- Add your own original MAK Prime logo files to `static/images/` (see branding note below). The app uses a text-based fallback mark until you add the image.
- Cinematic sound effects are represented by UI feedback hooks; add licensed/original audio files before enabling music.

## 1. Requirements

- Python 3.10+
- VS Code
- Internet connection for installing packages and using Groq API
- Optional Groq API key from Groq Console

## 2. Windows PowerShell setup

Open this folder in VS Code, then Terminal → New Terminal.

```powershell
py -m venv .venv
```

If `py` is unavailable, try:

```powershell
python -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use this command for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Install packages:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env`. Set a long random `SECRET_KEY`, a strong `ADMIN_PASSWORD`, and optionally your `GROQ_API_KEY`.

Run:

```powershell
python app.py
```

Open http://127.0.0.1:5000

## 3. Demo Mode and Groq

Without `GROQ_API_KEY`, pre-built cases, hints, answer checking, accounts and room features work; Detective AI responds using a clearly labeled Demo fallback. AI case generation requires a valid Groq key.

Never put your API key in HTML or JavaScript. Keep it only in `.env`, which is ignored by Git.

The default model can change availability. If Groq reports that the model is unavailable, set `GROQ_MODEL` in `.env` to a model currently enabled for your Groq account.

## 4. Admin account

On first startup, the app creates an admin only if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set in `.env`. Registering a normal account does not grant admin access.

Open `/admin` after signing in with that configured account.

## 5. Multiplayer

Sign in (guest accounts cannot create rooms), open Multiplayer, create a room and share its six-character code. Friends register/sign in and join using the code. Up to four players can join. Room score data refreshes every few seconds.

## 6. PostgreSQL deployment

Set `DATABASE_URL` to a PostgreSQL connection string supplied by your host, for example:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

The app normalizes common `postgres://` URLs. For production:
- Set `SECRET_KEY` to a unique random value.
- Set `FLASK_DEBUG=0`.
- Set `GROQ_API_KEY` in the host's secret/environment settings.
- Set `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD` before first launch.
- Use HTTPS and a managed PostgreSQL database.
- Back up your database and add migrations (Alembic/Flask-Migrate) before schema changes.

A free host may sleep, restrict background activity, or change its free-tier terms. Choose a Python web host that supports Flask and persistent PostgreSQL. SQLite on ephemeral hosting may lose data after restart/redeploy; use PostgreSQL for a live public deployment.

## 7. MAK Prime branding

Place your approved original logo at `static/images/mak-prime-logo.png`. Keep its original design; do not recreate or substitute it. The site currently shows a typographic MAK PRIME mark if the image is absent.

## 8. Security before public launch

This starter includes password hashing, server-side API keys, login protection for admin and multiplayer, and basic input limits. Before a public launch, add CSRF protection, rate limiting, email verification/password reset, audit logs, stronger authorization tests, database migrations, secure cookie settings, moderation/reporting, and automated tests. Review all generated AI content before publishing it.

## 9. Main routes

- `/` — landing page
- `/register`, `/login`, `/guest` — access
- `/dashboard` — cases, XP and history
- `/case/<id>` — play a case
- `/leaderboard` — XP ranking
- `/multiplayer` — invite-code rooms (login required)
- `/admin` — admin case/user management

## 10. Project files

- `app.py` — routes and application setup
- `models.py` — database models
- `ai_service.py` — Groq integration and demo fallback
- `game_data.py` — starter cases
- `templates/` — pages
- `static/` — styles and browser scripts
