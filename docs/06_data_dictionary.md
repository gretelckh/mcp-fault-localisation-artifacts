# Data dictionary

One section per released table. `n` is the number of data rows.

---

## `data/screening_1343.csv` (n = 1,343)

| column | type | meaning |
|---|---|---|
| `issue_number` | int | GitHub issue number |
| `title` | str | issue title, as written |
| `state` | str | `open` / `closed` at mining time |
| `created_at` | ISO 8601 | issue creation timestamp |
| `keyword_label` | enum | `BUG` / `QUESTION` / `OTHER` / `FEATURE` / `CI/REFACTOR` / `DOC` |
| `keyword_label_previous` | enum | the label the first pass of the screen gave, kept where the two disagree |
| `url` | str | `https://github.com/modelcontextprotocol/python-sdk/issues/<n>` |
| `body_excerpt_800_chars` | str | first 800 characters of the report body, redacted |

---

## `data/screening_funnel.csv` (n = 7)

| column | meaning |
|---|---|
| `stage` | 1–7 |
| `step` | what happens at this stage |
| `count` | how many issues remain |
| `note` | the rule applied, or the arithmetic that produces the count |

---

## `data/active_bugs_339.csv` (n = 339)

Index columns

| column | meaning |
|---|---|
| `seq` | row number in the released table, 1–339 |
| `case_id` | internal identifier `BUG-XXXX` |
| `issue` | GitHub issue number, e.g. `#76` — join key across every file |
| `url` | issue URL |
| `title` | issue title |
| `issue_state` | `open` / `closed` |
| `created_at` | issue creation timestamp |

Labels

| column | meaning |
|---|---|
| `origin_layer` | **ground truth**: `Host` / `Client` / `Server` / `Transport` / `multi`. Rules in `02_codebook.md` |
| `exposure_channel_raw` | evidence class: `pushed-to-Server` / `silent` / `caller-exception` / `single-layer-genericised` / `single-layer-correct` / `registration`, or `not_exercised_not_inferable` for the 267 |
| `label_source` | `expert` (hand-labelled) or `verified` (confirmed in the second pass) |
| `review_flag` | `Y` where a row was queued for a second review, empty otherwise |
| `evidence_tier` | `A` complete error, `B` fragment, `C` prose only, `D` no evidence |

Reproduction

| column | meaning |
|---|---|
| `reproduction_status` | `reproduced` / `not_reproduced__error_text_present` / `not_reproduced__no_error_text` |
| `evidence_source` | where the error evidence comes from: `运行时` (runtime capture) or the report body (`issue正文`) |
| `not_reproduced_reason` | for the 267: the concrete obstacle (free text, Chinese) |
| `reproduction_script` | for the 72: the harness entry that reproduced it, `file.py::case` |

Runtime evidence (72 rows only)

| column | meaning |
|---|---|
| `defect_description` | what the run did, in one line (Chinese) |
| `trigger_snippet` | the call that triggers the defect |
| `observed_output` | the captured return value or exception |
| `analyst_note` | why the defect happens (Chinese) |
| `issue_error_excerpt` | the error text pasted in the report, for comparison |

Cross-checks (not used as ground truth)

| column | meaning |
|---|---|
| `archived_llm_layer` | what an earlier LLM labelling pass said. It agrees with the reporter's own claim ~91 % of the time, i.e. it largely echoes the report; it is **not** the label used in the paper |
| `archived_llm_agrees_with_reporter` | that pass compared with the reporter's stated layer |
| `l2_path_layer` | layer inferred mechanically from the file paths touched by the linked pull request — an independent side check (35.4 % coverage, 76.5 % agreement with `origin_layer`) |
| `l2_confidence` | confidence of that inference, where recorded |
| `related_pr` | the linked pull request, where one exists |

---

## `data/evidence_class_339.csv` (n = 339)

A projection of the table above, for readers who only want the classification.

| column | meaning |
|---|---|
| `issue`, `case_id`, `title`, `url` | identification |
| `origin_layer` | ground-truth layer |
| `exposure_channel_raw` | class as recorded |
| `evidence_class` | the same class under the paper's names (`single-layer-masked` for `single-layer-genericised`, `registration-time` for `registration`) |
| `evidence_tier` | A / B / C / D |
| `reproduction_status` | as above |

---

## `data/blocking_gaps_83.csv` (n = 83)

The 83 bugs whose reports carry no analysable error (tiers C and D of the 267 not reproduced).

| column | meaning |
|---|---|
| `issue`, `title`, `origin_layer`, `evidence_tier`, `url` | identification |
| `gap_id` | capability gap `A`–`G`, in the order used in the paper |
| `gap_name` | the gap in full: A deployment/transport variant (16), B stdio subprocess and process lifecycle (7), C client/host application (14), D external service/dependency/packaging (15), E timing/concurrency/long connection (9), F non-runtime defect (19), G unusable report (3) |
| `what_reproduction_would_require` | the concrete thing that would be needed (Chinese) |
| `issue_excerpt` | the part of the report the judgement is based on |

---

## `repro/captures_index.csv` (n = 72)

One row per reproduced bug, stating what evidence exists for it. Use it to check a capture against
the record, or to see which bugs have a console dump before going looking for one.

| column | meaning |
|---|---|
| `issue` | issue number |
| `origin_layer` | ground-truth layer |
| `exposure_channel` | raw channel name (the codebook's R1–R6 output) |
| `evidence_class` | class under the paper's names |
| `evidence_tier` | A–D |
| `error_text_source` | `runtime` (our run produced it), `issue text` (quoted from the report), `none` (no diagnostic) |
| `has_error_text` | `yes` for 63 of 72 |
| `has_trigger_code` | `yes` for all 72 |
| `section3_chars` | length of the captured text in the capture file, 0 if empty |
| `has_console_log` | `yes` for 30 |
| `has_raw_payload` | `yes` for 54 |
| `has_harness_record` | `yes` for 54 — the runner's progress file has an entry |
| `harness_entry` | `file.py::case` in `repro/runner/`, where the harness has one |

---

## `repro/raw_map.csv` (n = 54)

| column | meaning |
|---|---|
| `issue` | issue number |
| `raw_file` | file name under `repro/raw/` that holds this bug's payload. Most are `real_<n>.txt`; the 18 hand-built replays are named after the scenario they exercise (`real_r_<scenario>.txt`) |

---

## `repro/repro_verdicts_72.csv` (n = 72)

| column | meaning |
|---|---|
| `issue` | issue number |
| `origin_layer` | ground-truth layer |
| `evidence_class` | class under the paper's names |
| `evidence_tier` | A–D |
| `observed` | `error` (an error surfaced) or `silent (no error raised)` |
| `trigger_summary` | one line on what the run did (Chinese) |
| `captured_output` | relative path to `repro/captures/issue_XXXX.txt` |
| `extra_source` | `yes` if a separate console log exists, `/raw` if a raw payload file exists |
| `harness_entry` | `file.py::case` in `repro/runner/` |

---

## `repro/evidence_matrix.csv` (n = 72)

One row per reproduced bug. Rebuilt by `scripts/build_evidence_matrix.py`; never edited by hand.

| column | meaning |
|---|---|
| `issue`, `origin_layer`, `exposure_channel`, `evidence_class`, `evidence_tier` | the same values as in `captures_index.csv` |
| `error_text_source` | `runtime` / `issue text` / `none` |
| `text_shape` | the fullest text captured for the bug: `stack` (real frames), `block` (4+ lines, no frames), `message` (1–3 lines), `none` (call succeeded) |
| `stack_frames` | number of frame lines found: 0 unless `text_shape = stack` |
| `body_lines` | non-blank lines in the captured text |
| `has_console_log`, `console_log` | whether a `repro/logs/` file exists, and its path |
| `has_raw_payload` | whether `repro/raw/` holds the payload |
| `run_output`, `capture` | paths to the two per-bug records |
| `transcript` | path to `repro/transcripts/issue_N.txt` when the traceback is complete (34 rows), empty otherwise |
| `gap_reason` | why there is no transcript — the client-visible message is all that survived, the failure is a wrong result with no exception, or only the tail of a traceback was kept. Empty whenever `transcript` is filled |

Counts: `stack` 35 (34 of them with a complete transcript), `block` 13, `message` 16, `none` 8.

---

## `repro/attempt_log.csv` (n = 350)

| column | meaning |
|---|---|
| `issue` | issue number |
| `status` | `done` (reproduced) or `limited` (attempted; obstacle recorded) |
| `origin_layer` | layer recorded at the time of the attempt |
| `transport` | transport used: `streamable-http`, `streamable-http/raw-post`, `sse`, `streamable-http/registration` |
| `defect_captured` | `True` / `False` — did the run produce the failure |
| `recorded_reason` | the obstacle, as written at the time (Chinese or English) |

---

## `llm/outputs/studyB_scores_247.csv` (n = 247)

| column | meaning |
|---|---|
| `issue` | issue number |
| `true_origin_layer` | ground truth, joined from `data/active_bugs_339.csv` |
| `model_reporter_claim` | the layer the model says the *reporter* claimed; empty when the model answered `unclear` (78 rows) |
| `model_origin_layer` | the layer the model says the fault originated in — the prediction |
| `correct` | 1 if `model_origin_layer == true_origin_layer`, else 0 |
| `reason` | the model's one-sentence justification |

## `llm/outputs/studyA_arms_72.json`

A JSON object with three keys (`baseline`, `ruleclue`, `analyst`), each a list of 72 records:

| field | meaning |
|---|---|
| `issue` | issue number |
| `origin` | layer recorded at the time of the run — **do not use it as truth**; join `origin_layer` from `data/active_bugs_339.csv` |
| `channel` | evidence class at the time of the run |
| `pred` | predicted layer |
| `raw` | the model's raw reply |
| `rank` / `scores_raw` | the ranked variant: layer order and the 0–100 scores |

## `llm/outputs/clues_72.json` (n = 72)

| field | meaning |
|---|---|
| `issue` | issue number |
| `origin`, `channel` | as above |
| `hint` | the clue paragraph the `ruleclue` arm was given for this bug |

## `llm/outputs/studyB_247.jsonl` (n = 247 lines)

| field | meaning |
|---|---|
| `issue`, `title`, `body`, `snippet` | exactly what the model was shown (`body` truncated to 4,000 chars, `snippet` to 2,000) |
| `reporter_claim_layer`, `our_layer`, `reason` | the parsed reply |
| `raw` | the reply before parsing |
| `scores` | the 0–100 layer scores, where the model produced them |
| `ok` | whether parsing succeeded |
| `true_origin_layer` | ground truth joined in for convenience |
