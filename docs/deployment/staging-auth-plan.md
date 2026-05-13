# V2 Staging Auth Plan

This phase adds staging protection only. It is not enterprise SSO, customer self-service onboarding, or a full SaaS tenant model.

## Modes

Local demo mode keeps the original one-command workflow:

```text
AUTH_ENABLED=false
NEXT_PUBLIC_AUTH_ENABLED=false
NEXT_PUBLIC_DEMO_ORG_ID=<seed org id>
```

In this mode the frontend continues to pass the deterministic demo organization id and the API accepts explicit `organization_id` values. Use seed/demo data only.

Protected staging mode requires login:

```text
AUTH_ENABLED=true
JWT_SECRET_KEY=<strong random secret>
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none
DEMO_ADMIN_EMAIL=<admin email>
DEMO_ADMIN_PASSWORD=<temporary seed password>
NEXT_PUBLIC_AUTH_ENABLED=true
NEXT_PUBLIC_API_BASE_URL=https://<staging-api-domain>
```

When auth is enabled, the API validates the signed HttpOnly session cookie and verifies that the logged-in user has a membership for the requested organization.

## Session Behavior

- Login: `POST /v1/auth/login` with email and password.
- Current user: `GET /v1/auth/me`.
- Logout: `POST /v1/auth/logout`.
- The browser receives an HttpOnly cookie; JavaScript never reads a JWT.
- Passwords are stored as bcrypt hashes only.
- The API never returns passwords, password hashes, OAuth tokens, or provider secrets.

## Staging Requirements

- Use HTTPS for both frontend and API.
- Store env vars in the hosting provider secret manager, not git.
- Use `AUTH_COOKIE_SECURE=true` on HTTPS staging.
- Use `AUTH_COOKIE_SAMESITE=none` if the frontend and API are on different sites.
- Set `CORS_ORIGINS` to the exact staging frontend origin.
- Run Alembic migrations before seeding.
- Run `scripts/seed_dev.py` with `DEMO_ADMIN_EMAIL` and `DEMO_ADMIN_PASSWORD` set to create the first staging admin user.
- Rotate or remove temporary demo passwords before broader team access.

## Deferred

- SSO/OAuth login.
- Password reset and invite emails.
- Per-feature role permissions.
- Session revocation lists.
- Multi-organization switching UI.
