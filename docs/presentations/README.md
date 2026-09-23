# Presentations

| File | Use |
| --- | --- |
| [`fyp_infographic/OfficeHours_AI_Catalog_Poster.pdf`](fyp_infographic/OfficeHours_AI_Catalog_Poster.pdf) | **SSE catalog poster** — official 14.5×19 template |
| [`fyp_infographic/README.md`](fyp_infographic/README.md) | Rebuild notes + 60-second pitch |

---

# Supervisor proposal — Vision + live demos

| File | Use |
| --- | --- |
| [`supervisor_vision_proposal.pptx`](supervisor_vision_proposal.pptx) | **Use this** for the supervisor meeting |
| [`supervisor_technical_briefing.pptx`](supervisor_technical_briefing.pptx) | Same deck (compat filename) |

```bash
python3 scripts/generate_supervisor_briefing_pptx.py
```

**Download:**  
https://github.com/abssisophia9-hub/officehours-ai/raw/cursor/supervisor-pitch-deck-abbe/docs/presentations/supervisor_vision_proposal.pptx

---

## The Vision (say this without notes)

> OfficeHours is the Canvas-linked course help desk: students get Quiet ask and peer Rooms, TAs get a triaged desk with Help Coach, and professors stamp the only answers the Study Agent may give — so help is fast without inventing the syllabus.

- **What:** one multi-role course help desk  
- **Who:** students, TAs, professors in a Canvas course  
- **Why this:** help without inventing the syllabus  

**Says no to:** campus ChatGPT · auto-publish FAQ · three URL demos · portal scraping · TAs as classmates in the section they staff  

---

## Meeting arc

| Beat | Point |
| --- | --- |
| **Discovery** | I was a TA → I felt the gap → that gap is my **Bet** |
| **Vision** | Makes the build **SHARED** with supervisor + second reader |
| **Demo** | Literally run student → TA → professor |

---

## Live demo (password `aui-demo`)

```bash
./scripts/run_product.sh
# → http://127.0.0.1:5180
```

| Seat | Account | Show |
| --- | --- | --- |
| Student | `s.elidrissi@aui.ma` | Quiet ask · Ask Triage · Study Agent refuse · Rooms |
| TA | `a.chen@aui.ma` · CSC 2302 | Desk · claim · Help Coach · reply / group meeting |
| Professor | `a.benali@aui.ma` | Clusters · stamp KB · Canvas sync · agent after stamp |

Full script: [`demo/demo_script.md`](../../demo/demo_script.md)
