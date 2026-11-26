# SHOPLEX

> **One Marketplace. Endless Opportunities.**

SHOPLEX is an enterprise multi-portal e-commerce marketplace monorepo powered by a centralized **Django REST Framework** API, a normalized **PostgreSQL** database (with local SQLite fallback for zero-config development), **Redis / Celery** background workers, and five independent **Next.js 16** portals sharing the `@shoplex/ui` luxury design system and `@shoplex/types` contracts.

## Five-Portal Architecture

| Portal | Production Domain | Local Port | Script | Role / Purpose |
| --- | --- | --- | --- | --- |
| **Customer** | `shoplex.com` | `3000` | `npm run dev:customer` | Multi-vendor storefront, discovery, quick-view, split-order checkout, account & returns |
| **Seller** | `seller.shoplex.com` | `3001` | `npm run dev:seller` | Merchant studio, onboarding application, multi-variant catalog, fulfillment & payouts |
| **Admin** | `admin.shoplex.com` | `3002` | `npm run dev:admin` | Operations center, seller verification queue, product moderation & catalog health |
| **Manager** | `manager.shoplex.com` | `3003` | `npm run dev:manager` | Regional management & authorized business analytics (`platform.analytics.read`) |
| **Owner** | `owner.shoplex.com` | `3004` | `npm run dev:owner` | Executive governance console, GMV/commission charts, dual approvals & financial rules |

## Monorepo Structure

- `frontend/apps/{customer,seller,admin,manager,owner}/` — Five standalone Next.js App Router portals.
- `frontend/packages/ui/` — Shared SHOPLEX design system (`Button`, `TextInput`, `SelectInput`, `TextareaInput`, `Checkbox`, `Card`, `DataTable`, `Modal`, `Sidebar`, `TopNav`, `PortalShell`, `StatCard`, `AreaChart`, `BarChart`, `Icon`, `StatusPill`, `Badge`, `Tooltip`, `Breadcrumbs`, `LoadingState`, `Skeleton`, `EmptyState`, `ErrorState`).
- `frontend/packages/types/` — Shared TypeScript API contracts.
- `backend/config/` — Django settings, URL routing, OpenAPI schema, and Celery configuration.
- `backend/apps/{accounts,authorization,platform,catalog,commerce,sellers}/` — Domain modules.
- `infrastructure/` — Docker & Nginx configuration.
- `documentation/` — Architecture, ER diagram, API contracts, security notes, and [PROJECT_PROGRESS.md](documentation/PROJECT_PROGRESS.md).

## Quick Start (Local Development)

1. **Backend & Demo Data:**
   ```sh
   python backend/manage.py migrate
   python backend/manage.py seed_demo
   python backend/manage.py runserver 0.0.0.0:8000
   ```
   - REST API: `http://localhost:8000/api/v1/`
   - Swagger UI: `http://localhost:8000/api/docs/`

2. **Frontend Portals:**
   ```sh
   cd frontend
   npm install
   npm run dev --workspace=@shoplex/customer -- --webpack
   ```
   *(Use `--workspace=@shoplex/seller`, `@shoplex/admin`, `@shoplex/manager`, or `@shoplex/owner` for the other portals.)*

3. **Development Demo Accounts (seeded by `seed_demo`, password `Shoplex-Demo-2026!`):**
   - Customer: `customer@shoplex.local`
   - Seller: `seller@shoplex.local`
   - Admin: `admin@shoplex.local`
   - Manager: `manager@shoplex.local`
   - Owner: `owner@shoplex.local`

4. **Docker Compose (PostgreSQL + Redis + API + Celery + Nginx):**
   ```sh
   cp .env.example .env
   docker compose up --build
   ```

See [documentation/PROJECT_PROGRESS.md](documentation/PROJECT_PROGRESS.md) and [documentation/architecture/README.md](documentation/architecture/README.md) for the database ER diagram and detailed progress log.
