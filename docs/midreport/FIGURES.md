# Figures for the mid-term report

matplotlib is not installed. `python -c "import matplotlib"` raised
`ModuleNotFoundError` in this session. The figures are SVG from the standard
library. No dependency was added.

Rebuild them with:

```bash
backend/venv/bin/python docs/midreport/figures/build_figures.py
```

The script prints the 95% Wilson intervals it draws. Counts are the labels.
The intervals only show uncertainty on these small samples.

| Figure | File | Built from |
| --- | --- | --- |
| Architecture | `docs/midreport/figures/architecture.svg` | The call path in `backend/app/ai/agent_policy.py`, `backend/app/services/kb_agent_service.py`, and `backend/app/ai/gemini_client.py`. This is a diagram of the code, not a measurement. |
| Orchestration pipeline | `docs/midreport/figures/pipeline.svg` | The order in `run_study_agent`, with the defaults printed when the policy environment variables are unset. |
| Outcome states | `docs/midreport/figures/outcomes.svg` | The API strings in `agent_policy.py` and `kb_agent_service.py`, and the page sentence in `frontend/officehours-app/src/pages/StudentAgentPage.jsx`. |
| Retrieval-only versus with-check | `docs/midreport/figures/retrieval_vs_check.svg` | `docs/eval_results/baseline_retrieval_only_20261010T180847Z.json`, sentence-transformers, both filters, `correct/n` by category. `docs/eval_results/with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json`, harness `correct/n` by category. Whiskers are 95% Wilson intervals on those rates. The Gemini file was not re-run. |
| Threshold sweep | `docs/midreport/figures/threshold_sweep.svg` | The `threshold_sweep` array under sentence-transformers, `both_on`, in the same baseline file. The dashed line is the production cutoff 0.42. The script does not change that cutoff. |

Each SVG carries that source in its subtitle.

The retrieval figure uses the saved baseline even though this session re-ran
the baseline. The re-run matched those counts and the sweep, and the new JSON
was not kept. See `docs/midreport/EVIDENCE.md`.
