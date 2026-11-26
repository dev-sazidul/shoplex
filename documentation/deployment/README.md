# SHOPLEX Production Deployment, Backup & Rollback Guide

## 1. Production Stack (`docker-compose.prod.yml`)

The production topology runs:
- **PostgreSQL 17 (`db`)**: Persistent relational store with `/backups` volume mount and healthcheck.
- **Redis 8 (`redis`)**: Append-only cache and Celery message broker.
- **Django + Gunicorn (`api`)**: Runs `manage.py migrate --noinput`, `manage.py check --deploy`, and serves the WSGI application via 4 Gunicorn workers.
- **Celery Worker (`worker`)**: Executes multi-channel notifications (`deliver_notification_task`) and background tasks.
- **Nginx 1.27 (`nginx`)**: Terminates TLS 1.2/1.3, enforces `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, and rate limits `/api/v1/auth/` (`5r/m`) and `/api/` (`20r/s`).

## 2. Deployment Steps

1. Prepare environment secrets in `.env` (never commit `.env` to Git):
   ```sh
   DJANGO_SECRET_KEY=<64-byte-cryptographic-secret>
   DJANGO_DEBUG=false
   DJANGO_ALLOWED_HOSTS=shoplex.com,seller.shoplex.com,admin.shoplex.com,manager.shoplex.com,owner.shoplex.com,api.shoplex.com
   DJANGO_CORS_ALLOWED_ORIGINS=https://shoplex.com,https://seller.shoplex.com,https://admin.shoplex.com,https://manager.shoplex.com,https://owner.shoplex.com
   POSTGRES_DB=shoplex
   POSTGRES_USER=shoplex
   POSTGRES_PASSWORD=<strong-database-password>
   OWNER_EMAIL=owner@shoplex.com
   OWNER_PASSWORD=<strong-owner-password>
   ```
2. Place TLS certificates (`fullchain.pem`, `privkey.pem`) in `infrastructure/certs/`.
3. Launch the production cluster and provision the Owner account:
   ```sh
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml exec api python manage.py create_owner
   ```
4. Build and start the five Next.js portals against `NEXT_PUBLIC_API_BASE_URL=https://api.shoplex.com/api/v1`.

## 3. Automated PostgreSQL Backup & Restore

- **Create Verified Dump + SHA-256 Checksum:**
  ```sh
  sh infrastructure/scripts/backup_postgres.sh
  ```
- **Restore from Verified Dump:**
  ```sh
  sh infrastructure/scripts/restore_postgres.sh ./infrastructure/backups/<backup-file.dump>
  ```

## 4. Rollback Procedure

1. Take an immediate snapshot backup via `infrastructure/scripts/backup_postgres.sh`.
2. Check out the previous verified release tag.
3. If a schema migration must be reversed, run `python manage.py migrate <app> <previous_migration>` inside the `api` container before redeploying the previous image.
4. Redeploy containers with `docker compose -f docker-compose.prod.yml up -d --build` and verify `/api/v1/health/` and `/api/v1/owner/payments/reconciliation/`.
