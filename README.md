# Review artefact — *Why Is It So Hard to Localize Bugs in MCP Pipelines?*

Artefact package accompanying the manuscript *Why Is It So Hard to Localize Bugs in MCP
Pipelines?*, released under the authors' GitHub account. It contains the five things the manuscript
promises in its data-availability statement:

| # | What the paper promises | Where it is |
|---|---|---|
| 1 | Screening record of all 1,343 mined issues | `data/screening_1343.csv`, `data/screening_funnel.csv` |
| 2 | The active dataset of 339 real bugs, with labels | `data/active_bugs_339.csv`, `data/evidence_class_339.csv` |
| 3 | Reproduction scripts + the output captured from each of the 72 runs | `repro/runner/`, `repro/run_output/`, `repro/captures/`, `repro/transcripts/` |
| 4 | Per-bug evidence classification | `data/evidence_class_339.csv`, `data/blocking_gaps_83.csv` |
| 5 | LLM prompts and raw model output | `llm/prompts.md`, `llm/outputs/` |

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

The script recomputes **every number in the paper** from the files in this repository and prints
them next to the value printed in the manuscript — 102 checks, all of which should read `ok`.
The last line reads `All checks passed ...` if the artefact and the paper agree.

If you only want to look at one thing, open `data/active_bugs_339.csv` in Excel or pandas and
filter the column `reproduction_status`.

---

## 2. What is in each file

### 2.1 Screening (`data/`)

`data/screening_1343.csv` — one row per issue in the mined pool (all issues of
`modelcontextprotocol/python-sdk`, pull requests excluded), with the issue number, title, state,
creation date, the keyword-screen label, the URL and the first 800 characters of the report body.
The keyword label takes one of six values: `BUG`, `QUESTION`, `OTHER`, `FEATURE`, `CI/REFACTOR`,
`DOC`.

`data/screening_funnel.csv` — the seven-stage funnel from 1,343 mined issues down to 339 analysed
bugs, with the count at each stage and the rule applied. Stages 3→4→5 are auditable: 398 confirmed
reports minus 59 that already behave correctly on the pinned SDK (`mcp 2.2.0`) gives the 339 bugs
the paper analyses.

### 2.2 Active dataset (`data/active_bugs_339.csv`)

One row per bug, 26 columns. The columns that matter for the paper:

| column | meaning |
|---|---|
| `issue` | GitHub issue number (`#123`) — every row is a real, public report |
| `origin_layer` | the layer where the defect **originates**: `Host`, `Client`, `Server`, `Transport`, or `multi` (one bug needs two changes) |
| `exposure_channel_raw` | what the SDK actually shows the developer: one of six evidence classes, or `not_exercised_not_inferable` when the bug could not be run |
| `evidence_tier` | `A` names the file and the exception, `B` gives a generic message, `C` names only the neighbouring layer, `D` gives no usable error |
| `reproduction_status` | `reproduced` / `not_reproduced__error_text_present` / `not_reproduced__no_error_text` |
| `not_reproduced_reason` | for the 267: the concrete obstacle that blocked reproduction |
| `observed_output` | for the 72: the return value or exception the run actually produced |
| `analyst_note`, `defect_description` | the analyst's free-text note for that bug (Chinese; see §6) |

Full column-by-column documentation: `docs/06_data_dictionary.md`.
The class definitions are in `docs/02_codebook.md`.

### 2.3 Reproduction (`repro/`)

`repro/runner/` — the harness and the case definitions:

* `repro_cases.py` / `repro_cases_b14.py` — one `Case(...)` per bug: which tool call to make, with
  which arguments, and a `builder` that stands up a server mirroring the reported defect.
* `repro_framework.py` — starts the server over Streamable HTTP with uvicorn, connects with the
  official client, invokes the tool and captures whatever comes back (return object or exception).
* `run_real_http.py`, `run_real_http2.py` — transport-level and interactive replays.

`repro/captures/issue_XXXX.txt` — **one file per reproduced bug** (72 files). Each is a
self-contained record: the trigger that was run, what the reporter described, the output that was
captured, the layer analysis, and a provenance table saying where each field came from. Sections
for the raw payload and the console dump appear only where the run kept one.

`repro/transcripts/issue_XXXX.txt` — **the 39 bugs that kept a complete Python traceback**, one file
each, body verbatim. Where the file opens with `CLIENT ->` / `SERVER !!` / `CLIENT <-` it shows the
request, the exception the server caught, and the result the client received. In many of the 39 the frames
point at a different layer than the message the caller saw, which is the phenomenon this study
measures. `repro/transcripts/README.md` explains the 40 that are not there. Start here if you
want to check one bug's evidence.

`repro/run_output/issue_XXXX.txt` — **one file per reproduced bug** (72 files), the shortest way to
see what a run actually printed. Six header lines say which harness ran, what kind of capture this
is, and where the text came from; the body is the output, verbatim. The header's `capture kind` is
the *source* of the text (a console log for 30, a traceback excerpt for 5, the client's return
payload for 37), not a claim about how complete it is: `text_shape` in `repro/evidence_matrix.csv`
is what says how much of the error each bug left behind. `repro/transcripts/` holds the **39
complete tracebacks**, and `evidence_matrix.csv` (column `transcript`) points at the file for each of them.
Paths and account names inside the text are redacted to `<user>` / `<python-env>`.

`repro/captures_index.csv` — one row per bug, saying which kinds of evidence exist for it
(trigger 72/72, error text 63, raw payload 54, console log 30). Read this before concluding that
something is missing: the four kinds were collected by different mechanisms at different times.

`repro/evidence_matrix.csv` — one row per reproduced bug answering the two questions a reviewer asks
first: *what exactly did you capture* (`text_shape`, `stack_frames`, the file paths) and *is anything
missing* (`gap_reason`). 21 of the 59 non-silent bugs have no stack trace: 13 exception-type cases
where the exception was raised in the client or at the HTTP boundary, and 8 wrong-result cases where
no exception exists. Rebuild it with `scripts/build_evidence_matrix.py`; the reasoning and the list
are in `docs/08_evidence_coverage.md`.

`repro/logs/` — the console dumps exactly as the harness wrote them (53 runs, 30 of them belonging
to the reproduced set; the rest are attempts that did not reproduce). The 12 files added last carry
a four-line provenance header naming the baseline harness they came from; the body below it is
unmodified apart from path redaction.

`repro/repro_verdicts_72.csv` — the verdict table: issue, origin layer, evidence class, evidence
tier, whether an error was raised or the call returned silently, and the path to the capture.

`repro/attempt_log.csv` — **all 350 attempts**, including the ones that failed, with the recorded
reason. This is the audit trail behind the claim that the 267 unreproduced bugs were attempted and
not asserted.

### 2.4 LLM experiments (`llm/`)

`llm/prompts.md` — the prompts, verbatim, with model, temperature and decoding parameters.

`llm/outputs/studyA_arms_72.json` — Study A: three arms (`baseline`, `ruleclue`, `analyst`) over
the 72 reproduced bugs, each with the predicted layer, the ranked layers and the raw scores.

`llm/outputs/studyB_247.jsonl` — Study B: one JSON object per bug (247 bugs), with the issue text
that was shown to the model, the model's JSON answer, and the true layer joined in.

`llm/outputs/studyB_scores_247.csv` — the same, flattened to one row per bug for counting:
`true_origin_layer`, `model_reporter_claim`, `model_origin_layer`, `correct`.

`llm/run_llm_labelling.py` — a self-contained reference implementation of the labelling call
(OpenAI-compatible endpoint, `temperature=0`), so the experiment can be re-run on another model.

### 2.5 Docs (`docs/`)

| file | content |
|---|---|
| `01_file_map.md` | this map, in one table, with file counts |
| `02_codebook.md` | the four layers, the six evidence classes, the four evidence tiers, the labelling rules |
| `03_screening_protocol.md` | how 1,343 → 439 → 398 → 339 was done, and what each stage can and cannot tell you |
| `04_reproduction_protocol.md` | environment, harness, what "reproduced" means, what was never claimed |
| `05_llm_experiments.md` | Study A and Study B designs, scoring, and the result tables |
| `06_data_dictionary.md` | every column of every released table |
| `07_results_snapshot.md` | all headline numbers in one page, each with the file that produces it |
| `08_evidence_coverage.md` | for the 72: what text was captured, what is missing, and why |

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
  single reason a bug is not reproduced, and the attempt log says so per bug.

---

## 5. How to cite the numbers

If you want to quote a number from this artefact, quote it together with the file it comes from,
e.g. *"119/247 = 48.2 % (`llm/outputs/studyB_scores_247.csv`)"*. Section `07_results_snapshot.md`
gives the full list.

---

## 6. Known limitations of the released files

1. **Free-text analyst notes are in Chinese.** The fields `defect_description`, `analyst_note`,
   `observed_output` and `not_reproduced_reason` were written by the analysts during the study and
   are released unedited apart from redaction. Every machine-readable label they support
   (`origin_layer`, `exposure_channel_raw`, `evidence_tier`, `reproduction_status`) is in English.
2. **Issue bodies are truncated.** Reports are capped at 800 characters (screening table) and
   6,000 characters (active dataset); the model input in Study B at 4,000 characters. The full text
   is one click away at the URL in each row.
3. **53 console logs, 30 of them for the 72, and 72 captures.** Every reproduced bug has a capture
   file and a run-output file, but the harness only started writing a separate console log partway
   through the study. Twelve of the richest transcripts were recovered from the baseline replay
   that preceded the repair experiment and are included here with a provenance header. For the
   other 42 bugs the output exists in the capture file, the run-output file and
   `repro/attempt_log.csv`, but no separate server-side transcript was kept.
4. **A stack trace exists for 40 of the 72, and 39 of those are complete.** The MCP server turns a
   tool exception into a `TextContent` error, so the frames stay in the server's stderr and only the
   message reaches the client. `repro/transcripts/` holds the 39 complete ones; the other one of the
   40 kept only a tail (#915). The remaining 32 are silent cases, client-side raises,
   returned errors and wrong results, where a server traceback does not exist.
   `docs/08_evidence_coverage.md` has the per-bug explanation.
5. **Redaction.** Local filesystem paths, the analysts' machine user names and e-mail addresses
   were replaced with `<user>` / `<email-redacted>` so that the artefact cannot identify its
   authors. Nothing else was changed.

---

## 7. Licence and redaction

Code (`repro/`, `llm/*.py`, `scripts/`) — MIT, see `LICENSE`.
Data and documentation (`data/`, `llm/outputs/`, `docs/`) — CC BY 4.0, see `LICENSE-DATA`.
The underlying issue text belongs to its authors on GitHub and is reproduced here under the
GitHub Terms of Service for the purpose of review.

Local machine paths and e-mail addresses found in captured tracebacks and issue text were redacted
before release; see `ANONYMITY.md` for the rules applied and a check a reader can re-run. The
authors' identity is not concealed by this repository. A permanent DOI will be minted after
acceptance.
