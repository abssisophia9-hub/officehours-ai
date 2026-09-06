# Canvas LTI live-test runbook

Staged checklist for a real AUI Canvas course after PR #80 is deployed.
Demo `/canvas-demo` is **off** when `OFFICEHOURS_DEMO=false`.

Related: [`backend/README.md`](../backend/README.md) (env catalog) ·
[`session_log_opening_auth_canvas.md`](session_log_opening_auth_canvas.md) ·
[`ops_scale.md`](ops_scale.md).

## Prerequisites

- Public HTTPS API + SPA (Canvas will not POST to `localhost`)
- Canvas LTI 1.3 developer key + course External tool
- Canvas API token with read access to the test course modules/files
- Backend running with the env below

## Backend env (minimum)

```bash
export OFFICEHOURS_DEMO=false
export OFFICEHOURS_FRONTEND_URL=https://officehours.aui.ma
export OFFICEHOURS_CORS_ORIGINS=https://officehours.aui.ma

export OFFICEHOURS_LTI_ISSUER=https://canvas.aui.ma
export OFFICEHOURS_LTI_CLIENT_ID=<developer-key-client-id>
export OFFICEHOURS_LTI_LAUNCH_URL=https://officehours-api.aui.ma/lti/launch
# Optional — reject other deployments
# export OFFICEHOURS_LTI_DEPLOYMENT_ID=<deployment-id>

# Live Rooms chapters + Study Agent materials
export CANVAS_BASE_URL=https://canvas.aui.ma
export CANVAS_ACCESS_TOKEN=<canvas-api-token>
```

Confirm:

```bash
curl -s https://officehours-api.aui.ma/auth/config
# expect "demo": false, "lti": true

curl -s https://officehours-api.aui.ma/lti/config
# paste these URLs into the Canvas developer key
```

## Canvas developer key

Admin → Developer Keys → **+ LTI Key** → LTI 1.3:

| Field | Value |
| --- | --- |
| OpenID Connect Initiation URL | `https://YOUR-API/lti/login` |
| Target Link URI / Redirect URI | `https://YOUR-API/lti/launch` |
| JWK Method | Public JWK URL → `https://YOUR-API/lti/jwks` |
| Privacy | **Public** (email must be in the launch) |
| Placement | Course navigation |

Install the tool on a test course (Settings → Apps → By Client ID).

## Live checklist

1. **Student launch** — Canvas course → OfficeHours → lands on `/sso` then `/student` with that course active.
2. **TA launch** — same click as TA enrollment → `/ta`.
3. **Professor launch** — instructor → `/professor`.
4. **Demo lockout** — `POST /canvas/launch` returns **404**; `/canvas-demo` is not registered.
5. **Live sync** — `GET /knowledge/canvas/status` shows `mode: "live"`; Rooms chapters match Canvas modules.
6. **KB gate** — synced materials are `pending_review` until a professor stamps; then `/agent/ask` answers from those materials.
7. **Failure path** — broken launch redirects to `/login?sso_error=…`.

## IT ticket (copy/paste)

> Please provision for OfficeHours AI:
> 1. LTI 1.3 developer key on `https://canvas.aui.ma` with **Public** privacy
> 2. Canvas API token with read access to course modules/files
> 3. (Optional) Microsoft Entra app registration for `@aui.ma` SSO
> 4. DNS: SPA + API origins, both HTTPS
>
> Paste URLs from `GET https://YOUR-API/lti/config` into the developer key.

## Known caveats

- LTI `state`/`nonce` are in-process memory — use a **single** uvicorn worker (or move state to Redis) for multi-instance hosts.
- Without `CANVAS_BASE_URL` + `CANVAS_ACCESS_TOKEN`, launch still works but modules stay empty (no local mirror when demo is off).
