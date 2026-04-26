# UVA Food Rating (Flask + PyMySQL)

This is a raw-SQL Flask app for rating dishes, managing favorites, and following users. It supports returning users, multi-user shared database access, and role-based admin controls.

## Tech Stack

- Flask (server-rendered Jinja templates)
- Flask-Login (authentication and sessions)
- PyMySQL (raw SQL, no ORM)
- Google Cloud SQL Python Connector (optional, for Cloud SQL)
- MySQL
- Gunicorn (production server for Cloud Run/Procfile)

## Environment Variables

Create a `.env` file from `.env.example`:

- `FLASK_SECRET_KEY`
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `INSTANCE_CONNECTION_NAME` (optional; for Cloud SQL, format: `project:region:instance`)

Behavior:
- If `INSTANCE_CONNECTION_NAME` is set, the app connects through Cloud SQL Connector.
- Otherwise, it connects directly with `DB_HOST` + `DB_PORT`.

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env template:
   - PowerShell: `Copy-Item .env.example .env`
4. Fill `.env` with DB credentials and secret key.
5. Initialize schema (from repo root):
   - `mysql -h <host> -u <dev_admin> -p <db_name> -e "source db/schema.sql"`
6. Optional DB-level grants (after replacing placeholders in `db/security.sql`):
   - `mysql -h <host> -u <root_or_admin> -p -e "source db/security.sql"`
7. Start app:
   - `python run.py`
8. Open:
   - `http://127.0.0.1:8080`

Notes:
- Default app port is `8080` (`PORT` env var can override).
- Set `FLASK_DEBUG=1` for debug mode.

## Deploy (GCP Cloud Run)

- Container setup is already included via `Dockerfile`.
- Procfile command is also included for process-based hosts.
- Typical command:
  - `gcloud run deploy <service-name> --source . --region <region> --allow-unauthenticated --set-env-vars FLASK_SECRET_KEY=<secret>,DB_USER=<user>,DB_PASSWORD=<pass>,DB_NAME=<db>,INSTANCE_CONNECTION_NAME=<project:region:instance>`

## Implemented Features

- CRUD via app for:
  - users, dishes, locations, accommodations, ratings, rating tags/images, rating review votes, favorites, and follow relationships.
- Search/filter + sort on dishes page (dynamic table refresh).
- Following/follower social model and public user profile pages with user-specific activity.
- Security:
  - DB-level privileges (`db/security.sql`)
  - App-level auth, hashed passwords, login-required routes, admin guards, and ownership checks.

## Project Structure

- `run.py` - app entrypoint
- `app/` - Flask package (`auth`, `dishes`, `ratings`, `social`, `admin`)
- `app/db.py` - DB connection + query helpers + transaction wrapper
- `app/templates/` - Jinja templates
- `app/static/js/dishes.js` - dynamic filter/sort UI behavior
- `db/schema.sql` - tables, indexes, trigger
- `db/security.sql` - DB user/grant template
- `Dockerfile` and `Procfile` - production run config
