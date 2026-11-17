# SHOPLEX Project Progress

Last updated: 2026-11-17 · Phase 2 UI hardening

## Completed

- Initialized a monorepo with five separately runnable Next.js 16 applications: Customer, Seller, Admin, Manager, and Owner.
- Added shared TypeScript contracts and a SHOPLEX UI package with brand tokens, responsive typography/layout, buttons, inputs, cards, status pills, tables, dialogs, sidebar navigation, notices, and loading/empty/error states.
- Created a custom UUID/email Django user model and relational profiles, role/permission joins, session and MFA records, seller/manager foundation records, notifications, audit logs, and platform settings.
- Added versioned REST endpoints for account registration, email verification, login, JWT refresh rotation, logout, password reset, current user, session management, roles, permissions, and notifications.
- Added server-side account-status/session validation, permission checks, owner-only privilege seeding, role assignment audit events, and owner bootstrap command.
- Configured PostgreSQL via `DATABASE_URL`, SQLite fallback for local checks, Argon2-first password hashing, DRF throttling, CORS, security settings, Swagger/OpenAPI, Redis, and Celery.
- Added Docker Compose services for PostgreSQL, Redis, Django, Celery, and Nginx; added architecture/API/security documentation.
- Added nine backend tests covering verification, session issuance/revocation, refresh replay rejection, suspended-account access/refresh, cross-session logout isolation, role permission checks, and notification isolation.
- Phase 2 added Django `catalog`, `commerce`, and `sellers` domains; Customer storefront/account and Seller onboarding/workspace routes reuse the Phase 1 API, custom user model, auth, and shared UI.
- Customer flows now include server-rendered marketplace data, product/category/brand/store pages, product search/filter/sort/suggestions, product detail/structured data/reviews, registration/verification/password recovery, profile/security, addresses, cart/wishlist, coupon/shipping quote, idempotent multi-seller checkout, order tracking/cancellation/returns, printable invoice, payment history, notifications, and SEO sitemap/robots.
- Seller flows now include application submission/status with private documents, Admin + Owner review-cycle history and notifications, products/drafts/images/variants/inventory, dual product approval, own-order fulfillment/tracking/returns, earnings, and balance-limited payout requests.
- Financial/order behavior is server-calculated: configurable commission precedence, default commission environment value, seller-specific suborders, reserved stock, retry-safe checkout, completion-gated seller earnings, and owner-controlled shipping/commission configuration endpoints.
- Added 13 additional backend tests (22 total) covering dual seller approval, rejection/resubmission cycles, product publication gate, seller isolation, split checkout/idempotency/stock rollback, shipping quote, delivered-purchase reviews, payment privacy, and payout eligibility.
- Added private reviewer document downloads, printable customer invoices, protected product and seller review queues, configurable shipping quotes, customer payment/review history, and seller-owned product-variation stock controls.
- UI hardening pass: fixed the shared Button default so non-submit actions cannot accidentally submit forms; seller-only workspace routes now redirect unapproved/customer accounts to the application flow while preserving customer access to seller onboarding; refreshed shared responsive tokens, sticky marketplace navigation/filter/sidebar behavior, card surfaces, focus states, and mobile-safe spacing.

## Folder Structure

```text
frontend/
  apps/{customer,seller,admin,manager,owner}/  # separate Next.js applications
  packages/ui/                                 # shared components, styles, design tokens
  packages/types/                              # shared API/identity types
backend/
  config/                                       # settings, URLs, ASGI/WSGI, Celery
  apps/accounts/                                # custom user and authentication APIs
  apps/authorization/                           # roles, permissions, permission classes
  apps/platform/                                # sessions, notifications, audit and profiles
  apps/catalog/                                 # products, taxonomy, images, reviews and approval history
  apps/commerce/                                # cart, addresses, split orders, commission, payout and returns
  apps/sellers/                                 # seller applications, review, dashboard and private documents
infrastructure/
  docker/                                       # API Dockerfile
  nginx/                                        # reverse-proxy config
documentation/
  architecture/ api/ security/                 # system design and handoff docs
```

## Database Models

- `accounts.User`: UUID custom user, unique email login, status and verification timestamp.
- `accounts.UserProfile`: one-to-one profile/preferences.
- `authorization.Role`, `Permission`, `RolePermission`, `UserRole`, `UserPermission`: normalized role catalog, role grants, assignments, and expiring direct overrides.
- `platform.AuthSession`, `MFADevice`: revocable JWT session metadata and MFA-ready device record.
- `platform.SellerProfile`, `SellerApplication`, `SellerDocument`, `SellerApplicationApproval`, `ManagerProfile`, `ManagerInvitation`: seller business records and reviewer-cycle history; manager records remain foundation-only.
- `platform.Notification`, `AuditLog`, `PlatformSetting`: user-scoped alerts, append-only-through-model event records, and key/value configuration.
- `catalog.Category`, `Brand`, `Product`, `ProductImage`, `ProductVariant`, `ProductApproval`, `ProductReview`, `MarketingBanner`, `NewsletterSubscription`: catalog, content, variations, dual-review history, and ratings.
- `commerce.Address`, `Cart`, `CartItem`, `WishlistEntry`, `Coupon`, `CouponRedemption`, `ShippingRule`, `CommissionRule`: customer shopping state and pricing rules.
- `commerce.Order`, `SellerOrder`, `OrderItem`, `Payment`, `SellerEarning`, `SellerPayoutRequest`, `ReturnRequest`: parent checkout, seller-specific fulfillment, payment record, earnings ledger, settlements, and returns.

All migrations are present and checked for drift. Seller and product approvals are recorded separately by reviewer role and cycle; publication/activation requires both current-cycle decisions. The order and payout state is server-controlled; sellers cannot submit balance values.

## API Endpoints

See [API foundation](api/README.md) for methods, paths, and access rules. All business APIs are under `/api/v1/`; schema and Swagger UI are at `/api/schema/` and `/api/docs/`.

## Environment Variables

- `DJANGO_SECRET_KEY`: mandatory in non-debug mode; development can generate a per-process fallback.
- `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`: Django mode and host allowlist.
- `DJANGO_CORS_ALLOWED_ORIGINS`: comma-separated portal origins.
- `DATABASE_URL`: PostgreSQL URL; omitted locally to use SQLite.
- `POSTGRES_PASSWORD`: Compose-only database password; local fallback is not production safe.
- `REDIS_URL`: Redis broker/cache URL.
- `FRONTEND_BASE_URL`: verification/reset URL base for future email templates.
- `OWNER_EMAIL`, `OWNER_PASSWORD`: used only by `create_owner` bootstrap command.
- `NEXT_PUBLIC_API_BASE_URL`: optional browser API base; defaults to `http://localhost:8000/api/v1`.
- `NEXT_PUBLIC_SITE_URL`: canonical and sitemap origin; defaults to `http://localhost:3000`.
- `DEFAULT_PLATFORM_COMMISSION_PERCENT`: configurable global fallback commission; defaults to `10.00` percent.

See `.env.example` for the starter values.

## Verification

- `python backend/manage.py check`: passed.
- `python backend/manage.py makemigrations accounts authorization platform`: passed and generated initial migrations.
- `python backend/manage.py migrate`: passed against local SQLite because Docker/PostgreSQL are unavailable in the current shell.
- `python backend/manage.py test apps.accounts apps.authorization apps.platform`: 9 tests passed.
- `python backend/manage.py makemigrations --check --dry-run`: passed with no model/migration drift.
- `python backend/manage.py spectacular --validate`: passed with no schema errors or warnings.
- `cd frontend && npm install`: passed, no reported vulnerabilities.
- `python backend/manage.py test apps.accounts apps.authorization apps.sellers apps.catalog apps.commerce apps.platform`: 22 tests passed.
- `npm run build:all`: passed for all five Next.js applications; Customer includes static account/marketing routes and server-rendered dynamic product/category/store routes.
- Latest verification limitation: the workspace currently has no usable Node/npm binary, and the checked-in `.venv` points to a missing Homebrew Python 3.14 binary; therefore this UI hardening pass was validated with editor diagnostics only and the existing recorded backend/frontend verification remains the last successful full run.
- Live Django API `/api/v1/health/`, `/api/v1/storefront/`, Customer `/`, `/products`, `/robots.txt`, and `/sitemap.xml`: HTTP 200.
- Docker Compose YAML parses successfully.
- PostgreSQL/Compose startup was not run: Docker is not installed in the current environment.

Phase 2 migrations: `platform.0002_sellerapplication_review_cycle_and_more`, `platform.0003_sellerapplication_uniq_active_seller_application`, `authorization.0003_marketplace_review_permissions`, `catalog.0001_initial`, `catalog.0002_alter_product_price`, `commerce.0001_initial`, `commerce.0002_order_idempotency_key_and_more`, and `commerce.0003_alter_coupon_discount_value_and_more`.

## Pending / Later Phases

- Run migrations and integration tests against PostgreSQL in Docker/CI; configure production database, secrets, TLS, backups, and monitoring.
- Replace development server with Gunicorn in production; harden Nginx and compose credentials.
- Implement secure production cookie/BFF token delivery and production email provider/templates. Browser tokens remain memory-only in Phase 2, so a full page reload requires signing in again.
- Encrypt MFA secrets and implement enrollment, challenge, recovery, and owner-mandatory MFA.
- Add database-level audit immutability and comprehensive audit coverage for every sensitive action.
- Add password reset/session race tests, concurrent checkout/stock tests, API browser tests, and PostgreSQL CI integration.
- Implement online payment-provider integrations/webhooks, refund execution/reconciliation, taxes, and production settlement execution; checkout currently supports Cash on Delivery only. Return requests can be reviewed, but money movement is not implemented.
- Implement Owner/Admin review queue screens; the protected review APIs are present, while their operational portal UIs remain for later phases.
- Finish private document malware scanning and move local private uploads/product images to configured cloud object storage.
- Build remaining Admin, Owner, and Manager portals and business settings/share management in later phases.
- Run PostgreSQL/Compose end-to-end in an environment with Docker; production hardening, TLS, backups, observability, and deployment remain required.

This file is the cross-phase handoff; update it at the end of each later phase.
