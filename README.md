# Review artefact — *Why Is It So Hard to Localize Bugs in MCP Pipelines?*

Anonymous artefact package submitted for double-blind review. It contains the five things the
manuscript promises in its data-availability statement:

| # | What the paper promises | Where it is |
|---|---|---|
| 1 | Screening record of all 1,343 mined issues | `data/screening_1343.csv`, `data/screening_funnel.csv` |
| 2 | The active dataset of 339 real bugs, with labels | `data/active_bugs_339.csv`, `data/evidence_class_339.csv` |
| 3 | Reproduction scripts + captured console output for the 72 reproduced bugs | `repro/runner/`, `repro/captures/`, `repro/logs/` |
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
them next to the value printed in the manuscript — 64 checks, all of which should read `ok`.
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

`repro/captures/issue_XXXX.txt` — **one file per reproduced bug** (72 files). Each has a short
header (origin layer, evidence class, transport, harness entry) followed by the captured return
value or exception, and, where the run also wrote one, the raw payload and the console log.

`repro/logs/` — the console logs exactly as the harness wrote them (41 runs, including runs that
did not reproduce the defect).

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
3. **41 console logs, 72 captures.** Every reproduced bug has a capture file, but the harness only
   started writing a separate console log partway through the study, so the older runs have their
   output recorded in the capture file and in `repro/attempt_log.csv` only.
4. **Redaction.** Local filesystem paths, the analysts' machine user names and e-mail addresses
   were replaced with `<user>` / `<email-redacted>` so that the artefact cannot identify its
   authors. Nothing else was changed.

---

## 7. Licence and anonymity

Code (`repro/`, `llm/*.py`, `scripts/`) — MIT, see `LICENSE`.
Data and documentation (`data/`, `llm/outputs/`, `docs/`) — CC BY 4.0, see `LICENSE-DATA`.
The underlying issue text belongs to its authors on GitHub and is reproduced here under the
GitHub Terms of Service for the purpose of review.

The repository was prepared so that it contains no author name, affiliation, grant number or local
path. See `ANONYMITY.md` for the checklist that was applied. A permanent DOI will be minted after
acceptance.
