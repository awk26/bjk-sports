# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BJK Athletes — a Flask app for managing athletes, coaches, and admins in a sports academy. Four roles: `superadmin` (hardcoded credentials, not in DB) → `admin` → `coach` → `athlete`, each with its own blueprint, dashboard, and template set.

## Running the app

```
pip install -r requirements.txt
python main.py          # runs on http://0.0.0.0:5003
```

Requires a `.env` file (not committed) with MySQL connection info and API keys:
`HOST_JIA`, `USER_JIA`, `PASSWORD_JIA`, `PORT_JIA`, `DB_NAME_JIA`, `GOOGLE_API_KEYS`, `SESSION_COOKIE_SECURE`, `PORTALL_API_KEY_UPLOAD`, `PORTALL_API_KEY_EXTRACT`.

Database: MySQL/MariaDB. `schema.sql` has the base schema (users, coaches, athletes, password_reset_tokens, audit_log) plus stored-procedure definitions the app calls. `common/extended_schema.sql` documents later column/table additions (athlete/coach profile fields, `events` table) — most of it is applied automatically at startup by `models.ensure_schema_extensions()`, which runs idempotent `ALTER TABLE`/`CREATE TABLE IF NOT EXISTS` statements rather than requiring a manual migration step.

## Tests

```
pytest tests/
```

**Known issue:** everything under `tests/` (and `main_test.py`) predates the move to a MySQL-backed model layer — it imports from a `bjk_athletes` package with in-memory `USERS`/`COACHES`/`ATHLETES` dicts and `init_default_users()`, none of which exist anymore (the real code is `common/models.py`, DB-backed via stored procedures, with `init_default_data()`). These tests will not currently collect/run against the current codebase. Don't assume they pass or use them as a reference for current architecture; if asked to add tests, they'll need to be rewritten against `common/models.py` and the real `main.py`/`create_app()`, likely mocking `common.database.Database`.

## Architecture

**App factory + blueprints.** `main.py:create_app()` wires up `Config`, `CSRFProtect`, security headers/CSP (with a per-request nonce for inline scripts), no-cache headers for authenticated paths, and registers one blueprint per role/area: `routes/auth.py` (login, logout, password reset — no prefix), `routes/admin.py` (`role_required("admin")`, no prefix), `routes/coach.py` (`role_required("coach")`, no prefix), `routes/superadmin.py`, `routes/athlete.py` (`/athlete` prefix, `role_required("athlete")`), `routes/events.py` (`/events` prefix). The shared `/dashboard` route in `main.py` branches on `session["user"]["role"]` to pick which dashboard stats to load and which panel of `dashboard.html` to render.

**All data access goes through `common/models.py`.** Routes never touch SQL or `common/database.py` directly — they call functions in `models.py`, which call `db.call_proc("sp_...", args)` (a thin wrapper in `common/database.py` over a pooled `pymysql` connection). Stored procedures follow a `sp_<entity>_<action>` naming convention (`sp_athlete_list`, `sp_coach_create`, `sp_analytics_athlete_kpis`, etc.) and live in the MySQL database itself, not in this repo as executable code — `schema.sql`/`extended_schema.sql` are the closest thing to their source of truth here. `Database.call_proc()` returns `{"rows": [...], "out_params": {...}}`; OUT params come back as `p0, p1, ...` by positional index, with the create-style procedures' generated ID as the last one.

**Auth/session model.** `session["user"]` is a plain dict (`username`, `role`, `name`, plus `coach_id` or `athlete_id` when applicable) — there's no Flask-Login or user-loader; `common/decorators.py` provides `login_required` and `role_required(*roles)` which check `session` directly. Superadmin is a special case: it's never a row in `users`, just credentials checked against `Config.SUPERADMIN_USERNAME`/`SUPERADMIN_PASSWORD` (env-overridable) in `verify_superadmin()`.

**Optional external integrations, both designed to degrade gracefully:**
- `common/gemini_recommendations.py` — generates coaching-recommendation text via Gemini (`GOOGLE_API_KEYS`, `google-genai` package) for the athlete analytics dashboard, in-memory cached per athlete's rating fingerprint. Falls back to rule-based recommendations in `models.py` if the key/package/API call isn't available.
- `common/portall_client.py` — uploads a scanned/PDF/Excel assessment form to the Portall extraction API and polls for parsed field data to pre-fill the coach's assessment form (`routes/coach.py`). Raises `PortallError` with a coach-safe message on any failure; never affects assessment data directly.

**Name/phone conventions.** There's a single `name` column per person (no separate first/middle/last), and phone numbers are stored pre-formatted with a `+91` prefix. `combine_name`/`split_name` and `format_phone_in`/`strip_phone_prefix` in `models.py` convert between the stored single string and the split fields shown in the add/edit forms — this is presentation-only, not a schema change.

**Security hardening already in place (don't regress it):** CSP with a per-request nonce (`g.csp_nonce`, injected as `csp_nonce()` in templates — any new inline `<script>`/`<style>` needs `nonce="{{ csp_nonce() }}"`), `no-store` cache headers on `/login`, `/dashboard`, `/coach/`, `/admin/`, `/superadmin/`, `/events/`, CSRF via `Flask-WTF`, `SESSION_COOKIE_HTTPONLY`/`SAMESITE=Lax`. These exist because of a prior VAPT (vulnerability assessment) pass — see recent commit `07a17b9 resolve vapt`.
