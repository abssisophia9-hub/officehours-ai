# Demo Script — OfficeHours AI (unified product)

Primary path for supervisors and FYP demos. Vocabulary:
[`docs/glossary.md`](../docs/glossary.md).

## Setup

1. Seed the backend (optional if you want a fuller queue):
   ```bash
   cd backend
   python3 scripts/seed_demo_data.py --reset --limit 20
   ```
2. Start the product stack:
   ```bash
   ./scripts/run_product.sh
   ```
   Or separately: backend `:8000` + `frontend/officehours-app` `:5180`.
3. Open **one** browser window: http://127.0.0.1:5180  
   Password for all seeded accounts: **`aui-demo`**.

> **Legacy (optional):** the mid-report two-app flow (student-kiosk `:5173` +
> professor-dashboard `:5174`) still works for hardware / historical captures.
> Prefer this script for current demos.

## Script

1. **Student** — sign in as `s.elidrissi@aui.ma`  
   Quiet ask or Identify me → message / face-to-face / online → submit  
   Show **Ask Triage** breakdown (Analyzer / Matcher / hint) and request code status.
2. **TA (+ student)** — `a.chen@aui.ma` on CSC 2302  
   Claim → start helping → **Help Coach** draft / Socratic → Reply or propose a
   **shared group meeting** for a repeated cluster. Switch course picker to a
   student course to show dual role.
3. **Professor** — `a.benali@aui.ma`  
   Clusters / recommendations → approve KB → optional Canvas sync / materials.
4. Optional: `/canvas-demo` → launch as Karim (TA in one course, student in another).

## Talking points

- Role is **per course** (TA can also be a student)
- Ask Triage at intake; Help Coach while helping; professor gates Study Agent KB
- Face-to-face ≠ typed reply; repeats → group meeting / FAQ, not broadcast chat
- Anonymity option remains; identified asks enable follow-up
