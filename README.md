# Artefact — *Why Is It So Hard to Localize Bugs in MCP Pipelines?*

Artefact package accompanying the manuscript *Why Is It So Hard to Localize Bugs in MCP
Pipelines? An Empirical Study with a Reproducible Fault-Injection Benchmark*. It contains the five
things the manuscript promises in its data-availability statement, and nothing else:

| # | What the paper promises | Where it is |
|---|---|---|
| 1 | Issue-screening workbook over all 1,343 pure issues | `data/screening_1343.csv`, `data/screening_funnel.csv` |
| 1a | The same pull, raw, exactly as the GitHub API returned it (1,373 issues, 14 API fields, no analysis columns) | `data/gh_issues_raw_2026-11-09.xlsx` |
| 2 | The live dataset: 339 rows | `data/active_bugs_339.csv`, `data/evidence_class_339.csv` |
| 3 | The 72 reproduction scripts and the output captured from each run | `repro/runner/`, `repro/captures/`, `repro/transcripts/` |
| 4 | Per-bug evidence classification | `data/evidence_class_339.csv`, `repro/evidence_matrix.csv`, `data/blocking_gaps_83.csv` |
| 5 | LLM prompts and raw answers | `llm/prompts.md`, `llm/outputs/` |
| 6 | A script that recomputes every number in the paper | `scripts/verify_numbers.py` |

Nothing here is synthetic. Every row is traceable to a public GitHub issue in
`modelcontextprotocol/python-sdk`, a run that was actually executed, or a model response that was
actually returned.

---

## 1. Quick start (60 seconds)

You need Python 3.9+. No third-party package is required for verification.

```bash
git clone <this-repo> mcp-artefacts && cd mcp-artefacts
python scripts/verify_numbers.py
```

The script recomputes **every dataset-level number in the paper** from the files in this repository
and prints each value next to the one printed in the manuscript — 98 checks, all of which should
read `ok`. The last line reads `All checks passed ...` if the artefact and the paper agree.

If you only want to look at one thing, open `data/active_bugs_339.csv` in Excel or pandas and
filter the column `reproduction_status`.

---

## 2. What is in each file

### 2.1 Screening (`data/`)

`data/screening_1343.csv` — one row per issue in the mined pool (all issues of
`modelcontextprotocol/python-sdk`, pull requests excluded): issue number, title, state, creation
date, the keyword-screen label, the URL and the first 800 characters of the report body. The
keyword label takes one of six values: `BUG`, `QUESTION`, `OTHER`, `FEATURE`, `CI/REFACTOR`, `DOC`.

`data/screening_funnel.csv` — the seven-stage funnel from 1,343 mined issues down to 339 analysed
bugs, with the count at each stage and the rule applied. Stages 3→4→5 are auditable: 398 confirmed
reports minus 59 that already behave correctly on the pinned SDK (`mcp 2.2.0`) gives the 339 bugs
the paper analyses.

`data/gh_issues_raw_2026-11-09.xlsx` — the raw pull, before any screening or labelling: every
field the GitHub API returned for the repository, unmodified apart from comment bodies being
truncated. Useful if you want to redo the screening from scratch rather than audit ours.

### 2.2 Live dataset (`data/active_bugs_339.csv`, `data/evidence_class_339.csv`)

One row per bug, 25 columns. The columns that matter for the paper:

| column | meaning |
|---|---|
| `issue` | GitHub issue number (`#123`) — every row is a real, public report |
| `origin_layer` | the layer where the defect **originates**: `Host`, `Client`, `Server`, `Transport`, or `multi` (one bug needs two changes) |
| `exposure_channel_raw` | what the SDK actually shows the developer: one of six evidence classes, or `not_exercised_not_inferable` when the bug could not be run |
| `evidence_tier` | `A` names the file and the exception, `B` gives a generic message, `C` names only the neighbouring layer, `D` gives no usable error |
| `reproduction_status` | `reproduced` / `not_reproduced__error_text_present` / `not_reproduced__no_error_text` |
| `not_reproduced_reason` | for the 267: the concrete obstacle that blocked reproduction |
| `observed_output` | for the 72: the return value or exception the run actually produced |
| `analyst_note`, `defect_description` | the analyst's free-text note for that bug (Chinese; see §5) |

`data/evidence_class_339.csv` is the compact per-bug classification: issue, origin layer, evidence
class, evidence tier, and the one-line reason for the class.

### 2.3 Reproduction (`repro/`)

`repro/runner/` — the harness and the case definitions:

* `repro_cases.py` / `repro_cases_b14.py` — one `Case(...)` per bug: which tool call to make, with
  which arguments, and a `builder` that stands up a server mirroring the reported defect.
* `repro_framework.py` — starts the server over Streamable HTTP with uvicorn, connects with the
  official client, invokes the tool and captures whatever comes back (return object or exception).
* `run_real_http.py`, `run_real_http2.py` — transport-level and interactive replays.
* `capture_with_server_log.py` — one bug, client result plus server traceback.

`repro/captures/issue_XXXX.txt` — **one file per reproduced bug** (72 files). Each is a
self-contained record: the trigger that was run, what the reporter described, the output that was
captured, the layer analysis, and a provenance table saying where each field came from. This is the
"captured console output" the paper refers to: section 3 holds exactly what the client saw.

`repro/transcripts/issue_XXXX.txt` — the **40 bugs whose run kept a Python traceback**, one file
each, body verbatim, all 40 complete. Where the file opens with `CLIENT ->` / `SERVER !!` /
`CLIENT <-` it shows the request, the exception the server caught, and the result the client
received. In many of the 40 the frames point at a different layer than the message the caller saw,
which is the phenomenon this study measures.

`repro/evidence_matrix.csv` — one row per reproduced bug answering the two questions a reviewer
asks first: *what exactly did you capture* (`text_shape`, `stack_frames`, `body_lines`, plus the
path to the capture and, where one exists, the run log) and *is anything missing* (`gap_reason`).
21 of the 59 non-silent bugs have no stack trace: 13 exception-type cases where the exception was
raised in the client or at the HTTP boundary, and 8 wrong-result cases where no exception exists.

`repro/README.md` — how to read a case, worked example included.

### 2.4 LLM experiments (`llm/`)

`llm/prompts.md` — the prompts, verbatim, with model, temperature and decoding parameters.

`llm/outputs/studyA_arms_72.json` — Study A: three arms (`baseline`, `ruleclue`, `analyst`) over
the 72 reproduced bugs, each with the predicted layer, the ranked layers and the raw scores.

`llm/outputs/studyB_247.jsonl` — Study B: one JSON object per bug (247 bugs), with the issue text
that was shown to the model, the model's JSON answer, and the true layer joined in.

`llm/outputs/studyB_scores_247.csv` — the same, flattened to one row per bug for counting:
`true_origin_layer`, `model_reporter_claim`, `model_origin_layer`, `correct`.

`llm/outputs/clues_72.json` — the six fixed, layer-blind guidance paragraphs used by the `ruleclue`
arm, one per evidence class.

`llm/run_llm_labelling.py` — a self-contained reference implementation of the labelling call
(OpenAI-compatible endpoint, `temperature=0`), so the experiment can be re-run on another model.

---

## 3. Mapping the artefact to the paper

| Paper claim | Value | Produced by |
|---|---|---|
| Mined issues | 1,343 | `data/screening_1343.csv` (row count) |
| Confirmed reports / removed / active | 398 / 59 / 339 | `data/screening_funnel.csv` |
| Origin layer split of the 339 | Transport 105, Server 98, Client 84, Host 51, multi 1 | `origin_layer` |
| Reproduced at runtime | 72 (Server 38 / Client 21 / Host 5 / Transport 8) | `reproduction_status` |
| Not reproduced | 267 = 184 with an analysable error + 83 without | `reproduction_status` |
| Evidence classes on the 72 | 8 / 13 / 18 / 18 / 12 / 3 | `exposure_channel_raw` |
| Evidence tiers on the 339 | A 181 / B 66 / C 25 / D 67 | `evidence_tier` |
| Why 83 evidence-poor reports are blocked | 16 / 7 / 14 / 15 / 9 / 19 / 3 | `data/blocking_gaps_83.csv` |
| Study A, baseline | 41/72 = 56.9 %, non-Server 3/34 = 8.8 % | `llm/outputs/studyA_arms_72.json` |
| Study A, rule-based clue | 46/72 = 63.9 %, non-Server 8/34 = 23.5 % | same |
| Study B, issue text only | 119/247 = 48.2 %, non-Server 51/172 = 29.7 % | `llm/outputs/studyB_scores_247.csv` |

---

## 4. Re-running the reproduction harness

The harness targets the SDK build the study was run on (`mcp 2.2.0`, Streamable HTTP transport,
CPython 3.12, Linux x86-64). It is included so that the trigger for each bug is inspectable, not
because every case is portable: several cases depend on a specific internal module layout or on a
third-party package that the reported bug itself is about.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt                     # mcp==2.2.0, uvicorn, pydantic, httpx
python -m repro.runner.repro_framework --only 234   # replay one case
python -m repro.runner.repro_framework --batch 1    # replay a batch
```

The framework prints the same three things the captures record: the return object, whether
`is_error` was set, and any exception that escaped. Two cautions:

* Cases whose defect lives in the **client or host application** (Claude Desktop, the Inspector,
  VS Code, Jupyter) need that application; the harness records them as `not_exercised` rather than
  simulating a pass.
* Cases marked `env/transport-config` need a transport variant (stdio, SSE, a reverse proxy, a
  mounted sub-path) that the single Streamable-HTTP replay does not exercise. They are the largest
  single reason a bug is not reproduced, and `not_reproduced_reason` says so per bug.

---

## 5. Known limitations of the released files

1. **Free-text analyst notes are in Chinese.** The fields `defect_description`, `analyst_note`,
   `observed_output` and `not_reproduced_reason` were written by the analysts during the study and
   are released unedited apart from redaction. Every machine-readable label they support
   (`origin_layer`, `exposure_channel_raw`, `evidence_tier`, `reproduction_status`) is in English.
2. **Issue bodies are truncated.** Reports are capped at 800 characters (screening table) and
   6,000 characters (live dataset); the model input in Study B at 4,000 characters. The full text
   is one click away at the URL in each row, and `data/gh_issues_raw_2026-11-09.xlsx` carries the
   raw bodies as returned by the API.
3. **A stack trace exists for 40 of the 72, and all 40 are complete.** The MCP server turns a tool
   exception into a `TextContent` error, so the frames stay in the server's stderr and only the
   message reaches the client. The remaining 32 are silent cases, client-side raises, returned
   errors and wrong results, where a server traceback does not exist; `repro/evidence_matrix.csv`
   records the reason for each of them in `gap_reason`.
4. **Capture headers cite internal paths.** A capture may name the harness entry that produced it,
   and occasionally a console dump or raw payload file. Those internal dumps are not part of this
   release; the text used for coding is reproduced in section 3 of the same capture.
5. **Redaction.** Local filesystem paths and the analysts' user names were replaced with `<user>` /
   `<python-env>` so that the artefact cannot identify its authors. Nothing else was changed.

---

## 6. Licence and redaction

Code (`repro/`, `llm/*.py`, `scripts/`) — MIT, see `LICENSE`.
Data and documentation (`data/`, `llm/outputs/`) — CC BY 4.0, see `LICENSE-DATA`.
The underlying issue text belongs to its authors on GitHub and is reproduced here under the GitHub
Terms of Service for the purpose of review.

The authors' identity is not concealed by this repository. A permanent DOI will be minted after
acceptance.
