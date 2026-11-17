# SHOPLEX Architecture

## System Shape

Five separate Next.js applications share React/TypeScript UI and types. They use a single versioned Django REST API; PostgreSQL is the source of truth for identity, authorization, platform data, sessions, and audit history. Redis backs Celery and Django's configured cache integration point. Nginx provides the local reverse-proxy entry point.

```text
Customer / Seller / Admin / Manager / Owner Next.js apps
                         |
                 HTTPS / JSON REST
                         |
              Nginx -> Django REST API
                         |
             PostgreSQL + Redis / Celery
```

## Ownership Boundaries

- `accounts`: custom email-based user, profile, registration, verification, login, reset, and session operations.
- `authorization`: platform roles, granular permissions, role assignments, user-level grants/denials, and API permission checks.
- `platform`: sessions, MFA devices, seller/manager identity records, notifications, settings, and audit events.
- `frontend/packages/ui`: shared visual tokens and components; no authorization decisions live in browser code.
- `frontend/apps/*`: independent Next.js deployables; each consumes the same backend and shared packages.

## Authentication / Authorization

The API issues 10-minute access JWTs and 7-day rotating refresh JWTs. Both carry a session identifier; refresh rotates the stored JTI under a database row lock, and protected API requests reject missing, expired, revoked, or suspended sessions. Password resets and logout revoke server-side sessions. User status is checked on every authenticated request.

RBAC uses `Role`, `Permission`, `RolePermission`, `UserRole`, and `UserPermission`. Explicit grants or denials override role grants; only the owner role receives foundation management permissions by seed migration. Owner role assignment is intentionally excluded from the API and provisioned with the `create_owner` management command.

## Database Notes

The initial identity and platform schema uses UUID identifiers for user-facing entities, normalized join tables, database uniqueness constraints, explicit indexes, and foreign keys. `AuditLog` blocks update/delete through its model API; production should additionally use a PostgreSQL role/trigger policy to enforce append-only behavior against direct SQL.

## Deployment Boundary

`docker-compose.yml` runs PostgreSQL, Redis, the Django development server, a Celery worker, and Nginx. The five Next apps run independently with `npm run dev:<portal>` from `frontend/`. The compose API uses Django's development server and must be replaced with a production WSGI server and hardened secrets/TLS before deployment.
