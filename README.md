# UVA Food Rating (Flask + PyMySQL)

This project is a raw-SQL Flask app for rating dishes, managing favorites/following, and supporting multi-user access with a shared MySQL database.

## Tech Stack

- Flask (server-rendered Jinja templates)
- PyMySQL (raw SQL, no ORM)
- Flask-Login (authentication/session management)
- MySQL (shared remote database)

## Quick Start

1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy environment template:
   - `copy .env.example .env` (Windows PowerShell: `Copy-Item .env.example .env`)
4. Fill `.env` with your shared MySQL credentials.
5. Initialize database schema:
   - `mysql -h <host> -u <dev_admin> -p <db_name> -e "source db/schema.sql"`
6. (Optional) Apply DB privilege script after replacing placeholders:
   - `mysql -h <host> -u <root_or_admin> -p -e "source db/security.sql"`
7. Run app:
   - `python run.py`
8. Open:
   - `http://127.0.0.1:5000`

## Implemented Requirements Mapping

- CRUD through the app for users, dishes, locations, accommodations, ratings, favorites, following relationships, rating tags/images, and rating reviews.
- Optional feature implemented: search/filter + sort on dish listing.
- Returning users supported via login/logout and persistent account data.
- Multi-user supported via shared remote MySQL access.
- Security:
  - DB-level permissions via `db/security.sql`.
  - App-level auth/authorization with hashed passwords and owner/admin checks.

## Project Structure

- `run.py`: app entrypoint
- `app/`: Flask app package
  - `auth`, `dishes`, `ratings`, `social`, `admin` blueprints
  - `db.py`: connection/query/transaction helpers
  - `templates/`: server-rendered UI
  - `static/js/dishes.js`: dynamic filter/sort table refresh
- `db/schema.sql`: canonical schema + trigger + indexes
- `db/security.sql`: DB-user grants for runtime and developers
