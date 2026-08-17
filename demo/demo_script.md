# Demo Script — OfficeHours AI (unified product)

Primary path for supervisors and FYP demos. Vocabulary:
[`docs/glossary.md`](../docs/glossary.md).

## Setup

1. Seed the backend (optional if you want a fuller Quiet-ask queue):
   ```bash
   export OFFICEHOURS_DEMO=true
   cd backend
   python3 scripts/seed_demo_data.py --reset --limit 20
   ```
2. Start the product stack:
   ```bash
   ./scripts/run_product.sh
   ```
   Community deploy uses `OFFICEHOURS_DEMO=false` + live Canvas instead of
   these seeded accounts.
3. Open **one** browser window: http://127.0.0.1:5180  
   Password for all seeded accounts: **`aui-demo`**.

> **Legacy (optional):** the mid-report two-app flow (student-kiosk `:5173` +
> professor-dashboard `:5174`) still works for hardware / historical captures.
> Prefer this script for current demos.

## Script

1. **Student** — sign in as `s.elidrissi@aui.ma`  
   Quiet ask or Identify me → message / face-to-face / online → submit  
   Show **Ask Triage** breakdown (Analyzer / Matcher / hint) and request code status.  
   Open **Rooms** (`CSC 3323`) → Create a Room (named) → chapter from the demo
   Canvas/syllabus grid → Express Interest / accept a solution → leaderboard.
2. **TA (+ student)** — `a.chen@aui.ma` on CSC 2302  
   Claim → start helping → **Help Coach** draft / Socratic → Reply or propose a
   **shared group meeting** for a repeated cluster. Switch course picker to a
   student course to show dual role.
3. **Professor** — `a.benali@aui.ma`  
   Clusters / recommendations → **review insights** (Rooms chapters + Quiet asks)
   → approve KB → optional Canvas sync / materials.
4. Optional: `/canvas-demo` → launch as Karim (TA in one course, student in another).

## Talking points

- Role is **per course** (TA can also be a student)
- Ask Triage at intake; Help Coach while helping; professor gates Study Agent KB
- **Rooms** are named classmate help (leaderboard); Quiet ask is anonymous to staff
- Chapters on deploy = Canvas modules, not a hardcoded CSC list
- Face-to-face ≠ typed reply; repeats → group meeting / FAQ, not broadcast chat
