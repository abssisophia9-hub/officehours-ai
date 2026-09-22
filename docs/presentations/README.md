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





---

## Capstone proposal poster (SSE template)

**Visuals first:** [`poster_visuals/`](poster_visuals/) — print-size PNGs. Open [`poster_visuals/index.html`](poster_visuals/index.html).

| File | Use |
| --- | --- |
| [`poster_visuals/V01`–`V10`](poster_visuals/) | Walk-up figures (architecture, agents, pipeline, gap, roles, stamp gate, roadmap, evaluation, demo vs live, QR) |
| [`poster_visuals/V11`–`V16`](poster_visuals/) | Full repo diagrams if a judge wants more detail |
| [`poster_visuals/walkup_board.html`](poster_visuals/walkup_board.html) | All figures on one board |
| [`OfficeHours_AI_Capstone_Poster.pdf`](OfficeHours_AI_Capstone_Poster.pdf) | One-page SSE poster with those figures |
| [`OfficeHours_AI_Capstone_Poster.docx`](OfficeHours_AI_Capstone_Poster.docx) | Word / print |

**Before print:** replace supervisor name. QR already links the GitHub repository.
