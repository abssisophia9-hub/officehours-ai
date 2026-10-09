# Session log — opening, Microsoft sign-in, Canvas LTI (29–30 Aug 2026)

Every request, rejection, problem, and upgrade from the opening-page / hosting / sign-in / Canvas thread. Written so a supervisor can read the chat without the chat.

Related: [`project_journey.md`](project_journey.md) (Phase 10), [`product_overview.md`](product_overview.md), [`backend/README.md`](../backend/README.md).

---

## How to use this

- **Supervisor / IT:** jump to [Open items for AUI IT](#open-items-for-aui-it) and the [ready Microsoft email](#ready-email-supervisor--aui-it).
- **Defense:** the product claims that changed, and what is still waiting on campus credentials.
- **Us:** do not re-litigate rejected designs; they are listed under **Rejected**.

---

## Open items for AUI IT

These are **not** code gaps. The product is wired; campus credentials are missing.

### 1. Microsoft Entra ID (AUI sign-in)

Sign in already opens `login.microsoftonline.com` on tenant `7025e04c-70ca-48bf-ab7b-73954cb846ad` (the same picker as a normal AUI Microsoft login). Microsoft then rejects the app until an **App registration** exists.

Ask IT for:

1. **Application (client) ID**
2. **Client secret** (the secret *value*, plus expiry)
3. **Redirect URI** registered as **Web**, exactly:

```
http://127.0.0.1:8000/auth/microsoft/callback
```

After hosting, add a second URI on the **same** app:

```
https://YOUR-REAL-DOMAIN/auth/microsoft/callback
```

That URL is the **API callback**, not the landing page.

Settings: this organization only; delegated `openid` `profile` `email`; `@aui.ma` only.

Env once IT replies: `OFFICEHOURS_MS_TENANT_ID` (already known), `OFFICEHOURS_MS_CLIENT_ID`, `OFFICEHOURS_MS_CLIENT_SECRET`, `OFFICEHOURS_MS_REDIRECT_URI`, `OFFICEHOURS_FRONTEND_URL`.

Until then the picker works and the app fails with **AADSTS700038** (placeholder client id).

### 2. Canvas LTI 1.3 + API token

Code for signed LTI is in (`/lti/login`, `/lti/launch`, `/lti/config`). A real button **inside AUI Canvas** needs:

- LTI 1.3 developer key (issuer e.g. `https://canvas.aui.ma`, client id)
- Tool installed on the course (OIDC initiation `/lti/login`, launch `/lti/launch`, privacy **Public** so email is sent)
- `CANVAS_BASE_URL` + `CANVAS_ACCESS_TOKEN` so Rooms chapters and the agent read **that course’s modules**, not the local demo mirror

Until then: `OFFICEHOURS_DEMO=true` keeps `/canvas-demo` and the unsigned simulator for FYP walkthroughs. Off-demo, those routes are hidden.

---

## Ready email (supervisor → AUI IT)

**Subject:** App registration for OfficeHours (AUI Microsoft sign-in)

Please create an Entra ID App registration in the AUI tenant for our campus product OfficeHours.

- Name: OfficeHours
- Supported accounts: This organizational directory only (Al Akhawayn University)
- Platform: Web
- Redirect URI (development): `http://127.0.0.1:8000/auth/microsoft/callback`
- We will send a production `https://…/auth/microsoft/callback` as soon as the site is hosted — please add it to the same app
- API permissions (delegated): `openid`, `profile`, `email`
- Please admin-consent those permissions for the tenant

Please reply with: Application (client) ID, a client secret value (and expiry), and confirmation the redirect URI is registered exactly as above.

A second email (or the same ticket) can request the Canvas LTI 1.3 developer key and a Canvas API token. URLs to paste are on `GET /lti/config` once `OFFICEHOURS_LTI_ISSUER` + `OFFICEHOURS_LTI_CLIENT_ID` are set. See [`backend/README.md`](../backend/README.md).

---

## Chronological chit-chat

Dates are 29–30 August 2026. Quotes are paraphrased to the request, not a raw transcript.

### 1. “The copy is about the agent. It should be about community.”

**Asked:** Headline must be how students **get** help and **give** it. Study Rooms, Stack Overflow–style peer rating (Hilbert ŵ), choice at every level (human or AI, anonymous or named, help or ignore). Shared stress, collective learning, mutual support. Agent is a footnote.

**Also asked:** The page is flat. Add a color gradient through sections (white → soft fade → deeper tone at sign-in) so scrolling feels inevitable.

**Shipped:** Community headline (“Choose how you get help. Choose how you give it.”), choice chips, interactive Rooms (vote / Express Interest / Ignore), cream→sage→forest wash. Agent moved to “one door.”

**Problem found in QA:** Ignore only swapped a label; the thread did not look passed. Fixed with grayscale + lower opacity.

**User then:** “show results.” Screenshots and a walkthrough of that gradient page were shown.

### 2. “That is definitely not what I wanted.”

**Asked, specifically:**

- Remove gradients. Hard section breaks (solid color blocks / chapter bands). Not fades.
- Hero must be **rich**, not minimal. Illustrate a stressed student **alone**, then the **same** student relieved with peers.
- Illustrate choice: anonymous + named; human help + AI together; TA/professor **guiding**, not gatekeeping.
- Feel alive: icons, characters, scenes.
- Section breaks like chapter cuts, not continuous scroll effects.

**Rejected here:** the progressive gradient (they had just approved the *story*, not the wash). Agent-first headlines from earlier iterations. BeHive-shaped clones and the live Three.js courtyard (rejected in earlier turns on the same opening).

**Shipped:** Comic-style hero panels (2:13 AM alone → 2:31 AM shared); three drawn choice cards (dashed Request #204 vs named Sara; TA + robot; professor pointing to an open door); forest **01–05** cut bands; solid cream / white / lime / forest blocks; professor copy “A guide with a stamp.” Trio moved to its own chapter.

**User then:** “APPROVED.”

### 3. “Is this layout ready to host?”

**Answer we gave (still true):**

| Ready | Not ready if you host today |
| --- | --- |
| Opening verified desktop + 390px; guest `/` needs no API | `.env` baked `VITE_API_BASE=http://127.0.0.1:8000` — hosted login would call the visitor’s machine |
| Bundle does not include Three.js | `/canvas-demo` and `/demo/*` were public impersonation / design experiments (later gated) |
| SPA catch-all in the app | Host must rewrite all paths to `index.html` |
| | No favicon / Open Graph share card |
| | `OFFICEHOURS_DEMO` + `aui-demo` must be off on a community URL |
| | CI was red on `npm audit` / `nanoid` (not a product bug — later fixed) |

### 4. “What are we using for Sign in?” (Microsoft screenshots)

**User showed:** AUI-branded Microsoft account picker at  
`login.microsoftonline.com/7025e04c-70ca-48bf-ab7b-73954cb846ad/oauth2/v2.0/authorize`  
with `S.Abssi@aui.ma`.

**What the app was using then:** email + password (`POST /auth/login`) and demo accounts. **Not** Microsoft.

**Shipped:** Microsoft Entra ID authorization-code flow.

- `GET /auth/microsoft/login` → AUI tenant picker
- `GET /auth/microsoft/callback` → validate `id_token` (audience, tenant, `@aui.ma`), create user (no usable password), mint session, redirect `/sso#token=`
- Login page shows “Sign in with your AUI Microsoft account” when env vars are set

**What we tested:**

- Button appears; click hits the **correct AUI tenant**
- Microsoft error **AADSTS700038** with placeholder client id `00000000-…` (expected)
- `/sso#token=…` completion works (demo session → Sara’s student workspace)
- Backend tests: domain/audience/state guards, first-time user, no password login for SSO accounts

**What we did not test:** a full “pick Sophia → land in OfficeHours” click. That needs the three IT values.

### 5. “How do I request those three? After hosting?”

**Answer:** Request **now**. Hosting is only a second redirect URI on the same app. Azure allows multiple URIs. Localhost first; production URL later.

### 6. “Add this in Issues for my supervisor.”

**Tried:** `gh issue create` — GitHub token here cannot create issues (`createIssue` 403).

**Gave:** prefilled [New issue](https://github.com/abssisophia9-hub/officehours-ai/issues/new) body (title + IT email). If that link was never submitted, this file **is** the issue text. Supervisor can still send the email above.

### 7. “What’s left? The Canvas link works, right?”

**Honest split:**

- **Works:** `/canvas-demo` stand-in → `POST /canvas/launch` → provision → workspace. Opening “Or open from Canvas” was this demo.
- **Does not work yet as a campus claim:** a button **inside real AUI Canvas**. LTI 1.3 was not implemented then. Sync used a **local module mirror** unless `CANVAS_BASE_URL` + token were set.

### 8. “Work on real Canvas: LTI 1.3, live modules, hide /canvas-demo and /demo/*.”

**Shipped:**

- Signed LTI 1.3 OIDC (`/lti/login`, `/lti/launch`, `/lti/jwks`, `/lti/config`)
- Role map: Learner / TeachingAssistant / Instructor
- Launch lands `/sso#token=…&course=`
- Live Canvas listings follow `Link: rel=next`
- `OFFICEHOURS_DEMO=false`: unsigned `POST /canvas/launch` is **404**; SPA does not register `/canvas-demo` or `/demo/*`; opening CTA is text, not a simulator link

**Tests:** 149 backend tests after this work (LTI login redirect, signed student launch, instructor/TA map, bad issuer/state, unsigned launch hidden).

**Still needs IT:** developer key + API token (see open items).

### 9. “Why hasn’t the opening PR merged? We approved it.”

**Causes (not the page):**

1. PR #78 was still a **draft** (iteration default). Marked ready.
2. Red X = four frontend jobs failing `npm audit` on `nanoid < 3.3.18`. Backend tests green. Not a landing-page regression.

**User then:** “merge, and did you test Microsoft?”

**Done:** #78 merged to `main` (`9163274`). Microsoft answer: wiring tested; real AUI account completion not possible without the app registration.

### 10. “Fix housekeeping: npm audit / nanoid, unused three / recharts.”

**Shipped:**

- `nanoid` pinned to **3.3.18** in student-kiosk, professor-dashboard, ta-dashboard, officehours-app. Local `npm audit --audit-level=moderate` = 0 vulnerabilities. All four apps still build.
- Removed unused `three`, `@react-three/fiber`, `recharts` from the **unified** app. Deleted dead `CampusCanvas.jsx` / `helpPath.js`. Professor dashboard **keeps** Recharts (charts).

### 11. “Document every upgrade / problem / improvement. Every chit-chat.”

**This file.** Plus Phase 10 in [`project_journey.md`](project_journey.md).

---

## Rejected (do not bring back)

| Idea | Why it died |
| --- | --- |
| Live Three.js Ifrane courtyard as `/` | “This is not the frontend vision.” |
| BeHive-shaped page (ticker, 4-step path, numbers footer) | Inspiration ≠ copy-paste |
| Agent / Canvas as the **headline** | Community and choice are the story |
| Progressive page gradient | User asked for **hard chapter cuts**, not fades |
| Hosting before the Microsoft IT ticket | Register localhost now; add production URI later |
| Claiming real Canvas LTI before this upgrade | Was unsigned `/canvas-demo` only |
| Creating a GitHub Issue from this agent | Token has no `issues: write` |

---

## Improvements shipped (code)

| Area | What changed |
| --- | --- |
| Opening | Community headline; illustrated alone→together; choice scenes; hard 01–05 cuts; Sign in stays in the header |
| Microsoft | Entra ID SSO path + `/sso` handoff |
| Canvas | LTI 1.3 + live pagination + demo routes off when not `OFFICEHOURS_DEMO` |
| CI / deps | nanoid 3.3.18; drop unused 3D/charts from unified app |
| Docs | This log; journey Phase 10; README LTI + Microsoft env |

---

## Problems we hit (and what we did)

| Problem | What we did |
| --- | --- |
| Ignore on the Room thread looked like a label-only toggle | Dim + grayscale the card |
| Hero felt empty under a 100vh min-height | Dropped full-viewport hero; panels flex taller |
| Microsoft “tested” vs “works for Sophia” | Documented the placeholder client id; do not claim E2E AUI login |
| GitHub Issues API 403 | Prefilled issue URL + this log |
| Unsigned Canvas launch on a public host | 404 unless demo (or a launch secret) |
| CI red on nanoid | Pin 3.3.18 in all four lockfiles |
| Unused Three.js still in `package.json` after courtyard rejected | Uninstall + delete dead files |
| `sentence_transformers` import at app load in a thin venv | Install CPU torch + package for local tests (not a product change) |

---

## Git / PRs (this thread)

| | |
| --- | --- |
| Opening + Microsoft | PR **#78**, merged `main` `9163274` |
| LTI 1.3 + hide demos + housekeeping | Branch `cursor/canvas-lti13-live-54c7` (follow-on PR) |

---

## What a supervisor can claim vs cannot

**Can:** The opening is an illustrated campus-community story. Sign in is designed for AUI Microsoft accounts. Canvas can launch the product via LTI 1.3 once IT installs the tool. Demo mode still has a local Canvas stand-in.

**Cannot yet:** “Students already sign in with their AUI Microsoft account on the hosted site” (no app registration). “OfficeHours is a button inside live AUI Canvas reading live modules” (no developer key / API token on a community deploy).
