# API Foundation

Base path: `/api/v1/`

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/health/` | API health check | Public |
| POST | `/auth/register/` | Create pending customer account and send verification | Public, throttled |
| POST | `/auth/login/` | Obtain JWT pair and create tracked session | Public, throttled |
| POST | `/auth/refresh/` | Rotate refresh token for current tracked session | Public, throttled |
| POST | `/auth/logout/` | Revoke current server-side session | Authenticated |
| POST | `/auth/verify-email/` | Activate account with signed email token | Public, throttled |
| POST | `/auth/password-reset/` | Send a non-enumerating reset message | Public, throttled |
| POST | `/auth/password-reset/confirm/` | Change password with one-time Django token | Public, throttled |
| GET | `/auth/me/` | Read current user and roles | Authenticated |
| GET/PATCH | `/profile/` | Read or edit caller's profile | Authenticated, self only |
| GET | `/auth/sessions/` | List caller's sessions | Authenticated, self only |
| DELETE | `/auth/sessions/{id}/` | Revoke caller's session | Authenticated, self only |
| GET | `/roles/` | Read roles and attached permissions | `authorization.roles.read` |
| GET | `/permissions/` | Read permission catalog | `authorization.permissions.read` |
| GET/POST/DELETE | `/users/{id}/roles/` | Read or change non-owner role assignments | `authorization.users.assign_role` |
| GET | `/notifications/` | List caller's notifications | Authenticated, self-scoped |
| POST | `/notifications/{id}/read/` | Mark caller's notification read | Authenticated, self-scoped |

## Customer Catalog

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/storefront/` | Homepage sections, active sellers, banners, and product groups | Public |
| GET | `/products/` | Search, filter, sort, and paginate published products | Public |
| GET | `/products/suggestions/?q=...` | Search suggestions | Public |
| GET | `/products/{slug}/` | Product detail, variants, seller, stock, ratings, and images | Public |
| GET/POST | `/products/{slug}/reviews/` | Read or create delivered-purchase reviews | Public read; authenticated verified purchaser create |
| GET | `/reviews/mine/` | List caller's reviews | Authenticated, self only |
| GET | `/categories/`, `/brands/` | Browse active categories and brands | Public |
| POST | `/newsletter/subscribe/` | Subscribe an email address | Public, throttled |

## Seller Workspace

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET/POST | `/seller/application/` | View or submit/resubmit seller application and documents | Authenticated applicant, self only |
| GET | `/management/seller-applications/` | Queue pending/needs-info applications | Admin/Owner review permission |
| POST | `/management/seller-applications/{id}/review/` | Add independent Admin/Owner decision | `seller.applications.review`; no self-review |
| GET | `/management/seller-applications/{id}/documents/{document_id}/` | Download private verification file | Admin/Owner review permission; audited |
| GET | `/seller/dashboard/` | Product/order/earnings metrics | Active seller; seller only |
| GET/POST | `/seller/products/` | List own products or create draft | Active seller; own products only |
| GET/PATCH/DELETE | `/seller/products/{id}/` | Read/update/delete eligible own draft | Active seller; ownership checked in queryset |
| POST | `/seller/products/{id}/submit/` | Submit own product for dual review | Active seller; draft/returned only |
| GET/POST | `/seller/products/{id}/images/` | Read or upload product images | Active seller; private ownership boundary |
| GET/POST | `/seller/products/{id}/variants/` | List/create product options | Active seller; seller-owned product |
| GET/PATCH/DELETE | `/seller/products/{id}/variants/{variant_id}/` | Manage variation and stock | Active seller; seller-owned product |
| GET | `/management/product-approvals/` | Product review queue | Admin/Owner product-review permission |
| POST | `/management/products/{id}/review/` | Add independent product decision | `catalog.products.review`; no self-review |
| GET | `/seller/orders/` | List only seller-specific suborders | Active seller; seller only |
| POST | `/seller/orders/{id}/fulfillment/` | Advance fulfillment and add tracking | Active suborder's seller only |
| GET | `/seller/returns/` | List own return requests | Active seller; seller only |
| POST | `/seller/returns/{id}/review/` | Approve or decline a return request | Active suborder's seller only |
| GET/POST | `/seller/payout-requests/` | Read or request settlement from eligible balance | Active seller; balance calculated server-side |

## Customer Shopping

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET/POST | `/addresses/` | List/add shipping addresses | Authenticated, self only |
| GET/PATCH/DELETE | `/addresses/{id}/` | Manage own address | Authenticated, self only |
| GET/POST | `/cart/` | Read cart or add published product | Authenticated, self only |
| PATCH/DELETE | `/cart/items/{id}/` | Change/remove own cart line | Authenticated, self only |
| GET/POST | `/wishlist/` | Read/add own wishlist items | Authenticated, self only |
| DELETE | `/wishlist/{product_id}/` | Remove own wishlist item | Authenticated, self only |
| POST | `/coupons/validate/` | Validate a coupon against a subtotal | Authenticated |
| GET | `/shipping/quote/?address_id=...` | Quote destination shipping by cart seller count | Authenticated, address ownership checked |
| POST | `/checkout/` | Create idempotent parent order and seller suborders | Authenticated; COD is the enabled payment method |
| GET | `/orders/` | List caller's orders and seller-specific tracking | Authenticated, self only |
| GET | `/orders/{id}/` | Read own order | Authenticated, self only |
| POST | `/orders/{id}/cancel/` | Cancel eligible unshipped order and restore stock | Authenticated, self only |
| GET | `/orders/{id}/invoice/` | Render printable HTML invoice | Authenticated, self only |
| POST | `/orders/suborders/{id}/returns/` | Request return for delivered seller order | Authenticated, parent order ownership checked |
| GET | `/payments/` | List caller's payment records | Authenticated, self only |

## Payments, Refunds & Financial Reconciliation (Phase 5)

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| POST | `/payments/{order_id}/initiate/` | Initiate payment session for `sslcommerz`, `bkash`, `nagad`, `card`, or `bank_transfer` (rejects raw card PAN/CVV) | Authenticated order owner |
| POST | `/payments/webhook/{provider}/` | Server-side provider webhook verification with HMAC signature check, `PaymentWebhookEvent` duplicate callback protection, gateway fee ledger posting, and stock restoration on failure | Public webhook (HMAC signature verified) |
| POST | `/owner/payments/{order_id}/refund/` | Atomic full order refund synchronizing `Order`, `SellerOrder`, `Payment`, stock restoration, `SellerEarning(entry_type=REFUND)`, and append-only `FinancialLedgerEntry(transaction_type=REFUND_DEDUCTION)` | Owner role only |
| GET | `/owner/payments/reconciliation/` | Financial reconciliation report comparing completed suborder earnings, seller ledger credits/debits, settled payouts, and ledger entries | Owner role only |

## Manager Portal & Business Ownership Management (Phase 4)

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/manager/dashboard/` | Permission-scoped Manager dashboard: profile, responsibilities, authorized business overview, order reports, revenue analytics (`manager.reports.finance`), seller/product reports, assigned Admin monitoring (`manager.admins.monitor`), and own share ownership (`manager.shares.read`, `manager.shares.documents`) | Active Manager or Owner |
| GET/POST | `/owner/managers/` | List all managers and invitations, or create/invite a new manager account | Owner role only |
| POST | `/owner/managers/{id}/status/` | Activate, suspend, or remove a manager with immediate session invalidation | Owner role only |
| POST | `/owner/managers/{id}/permissions/` | Grant or revoke any of the 8 granular manager permissions (`UserPermission` override) with immediate effect | Owner role only |
| GET/POST | `/owner/admin-assignments/` | Assign, reassign, or remove Admin accounts to/from individual Managers and read assignment history | Owner role only |
| GET/POST | `/owner/shares/plans/` | List or create/update internal `BusinessSharePlan` and `BusinessShare` classes and company valuation | Owner role only |
| POST | `/owner/shares/offers/` | Record a share offer (`ShareOffer`) for a selected partner within the permitted allocation ceiling | Owner role only |
| POST | `/owner/shares/allocations/` | Allocate partner ownership shares (`ShareAllocation`) under a row lock, validating total allocated percentage never exceeds plan limits and recording append-only `ShareTransaction` and `OwnershipHistory` entries | Owner role only |
| POST | `/owner/shares/transfers/` | Execute a legally documented share transfer between two partners with append-only transaction and ownership history logging | Owner role only |
| POST | `/owner/shares/documents/` | Record an ownership legal document (`ShareDocument`: certificate, shareholder agreement, transfer deed, valuation report) | Owner role only |

## Final Owner & Admin Role Structure (16-Permission Engine)

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET/POST | `/owner/admins/` | List all Admin staff accounts and their 16 permission states, or create a new Admin staff account (0 permissions by default) | Owner role only |
| POST | `/owner/admins/{id}/status/` | Activate, suspend, or remove an Admin staff account with immediate `AuthSession` revocation | Owner role only |
| POST | `/owner/admins/{id}/permissions/` | Grant or revoke any of the 16 granular Admin permissions (`UserPermission`) with immediate backend enforcement, notification, and `AuditLog` | Owner role only |
| GET | `/admin-staff/me/permissions/` | Return the signed-in Admin's live backend-evaluated 16 permissions to sync frontend navigation | Admin or Owner |
| GET/POST | `/admin-staff/products/` | List or upload platform-owned SHOPLEX products (`ownership_type="platform"`, `seller="SHOPLEX Official"` owned by Owner, `created_by=actor`, `product_source`) | Owner or Admin with `admin.products.create` |
| PATCH/DELETE | `/admin-staff/products/{id}/` | Edit or delete platform-owned SHOPLEX products | Owner or Admin with `admin.products.edit` / `admin.products.delete` |
| POST | `/admin-staff/products/{id}/publish/` | Publish a platform-owned SHOPLEX product | Owner or Admin with `admin.products.publish` |
| GET | `/admin-staff/orders/` | View marketplace orders for operational support | Owner or Admin with `admin.orders.manage` |
| GET | `/admin-staff/customers/` | View marketplace customer directory | Owner or Admin with `admin.customers.manage` |
| GET | `/admin-staff/finance-report/` | Read-only selected financial report (no ledger writes or earnings access) | Owner or Admin with `admin.finance.reports` |
| POST | `/admin-staff/refunds/{order_id}/` | Process an Owner-authorized order refund with stock restoration and immutable ledger entry | Owner or Admin with `admin.refunds.process` |

## Admin & Owner Control Center (Phase 3)

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| GET | `/management/admin-dashboard/` | Operational moderation metrics, recent approval timeline, and product catalog list (no revenue/profit exposure) | Admin or Owner (`catalog.products.review` / `seller.applications.review`) |
| POST | `/management/products/{id}/status/` | Suspend (`suspend`) or restore (`restore`) a product listing | Admin or Owner (`suspend`); Owner only (`restore`) |
| GET/POST | `/management/product-reports/` | File a product compliance report (`POST`) or list reports (`GET`) | Authenticated create; Admin or Owner list |
| POST | `/management/product-reports/{id}/resolve/` | Resolve or dismiss a product report, with optional product suspension | Admin or Owner |
| GET | `/owner/dashboard/` | Executive business metrics (9), financial metrics (12), daily/monthly/yearly revenue charts, seller & product performance leaderboards | Owner role only |
| GET | `/owner/sellers/` | Full seller directory with product counts, order counts, gross sales, commissions, net earnings, and paid payouts | Owner role only |
| POST | `/owner/sellers/{id}/status/` | Suspend or reactivate a seller store and account, revoking active sessions on suspension | Owner role only |
| GET | `/owner/payouts/` | List all seller payout requests | Owner role only |
| POST | `/owner/payouts/{id}/decision/` | Approve, settle (`paid`), or reject a seller payout request; settling posts an immutable `FinancialLedgerEntry` | Owner role only |
| GET/POST | `/owner/finance/ledger/` | Read the immutable append-only financial ledger and summary totals, or record an operational expense / payment fee / refund deduction | Owner role only |
| POST | `/owner/categories/`, `/owner/brands/` | Create or update marketplace categories and brands | Owner role only |
| GET/PUT | `/owner/settings/` | Read or update the 11 platform settings domains (`website_info`, `branding`, `commission_defaults`, `shipping_config`, `tax_settings`, `refund_policies`, `payment_gateways`, `email_config`, `seo_settings`, `maintenance_mode`, `notification_settings`) | Owner role only |
| GET/POST | `/owner/security/` | Read mandatory MFA device status, active sessions, and login alerts; enroll/rotate MFA device or reauthenticate with password | Owner role only |
| GET | `/owner/audit-logs/` | Inspect the append-only platform audit history | Owner role only |

## Owner & Management Analytics

- `GET /management/overview/`: permission-scoped operational, financial (14-day daily GMV/order series, commission total, status breakdown), and user role metrics (`platform.analytics.read` for Owner/Manager commerce & user telemetry; operational moderation metrics for Admin/Owner/Manager).
- `GET/POST /management/commission-rules/`: configure global, category, or seller rates; Owner role only.
- `GET/POST /management/shipping-rules/`: configure country shipping rates; Owner role only.
- The environment fallback commission is `DEFAULT_PLATFORM_COMMISSION_PERCENT` (10.00 by default); database rules take precedence.

Schema JSON: `/api/schema/`; Swagger UI: `/api/docs/`. Email tokens are written to the console in development.
