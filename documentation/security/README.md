# Security Baseline

- Use the custom email-based `accounts.User`; never switch `AUTH_USER_MODEL` after the first migration.
- Django password validation requires 12 characters and Argon2 is the preferred hasher.
- Never commit `.env`; production must provide a strong `DJANGO_SECRET_KEY`, database credentials, HTTPS, and a real email provider.
- API endpoints default to authenticated access. Anonymous auth endpoints use DRF throttling; browser route protection is not treated as authorization.
- JWT access lifetime is short; refresh tokens rotate and are tied to revocable database sessions. Store tokens in memory in the Phase 1 browser shell; a production rollout should move session credentials to a carefully designed HttpOnly/SameSite cookie or backend-for-frontend pattern.
- Verify all security-sensitive state and resource ownership in API code. Do not rely on portal hostname or frontend role checks.
- Audit rows are append-only through the Django model; use database-level enforcement and restricted operational access in production.
- MFA model is groundwork only. Enrollment, secret encryption/key rotation, challenge enforcement, and recovery are pending.
- Email verification and reset messages use Django's console backend by default; configure a production email service before external use.
- Compose passwords are development-only defaults. Do not expose the development stack to the public internet.
