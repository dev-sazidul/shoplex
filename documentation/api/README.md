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

## Owner Configuration

- `GET/POST /management/commission-rules/`: configure global, category, or seller rates; Owner role only.
- `GET/POST /management/shipping-rules/`: configure country shipping rates; Owner role only.
- The environment fallback commission is `DEFAULT_PLATFORM_COMMISSION_PERCENT` (10.00 by default); database rules take precedence.

Schema JSON: `/api/schema/`; Swagger UI: `/api/docs/`. Email tokens are written to the console in development.
