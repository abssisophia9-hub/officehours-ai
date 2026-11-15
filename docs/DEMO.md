# Supervisor demo on this laptop

Verified on this machine on 10 Oct 2026:

- Ubuntu 24.04.4 LTS, x86_64
- Python 3.12.3 (`/usr/bin/python3`)
- Node v22.14.0, npm 10.9.7
- Git repo at the project root, `main` includes the study-agent slice and the evaluation

This session is that Ubuntu machine. If your laptop is Windows or macOS, use the same commands inside WSL or a terminal that can run `bash`. Do not install Node or Python system packages until you ask; everything below stays inside the project folder.

The product script is `./scripts/run_product.sh`. On Windows PowerShell use
`.\scripts\start-backend.ps1` and `.\scripts\start-frontend.ps1` from the
repo root (frontend script only runs `npm run dev`).

## Setup (once)

From the project root.

```bash
python3 --version
node --version
cd backend
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
venv/bin/pip install -r requirements.txt
venv/bin/python -c "import torch; print(torch.__version__, 'cuda', torch.cuda.is_available())"
cd ../frontend/officehours-app
npm ci
```

`torch.__version__` must end in `+cpu` and `cuda` must be `False`.

On this machine `backend/venv` was already present with `torch 2.14.1+cpu` and `pip check` reported no broken requirements. It was not deleted or reinstalled.

`npm ci` may print `EBADENGINE` because `react-router` asks for Node `>=22.22` and this machine has Node `22.14`. The app still installed and the page at http://127.0.0.1:5180 returned HTTP 200. Do not upgrade Node unless you decide to; that install would be outside the project folder.

## Warm up before the room

The first MiniLM use downloads `all-MiniLM-L6-v2` (about 90 MB) into `~/.cache/huggingface`. The terminal demo stalls on that download. The browser demo does not use MiniLM.

Run this once, the night before or while people are sitting down, from the project root:

```bash
backend/venv/bin/python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('all-MiniLM-L6-v2'); print(tuple(m.encode('warmup').shape))"
```

A good run prints a shape like `(384,)`. After that, the slice and the eval start in a few seconds.

What gets downloaded the first time, and only the first time:

| Download | When | About |
| --- | --- | --- |
| CPU PyTorch wheel | `pip install torch --index-url https://download.pytorch.org/whl/cpu` | Hundreds of MB. This is the step that avoids the multi-GB CUDA wheel. |
| `requirements.txt` | the next pip command | FastAPI, sentence-transformers, scikit-learn, pytest |
| `npm ci` | frontend folder | the product app |
| `all-MiniLM-L6-v2` | the warmup command, or the first slice/eval | about 90 MB under `~/.cache/huggingface` |

`./scripts/run_product.sh` sets `OFFICEHOURS_CLUSTERING_BACKEND=lexical`. The browser does not download MiniLM.

## One command: terminal slice

From the project root:

```bash
backend/venv/bin/python scripts/run_study_slice.py
```

A good run ends with both of these lines:

```text
Filtered (approved_only=true, course_scoped=true): 3/3 answered, 3/3 not found
Plain RAG (approved_only=false, course_scoped=false): 3/3 answered, 3/3 not found
```

Also expect:

- `Embedding backend: sentence-transformers`
- `Uploaded 4 chunk(s)` and `Approved 4 chunk(s) in one call`
- Citations `demo_kettle_notes.pdf, p. 1, chunk 1`, `p. 2, chunk 2`, and `p. 3, chunk 3`
- The three absent questions print `not found`
- Exit code 0

On this tiny PDF, plain mode matches filtered mode. The only file in that database is already approved, so turning the filters off has nothing extra to retrieve. The evaluation is the comparison that shows the filters.

## One command: evaluation

From the project root, after the warmup:

```bash
backend/venv/bin/python scripts/run_study_eval.py
```

A good run takes well under a minute once MiniLM is cached. It prints a long failure list, then a side-by-side table, and exits 0. The failure list is the measurement, not a crash.

Check these lines near the end:

- `human_written: 0 questions` and `(empty — not scored, not merged with agent_generated)`
- Both filters on, MiniLM: in_document correct `17/20`, hard_negative spurious_answer `11/20`, hidden_page_cited `0/20` and `0/10`
- Unapproved pages: `0/75` with both filters on, `13/75` with approval off, `0/75` with only the course filter off
- Other-course pages: `0/75` with both filters on, `0/75` with only approval off, `13/75` with the course filter off
- `sentence-transformers: the approval filter blocks unapproved pages`
- `sentence-transformers: the course filter blocks other-course pages`
- `separates=False` for both MiniLM and lexical
- A new file `docs/eval_results/baseline_retrieval_only_<timestamp>.json`

The 0.42 cutoff is not changed. `separates=False` means no cutoff on this set keeps every correct citation and rejects every hard negative.

## Browser demo

Start it only if ports 8000 and 5180 are free:

```bash
./scripts/run_product.sh
```

Open http://127.0.0.1:5180

Password for every demo account: `aui-demo`

| Who | Email | Course to click |
| --- | --- | --- |
| Sara, student | `s.elidrissi@aui.ma` | CSC 2302, role student |
| Alice, TA | `a.chen@aui.ma` | CSC 2302, role ta |
| Prof. Amine Benali | `a.benali@aui.ma` | CSC 2302, role professor |

The study agent from the student side, in this order:

1. Sign in as `a.benali@aui.ma`. On the opening page, choose **Sign in**. On **My Courses**, click the **CSC 2302** card whose pill says professor.
2. Scroll to **Upload files directly**. Choose `backend/demo_data/demo_kettle_notes.pdf`. Click **Upload to course KB**. The message should mention 4 chunks.
3. In **Knowledge Review**, click **Approve for student KB** on each of the four pending rows. The student agent sees nothing until those stamps exist. The terminal script approves all four in one call; the screen does it one row at a time.
4. Sign out. Sign in as `s.elidrissi@aui.ma`. Click the **CSC 2302** card whose pill says student.
5. Dismiss the “New here?” note if it appears. Click **Study Agent** (or scroll to **Ask stamped materials**).
6. Ask `How many mugs can the circular queue hold?` and click **Ask agent**. Expect eight mugs, and a citation of `demo_kettle_notes.pdf, p. 2`.
7. Ask `What is the chemical formula of sodium chloride?`. Expect the not-found text and the button **Turn this into a Quiet ask**.

Checked against the running app on this machine (`OFFICEHOURS_DEMO=true`, lexical, the same defaults as `run_product.sh`): after the upload and the four approvals, Sara’s mug question returned the page 2 chunk, and the salt question returned `should_seek_help: true`.

API: http://127.0.0.1:8000/health should show `"status":"healthy"` and `"demo":true`.

## Five-minute talk track

Say this while the output appears. Do not read the failure list line by line.

1. Slice, first lines. “This is a fresh database. I log in as the professor, upload a four-page demo PDF, and approve every chunk. Nothing here is a real syllabus.”
2. Filtered block. “With approval and the course filter on, three questions that are in the PDF are answered and cited with file, page, and chunk. Three questions that are not in the PDF come back not found. The agent does not guess.”
3. Plain block. “Same six questions with both filters off. On this one PDF the numbers match, because that file is already approved. The filter comparison is the next command.”
4. Eval, while the failure list scrolls. “Seventy-five questions, four filter settings, MiniLM and a lexical backend. A listed failure is a recorded miss. The run is fine if it reaches the table and exits 0.”
5. Hidden-page table. “Unapproved pages stay at 0 while the approval filter is on, and they show up when that filter is off. Other-course pages stay at 0 while the course filter is on, and they show up when that filter is off. Each filter blocks its own pages.”
6. Sweep. “From 0.30 to 0.70, no cutoff separates correct in-document citations from hard negatives. The answer cutoff is still 0.42. I am not changing it in front of you.”
7. Browser. “Same gate, with a person clicking. The professor stamps the PDF. Sara asks the mug question and gets page 2. She asks a chemistry question and the agent sends her to Quiet ask.”

## Troubleshooting from this run

**`address already in use` on port 8000, and Vite says `Port 5180 is in use`.** A product server was already running. A second `./scripts/run_product.sh` failed to bind 8000 and opened the app on 5181. Use the existing http://127.0.0.1:5180. Do not start a second copy. This happened in this session; the existing server was healthy.

**`torch` version does not end in `+cpu`, or `cuda` is `True`.** `sentence-transformers` pulled the CUDA wheel. Do not `pip install torch` from PyPI on top. Recreate the venv only if you mean to, then install the CPU wheel before `requirements.txt`, as in Setup.

**The slice or eval sits silent for a long time the first time.** MiniLM is downloading. Run the warmup command above. Later runs should take a few seconds (slice) or under a minute (eval). On this machine, after the model was cached, the slice finished in about 6 seconds and the eval in about 8 seconds.

**Tests print warnings.** `venv/bin/python -m pytest` from `backend/` passed here: **189 passed**. The warnings are a Starlette deprecation and a scikit-learn `L-BFGS-B` deprecation. They are not failures.

**`EBADENGINE` during `npm ci`.** Node on this machine is 22.14; `react-router` declares `>=22.22`. The dev server still served the app. No Node upgrade was installed.

**The eval “fails” because it lists many questions.** That list is expected. Success is exit code 0, `separates=False`, and the hidden-page counts above.

**The browser agent says it has no approved material.** The PDF was not stamped. Approve the four Knowledge Review rows, then ask again as Sara on CSC 2302. Asking before approval is the right “not yet” moment if you want to show the gate.

## Morning checklist

1. `git checkout main` and `git pull`.
2. `backend/venv/bin/python -c "import torch; print(torch.__version__)"` shows `+cpu`.
3. Run the MiniLM warmup command. Wait until it prints the vector shape.
4. Optional: `cd backend && venv/bin/python -m pytest -q` (about one minute, 189 passed here).
5. From the project root: `backend/venv/bin/python scripts/run_study_slice.py`. Look for `3/3 answered, 3/3 not found` twice.
6. `backend/venv/bin/python scripts/run_study_eval.py`. Look for `separates=False` and the approval/course sentences.
7. If http://127.0.0.1:5180 is not already open, run `./scripts/run_product.sh`.
8. Browser: professor stamps `demo_kettle_notes.pdf` on CSC 2302, then Sara asks the mug question and the salt question.
