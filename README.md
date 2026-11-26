# SHOPLEX

SHOPLEX is a multi-portal marketplace monorepo with one Django REST API and a shared PostgreSQL database. Phase 1 establishes the platform foundation; commerce workflows and portal-specific operations are intentionally deferred.

## Structure

- `frontend/apps/`: independent Next.js applications for Customer, Seller, Admin, Manager, and Owner.
- `frontend/packages/ui/`: shared SHOPLEX design-system components.
- `backend/config/`: Django settings, URL routing, and Celery configuration.
- `backend/apps/`: identity, authorization, and platform foundation models/APIs.
- `infrastructure/`: Docker and Nginx development configuration.
- `documentation/`: architecture, security, and phase progress notes.

## Quick start

Copy `.env.example` to `.env`, then run the backend and infrastructure:

```sh
docker compose up --build
```

The API is available at `http://localhost:8000/api/v1/`; interactive OpenAPI docs are at `http://localhost:8000/api/docs/`. To run the customer frontend separately, use `cd frontend && npm install && npm run dev:customer`.

For Python development without Docker, create a virtual environment, install `backend/requirements.txt`, set `DATABASE_URL` to a local PostgreSQL database (or omit it to use the development SQLite fallback), then run `python backend/manage.py migrate` and `python backend/manage.py runserver`.

See [documentation/PROJECT_PROGRESS.md](documentation/PROJECT_PROGRESS.md) for what is implemented and what remains.
