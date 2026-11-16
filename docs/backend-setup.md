# HelpBridge backend setup

This Django monolith is the Track 3 assistant backend. It is a plugin service for existing LMS and job platforms, not a standalone LMS.

## Requirements

- Python 3.11+ (3.13 is supported)
- Django 5.2
- PostgreSQL 17 for shared/production development
- Optional: Docker Compose

## Local SQLite (fast demo)

SQLite is allowed only when `DJANGO_ENV` is not `production` and `DATABASE_URL` is unset.

```bash
cd HelpBridge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python backend/manage.py migrate
python backend/manage.py createsuperuser
python backend/manage.py runserver 0.0.0.0:8000
pytest
```

- Swagger: http://localhost:8000/docs/
- OpenAPI: http://localhost:8000/api/schema/
- Health: http://localhost:8000/api/v1/health/

## PostgreSQL 17

```bash
# Example local database
# DATABASE_URL=postgres://helpbridge:helpbridge@localhost:5432/helpbridge
```

Set `DATABASE_URL` in `.env`. Django uses psycopg 3. When `DJANGO_ENV=production`, `DATABASE_URL` is required and SQLite is rejected.

```bash
docker compose up --build db
# then set DATABASE_URL and:
python backend/manage.py migrate
python backend/manage.py runserver
```

Full stack:

```bash
docker compose up --build
```

Run migrations against Compose Postgres if the API container starts before they apply:

```bash
docker compose exec api python backend/manage.py migrate
```

## Tests and checks

```bash
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
pytest
```

## Secrets

Never commit `.env`. `.env.example` contains placeholders only. Integration API keys are hashed at rest and shown once at creation time. Platform context tokens are short-lived and signed with `PLATFORM_CONTEXT_SIGNING_KEY`. Do not put that key in the widget.

## Widget and messaging configuration

- The widget asset is `frontend/widget/bridge.js`, collected at
  `/static/widget/bridge.js`. Production deployments should run
  `python backend/manage.py collectstatic` or serve the collected assets from a
  static host.
- Set `CORS_ALLOWED_ORIGINS` to a comma-separated allowlist of exact LMS origins.
  Cross-origin access is disabled when it is empty; credentials are not enabled.
- Set `CHANNEL_PLATFORM_INTEGRATION_ID` and `CHANNEL_DEFAULT_COURSE_ID` to an
  active integration and its published course before enabling Telegram or SMS
  tutoring. The channel workflow stores messages in tenant-scoped chat sessions.
- Configure `SMS_GATEWAY_API_KEY`; inbound gateways must send it in
  `X-SMS-Gateway-Key`. No outbound SMS provider adapter is implemented, so
  outbound SMS is recorded as failed rather than marked delivered.
- Configure `TELEGRAM_BOT_TOKEN` for live Telegram delivery and
  `TELEGRAM_WEBHOOK_SECRET` for webhook deployments. Telegram webhook requests
  must include the secret header; long polling uses the bot token.
