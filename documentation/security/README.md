# SHOPLEX Security Architecture & Phase 5 Audit Report

## 1. Authentication, Sessions & MFA

- **Password Hashing**: Argon2id primary (`Argon2PasswordHasher`) with 12-character minimum password policy.
- **Session-Bound Rotating JWTs**: 10-minute access tokens and 7-day rotating refresh tokens bound to server-side `platform.AuthSession` records (`select_for_update()` JTI rotation).
- **Immediate Session Revocation**: Password resets, logout, seller suspension, and manager suspension/removal immediately revoke active `AuthSession` rows in PostgreSQL.
- **Owner Security**: Mandatory TOTP MFA device registration (`MFADevice`), password reauthentication on sensitive security actions, and automated Owner login alerts with suspicious IP/User-Agent detection.

## 2. Six Mandatory Security Rules Verification

| Rule | Enforcement Mechanism | Verified By |
| --- | --- | --- |
| **1. Sellers cannot access another seller's data** | All seller product, variant, order, return, dashboard, and payout queries filter by `seller=request.user.seller_profile` | `ProductWorkflowTests.test_seller_product_listing_is_scoped_to_own_store`, `CommerceWorkflowTests` |
| **2. Admin cannot access platform financial information** | `/api/v1/management/admin-dashboard/` excludes all financial data; all `/api/v1/owner/*` and `/api/v1/owner/payments/*` views call `_require_owner(request.user)` | `ControlCenterPhase3Tests.test_admin_permission_boundaries_block_all_owner_financial_and_governance_apis`, `Phase5PaymentsFinancialAndSecurityTests` |
| **3. Managers cannot exceed Owner-assigned permissions** | `ManagerPortalDashboardView` checks `user_has_permission` per module (`manager.reports.finance`, `manager.admins.monitor`, `manager.shares.read`, etc.) and filters `AdminAssignment` and `ShareAllocation` to the caller | `ManagerAndShareGovernanceTests.test_financial_data_isolation_and_dynamic_permission_grant_revoke` |
| **4. Only Owner controls manager accounts** | `/api/v1/owner/managers/*` and `/api/v1/owner/admin-assignments/` require `Role.Key.OWNER` | `ManagerAndShareGovernanceTests.test_owner_creates_manager_and_prevents_manager_privilege_escalation` |
| **5. Only authorized Owner-level users can perform sensitive financial operations** | Commission rules, shipping rules, payout decisions, ledger postings, and order refunds enforce `_require_owner` inside atomic transactions | `ControlCenterPhase3Tests.test_immutable_financial_ledger_and_payout_settlement`, `Phase5PaymentsFinancialAndSecurityTests` |
| **6. Seller and product publication requires both Owner and Admin approval** | `review_seller_application` and `review_product` require distinct current-cycle `APPROVED` records from both `admin` and `owner` reviewer roles | `SellerOnboardingTests`, `ProductWorkflowTests.test_product_is_not_public_until_admin_and_owner_both_approve` |

## 3. Payment & Financial Ledger Integrity

- **Zero Raw Card Storage**: `PaymentInitiationView` and `PaymentWebhookView` explicitly reject payloads containing `card_number`, `pan`, `cvv`, `cvc`, or `pin`.
- **Webhook Signature & Idempotency**: `PaymentWebhookView` verifies HMAC-SHA256 signatures, checks server-calculated order amounts, and records unique `PaymentWebhookEvent.event_id` rows to ignore duplicate callbacks.
- **Append-Only Ledgers**: `AuditLog`, `FinancialLedgerEntry`, `ShareTransaction`, and `OwnershipHistory` block `.save()` on existing primary keys and block `.delete()` at the model layer.
