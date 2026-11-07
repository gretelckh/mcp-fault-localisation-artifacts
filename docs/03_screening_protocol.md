# Screening protocol: 1,343 → 439 → 398 → 339

Source: `modelcontextprotocol/python-sdk`, the official Python SDK of the Model Context Protocol.
At mining time the tracker had 1,343 issues and no pull requests in the pool (the tracker keeps PRs
in a separate space).

## The seven stages

| Stage | Rule | Count | Where it is in this repo |
|---|---|---:|---|
| 1 | every issue in the pool, all states | 1,343 | `data/screening_1343.csv` |
| 2 | keyword screen flags the report as a candidate bug | 439 | column `keyword_label` = `BUG` |
| 3 | manual review confirms a genuine defect report | 398 | `data/screening_funnel.csv` row 3 |
| 4 | removed: already behaves correctly on the pinned SDK (`mcp 2.2.0`) | 59 | computed as 398 − 339 |
| 5 | **ACTIVE dataset analysed in the paper** | **339** | `data/active_bugs_339.csv` |
| 6 | reproduced at runtime on this machine | 72 | `reproduction_status = reproduced` |
| 7 | not reproduced at runtime | 267 | 184 with error text + 83 without |

## What the keyword screen did

Every issue title+body was matched against a fixed keyword set; the six labels and their counts are
in `data/screening_1343.csv`:

| label | n | meaning |
|---|---:|---|
| `BUG` | 439 | contains failure vocabulary: "error", "exception", "crash", "does not work", a traceback, … |
| `QUESTION` | 277 | asks how to do something |
| `OTHER` | 457 | discussion, announcements, meta |
| `FEATURE` | 88 | requests functionality |
| `CI/REFACTOR` | 47 | build, test, refactor, chore |
| `DOC` | 35 | documentation |

The screen is deliberately permissive: it is a recall filter, not a classifier. That is why 41 of
the 439 `BUG` candidates were rejected at stage 3 — usage questions that contain the word "error",
feature requests phrased as complaints, reports about a different package, environment or packaging
failures with no SDK defect, CI/test issues, duplicates, and claims that could not be checked
against any code.

## Why stage 4 exists

The pinned version matters. A report from 2024 may describe a defect that the 2.2.0 release has
already fixed. We re-ran those reports; 59 of the 398 behaved correctly on 2.2.0 and were removed
from the analysed dataset. They remain in the confirmed pool for the funnel, because "we did not
study it" and "it is not a bug" are different statements.

## What this protocol can and cannot support

* **Can**: say how many reports exist, how the 339 were selected, and that the selection is
  reproducible from `data/screening_1343.csv` plus the keyword list.
* **Cannot**: claim that the 339 are a random sample of all MCP faults. They are all the reports in
  one SDK's tracker that survived screening — a census of one project, not a sample of the
  ecosystem. The paper says this explicitly.
* **Cannot**: claim the 267 unreproduced reports are not bugs. They are reports we could not
  trigger on this machine; `data/blocking_gaps_83.csv` and `repro/attempt_log.csv` say why, per bug.

## Reproducing the funnel

```python
import csv
pool = list(csv.DictReader(open("data/screening_1343.csv")))
active = list(csv.DictReader(open("data/active_bugs_339.csv")))
print(len(pool))                                        # 1343
print(sum(r["keyword_label"] == "BUG" for r in pool))    # 439
print(len(active))                                      # 339
print(len(pool) - len(active))                          # 1004 not analysed (904 non-bug + 41 rejected + 59 fixed)
```
