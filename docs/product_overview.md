# Product overview — what is the final product?

## Short answer

Your FYP product is a **campus web triage system** for AUI office hours:

- students use a **kiosk/browser page**
- TAs use a **browser dashboard**
- the professor uses a **browser dashboard**
- one **FastAPI backend** runs **custom-trained Oracle agents**

It is **not** (today) a published desktop app with App Store installers or AUI SSO login.

## What users actually open

| Role | What they open | Typical device |
| --- | --- | --- |
| Student | Student kiosk web app | Shared hallway tablet / laptop kiosk, or personal laptop browser |
| TA | TA dashboard web app | Desktop browser during office hours |
| Professor | Professor dashboard web app | Desktop browser |

All three talk to the same backend (`http://…:8000`). In development:

- kiosk → `http://127.0.0.1:5173`
- professor → `http://127.0.0.1:5174`
- TA → `http://127.0.0.1:5175`

## What “publish” means for this FYP

For demo day / evaluation, “publishing” usually means:

1. Run the backend on a campus laptop or small server
2. Serve the three Vite builds (or run `npm run dev`) on the LAN
3. Point kiosk tablets / staff browsers at those URLs
4. Optionally put the kiosk in fullscreen for a hardware prototype feel

Future production hardening (out of current MVP scope) could add:

- AUI SSO / role-based login
- HTTPS reverse proxy
- Postgres instead of SQLite
- hosted deployment (university VM / cloud)

## What the AI is allowed to do

Oracle agents **draft and triage**. They do **not** auto-publish answers to students.

Publication gate:

`TA resolve → pending_review → professor approve → student KB agent`

That human-in-the-loop design is intentional for ethics + FYP grading.

## Branding

UI is AUI-branded (official logo asset + Ifrane-inspired forest/sand glass theme) across all three apps.
