# Results snapshot

Every number below is produced by `python scripts/verify_numbers.py` from the files in this
repository. The value in brackets is the one printed in the manuscript.

## Dataset

| Quantity | Value | Source |
|---|---|---|
| issues mined | 1,343 | `data/screening_1343.csv` |
| keyword candidates | 439 | `keyword_label = BUG` |
| confirmed reports | 398 | `data/screening_funnel.csv` |
| removed (already fixed on 2.2.0) | 59 | 398 − 339 |
| **active dataset** | **339** | `data/active_bugs_339.csv` |

## Origin layer of the 339

| Layer | n | share |
|---|---:|---:|
| Transport | 105 | 31.0 % |
| Server | 98 | 28.9 % |
| Client | 84 | 24.8 % |
| Host | 51 | 15.0 % |
| multi | 1 | 0.3 % |

Transport is the largest single layer — the layer the SDK itself implements most heavily, and the
one its error reporting describes least.

## Reproduction

| Quantity | Value |
|---|---|
| reproduced | 72 (Server 38 / Client 21 / Host 5 / Transport 8) |
| not reproduced | 267 = 184 with error text + 83 without |

What the 72 runs actually captured (`repro/evidence_matrix.csv`):

| Shape of the captured text | n |
|---|---:|
| real stack trace, with file and line (34 complete + 1 tail only) | 35 |
| multi-line error block, no frames | 13 |
| one-to-three-line message | 16 |
| no error at all (`is_error=False`) | 8 |

**34 complete tracebacks** are collected in `repro/transcripts/`, one file per bug. One more
(#915) kept only the tail of its traceback and stays in `run_output/`. The remaining 37
are silent cases, client-side raises, returned errors and wrong results, where a server traceback
does not exist; `docs/08_evidence_coverage.md` has the list and the reason for each.

## Evidence classes on the 72

| Class | n |
|---|---:|
| `pushed-to-Server` | 8 |
| `silent` | 13 |
| `caller-exception` | 18 |
| `single-layer-genericised` | 18 |
| `single-layer-correct` | 12 |
| `registration` | 3 |

Evidence tiers over all 339: A 181 / B 66 / C 25 / D 67.

## The 83 evidence-poor reports

| Gap | n | what it means |
|---|---:|---|
| A | 16 | needs a deployment / transport variant |
| B | 7 | needs a stdio subprocess or process-lifecycle setup |
| C | 14 | needs a specific client or host application |
| D | 15 | needs an external service, dependency or packaging setup |
| E | 9 | needs timing, concurrency or a long-lived connection |
| F | 19 | non-runtime defect: nothing crashes at runtime |
| G | 3 | the report contains no information at all |

## Study A — runtime text only (n = 72)

| Arm | all 72 | non-Server (n = 34) |
|---|---|---|
| baseline | 41 = 56.9 % | 3 = 8.8 % |
| rule-based clue | 46 = 63.9 % | 8 = 23.5 % |
| analyst note | 40 = 55.6 % | 3 = 8.8 % |

## Study B — full issue report (n = 247)

| true layer | correct / n | accuracy |
|---|---|---|
| Server | 68 / 75 | 90.7 % |
| Client | 41 / 61 | 67.2 % |
| Transport | 8 / 81 | 9.9 % |
| Host | 2 / 29 | 6.9 % |
| multi | 0 / 1 | 0.0 % |
| **all** | **119 / 247** | **48.2 %** |
| **non-Server** | **51 / 172** | **29.7 %** |

The model abstained on the reporter's claim in 78 of 247 reports.

---

## One labelling decision worth knowing about

Issue **#3434** is a case where the reporter's label and the evidence disagree: the reporter files it
as a Server fault, while the failure is raised by the caller's `progress_callback` crossing the
in-process dispatcher. `data/active_bugs_339.csv` records `Server` for this row, and every aggregate
number in this snapshot follows from that — including the Server/Client split of the 72 (38/21).
Under that label the model also gets it wrong in both studies, so the accuracies above are the
strict ones.

If a reader prefers the Client reading of #3434, these move with it: the Server/Client split of the
72 becomes 37/22; Study A becomes 40/72 (55.6 %), 45/72 (62.5 %) and 39/72 (54.2 %) for the three
arms; Study B becomes 120/247 (48.6 %) and 52/172 (30.2 %) on non-Server; and the mismatch count
becomes 25/35. Everything else — 339, 72, 267, 184, 83, the evidence-class counts and the tier
counts — is independent of this row.

The row is called out here rather than silently harmonised so that the released data and the paper
can be checked against each other.
