# Keycloak Migration Plan (auth-app as Wrapper Layer)

## Goal

Migrate authentication to Keycloak while keeping `auth-app` as an intermediate compatibility and customization layer, so consuming apps (including `org-app`) do not need a breaking rewrite.

---

## Target Architecture

- **Keycloak** = identity provider (login, credentials, session, token issuance).
- **auth-app (wrapper)** = stable ecosystem-facing API contract and custom business auth logic.
- **org-app and other apps** continue to call `auth-app` (`third/auth`) as they do today.

This keeps external integration stable while enabling progressive migration behind the wrapper.

---

## Why Wrapper Pattern

- Preserves current `third/auth` contract (`token`, `validate`, `whois`, `authorize`).
- Avoids immediate refactor in `org-app`, `provider-app`, and `subscription-app`.
- Centralizes custom rules that Keycloak does not natively model (ecosystem roles/context logic).
- Allows fallback/rollback to current local auth behavior during rollout.

---

## Responsibility Split

### Keycloak owns

- User authentication and credential policy
- MFA / account lock / brute-force protection (optional)
- Standard OIDC token issuance and lifecycle
- Identity federation (future: LDAP, external IdP)

### auth-app wrapper owns

- Existing API surfaces:
  - `admin/auth/*` (if retained for internal ops)
  - `third/auth/token`
  - `third/auth/validate`
  - `third/auth/whois`
  - `third/auth/authorize`
- Token translation/normalization from Keycloak claims to ecosystem claims
- Custom profile mapping:
  - `appScope`
  - `role`
  - `context`
- Authorization policy decisions consumed by `org-app` and others
- Backward-compatible response shapes expected by existing clients

---

## Migration Phases

## Phase 0 - Prep

- Define Keycloak realm, clients, roles, and groups.
- Map existing profile model to Keycloak representation:
  - realm/client roles for `role`
  - attributes/groups for `appScope` and optional `context`
- Add configuration in auth-app:
  - `KEYCLOAK_BASE_URL`
  - `KEYCLOAK_REALM`
  - `KEYCLOAK_CLIENT_ID`
  - `KEYCLOAK_CLIENT_SECRET`
  - `KEYCLOAK_JWKS_URL`
- Keep current local auth as fallback toggle:
  - `AUTH_MODE=local|keycloak|hybrid`

## Phase 1 - Validate / Whois via Keycloak

- Implement Keycloak JWT validation in `third/auth/validate`.
- Implement `third/auth/whois` using normalized claims mapped from Keycloak token.
- Keep `third/auth/token` local for now (safer incremental step).
- Add test parity checks: local token output vs Keycloak-normalized payload.

## Phase 2 - Token issuance bridge

- Switch `third/auth/token` to authenticate through Keycloak token endpoint.
- Convert Keycloak response into existing auth-app response shape:
  - `accessToken`, `tokenType`, `expiresInSeconds`
- Keep old endpoint contract unchanged for clients.

## Phase 3 - Authorize policy enforcement

- Implement `third/auth/authorize` from normalized profiles/claims.
- Add explicit checks for:
  - `appScope` match
  - `requiredRole` match
  - `context` match (when provided)
- Add audit logging for denied decisions.

## Phase 4 - Admin surface strategy

Choose one:

1. **Retain admin/auth in wrapper**  
   auth-app admin UI writes user-role-context model and syncs to Keycloak admin API.

2. **Use Keycloak admin directly**  
   auth-app admin UI becomes read-only or redirects to Keycloak admin for identity ops, but keeps custom profile UI if needed.

Recommended initially: **retain wrapper admin for compatibility**, then progressively move standard IAM actions to Keycloak.

## Phase 5 - Cutover and hardening

- Set `AUTH_MODE=keycloak` in non-dev environments.
- Disable local password auth paths.
- Enable Keycloak production settings (TLS, secure cookies, proper realm config).
- Finalize monitoring and alerts for auth failure rates.

---

## org-app Interaction (No Breaking Change)

`org-app` should continue current flow:

1. Get bearer token (still from `auth-app/third/auth/token`)
2. Call protected endpoint in `org-app`
3. `org-app` calls `auth-app/third/auth/authorize`
4. `auth-app` validates Keycloak token + applies custom policy
5. `org-app` receives `allowed=true|false`

No immediate direct Keycloak dependency in `org-app`.

---

## Customization Examples in Wrapper

- Context-aware role checks (`org-001`, provider contexts, tenant constraints)
- Transitional claim mapping between legacy and Keycloak role naming
- Temporary allow/deny rules during migration waves
- Enriched `whois` payload for ecosystem-specific metadata
- Cross-component policy checks not suitable in raw IdP config

---

## Data and Mapping Strategy

- Migrate existing users/profiles into Keycloak:
  - username
  - password reset required policy (optional)
  - role assignments
  - context attributes
- Build deterministic mapping rules:
  - Keycloak claim -> wrapper `profiles[]`
- Keep migration scripts idempotent (safe re-run).

---

## Security and Operational Considerations

- Validate tokens using Keycloak JWKS (with key rotation support).
- Do not trust frontend role checks; enforce all decisions in backend.
- Store Keycloak secrets only in environment/secret manager.
- Add structured audit events in wrapper:
  - login attempts (success/failure)
  - authorize decisions
  - admin profile/password changes

---

## Rollback Plan

- Keep local auth code path behind feature flag until stable.
- If Keycloak issues occur:
  - switch `AUTH_MODE` back to `local` or `hybrid`
  - preserve API contract so clients remain unaffected

---

## Deliverables Checklist

- [ ] Wrapper Keycloak client module in backend
- [ ] `third/auth/validate` Keycloak-backed
- [ ] `third/auth/whois` normalized mapping
- [ ] `third/auth/token` bridged to Keycloak
- [ ] `third/auth/authorize` policy parity tests
- [ ] Admin strategy implemented (retain/sync or redirect)
- [ ] End-to-end test with `org-app`
- [ ] Feature flag + rollback tested
- [ ] Runbook for ops

