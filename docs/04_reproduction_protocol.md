# Reproduction protocol

## What "reproduced" means here

A bug is `reproduced` only if a run on this machine produced the failure the report describes, and
the output of that run was captured. Every one of the 72 has a capture file in `repro/captures/`.
No bug is labelled `reproduced` because the report "looks reproducible", and no evidence class is
assigned without a run.

A bug is **not** marked as fixed, or as a non-bug, when reproduction fails. It is marked
`not_reproduced__*` with the concrete obstacle recorded in `not_reproduced_reason`.

## Environment

| Item | Value |
|---|---|
| SDK | `mcp 2.2.0` (Python), the version the study is pinned to |
| Transport | Streamable HTTP (the production transport), plus SSE and stdio for the cases that need them |
| Python | CPython 3.12 |
| OS | Windows x86-64 |
| Server process | uvicorn, one process per case, port assigned by the OS |
| Client | the SDK's own client, driven by the harness |

## The harness

```
repro/runner/repro_cases.py      one Case(...) per bug: tool call, arguments, and a builder
                                 function that stands up a server mirroring the defect
repro/runner/repro_framework.py  starts the server, connects, invokes, captures the outcome
repro/runner/run_real_http.py    transport-level replays (connection closed, bad frame, …)
repro/runner/run_real_http2.py   interactive replays (progress callbacks, concurrent calls)
repro/runner/repro_cases_b14.py  the last batch of cases added
```

A `Case` records four things a reader needs: which tool is called, with which arguments, what
server-side defect the builder injects, and the one-line description of the expected failure. That
is enough to replay the case by hand even if the harness does not run on your machine.

Each run captures:

1. the return object (`CallToolResult`) — text content, `is_error`, structured content;
2. or the exception that escaped — as its traceback when the traceback actually reached the client,
   otherwise as the one-line message the client received (the server converts most tool exceptions
   into `is_error=True`, so this is the common case; see "How complete is the evidence" below);
3. the transport-level record (HTTP status, headers) where the failure is at that level.

## What is in `repro/`

| Item | Count | Content |
|---|---:|---|
| `captures/issue_XXXX.txt` | 72 | one per reproduced bug: trigger, reporter description, captured output, layer analysis, provenance table |
| `captures_index.csv` | 72 | one row per bug: which kinds of evidence exist for it |
| `raw/` | 54 | the raw payload the run wrote to disk |
| `raw_map.csv` | 54 | issue number → raw payload file |
| `logs/NNNN.txt` | 53 | console dumps as the harness wrote them, including runs that did not reproduce (30 belong to the 72) |
| `evidence_matrix.csv` | 72 | one row per bug: `text_shape` (stack / block / message / none), the file paths, and the reason for any gap |
| `repro_verdicts_72.csv` | 72 | verdict table: origin layer, evidence class, evidence tier, error vs silent, path to the capture |
| `attempt_log.csv` | 350 | every attempt the harness recorded: 49 `done` (reproduced) and 301 `limited` (attempted, obstacle recorded) |

### How complete is the evidence, bug by bug

The four kinds of evidence were not collected by the same mechanism, so they do not cover the same
set of bugs. `captures_index.csv` states this per bug rather than leaving the reader to guess:

| Evidence | Bugs with it | Why the others do not have it |
|---|---:|---|
| Trigger code or reproduction recipe | 72 | required to run the case at all |
| Error text | 63 | 49 captured at runtime, 14 quoted from the issue body because our replay did not raise it again, 9 are silent failures with no diagnostic |
| Raw payload on disk | 54 | the per-bug dump was added after the first batch had been run |
| Console dump | 30 | the separate log dump was added later still; 12 were recovered from the baseline replay that preceded the repair experiment |
| Runner progress record | 54 | a few cases were driven by standalone scripts that did not write to the progress file |

No cell is filled in by inference. Where a source does not exist, the section is absent from the
capture and the corresponding column says `no`.

### Stack traces: 15 of 72

The one number a reader is most likely to misread is "console dump 30". A console log existing is not
the same as a traceback existing. By content (`evidence_matrix.csv`, column `text_shape`):

| Shape | Bugs |
|---|---:|
| real stack trace, with file and line | 15 |
| multi-line error block, no frames | 13 |
| one-to-three-line message | 36 |
| no error at all (`is_error=False`) | 8 |

The reason is protocol-level: `mcp/server/mcpserver/tools/base.py` catches a tool exception and
returns a normal result with `is_error=True` and a one-line `TextContent`; the frames go to the
server's stderr and are printed only if that process installs a log handler. Our harness recorded
the client side. `docs/08_evidence_coverage.md` splits the 57 without a traceback by failure kind
(22 exception-type, 24 wrong-result, 11 silent), lists the 22 exception-type cases by issue, and
explains why they were not regenerated from a newer environment.

The attempt log is the honest part of the package: it shows the failures as failures, with the
reason. Its 350 rows are 350 distinct issues — 49 recorded `done` and 301 `limited`. It includes
240 of the 267 bugs that ended up not reproduced; the other 27 are documented only by
`not_reproduced_reason` in the dataset, because reproduction was judged infeasible from the report
before a run was attempted.

## Why 267 were not reproduced

The obstacles are not uniform, and lumping them together would overstate the failure rate. The
per-bug labels in `not_reproduced_reason` collapse into two big families:

* **the run needs an environment we do not have** — a specific transport (stdio subprocess, SSE,
  a reverse proxy, a mounted sub-path), a dependency the bug is *about* (Elasticsearch, an OAuth
  provider, `npx`, a particular `httpx`), a platform (Windows, Cloud Run, Docker), or a third-party
  client (Claude Desktop, VS Code, the Inspector, Jupyter);
* **the run does not exercise the defect** — a race, a lost update, a long-lived connection that
  only breaks after minutes, a schema shape that a single clean tool call never produces.

The 83 reports that carry no usable error text are analysed separately in
`data/blocking_gaps_83.csv`: for each, what reproduction *would* require. Seven capability gaps
account for all 83 (16 / 7 / 14 / 15 / 9 / 19 / 3).

## Re-running a case

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m repro.runner.repro_framework --only 234      # replay #234
python -m repro.runner.repro_framework --batch 1       # replay a batch
```

Two caveats worth knowing before you try:

* The builders use the internal module layout of the pinned version (`mcp.server.mcpserver`,
  `mcp.client.client`). On another release they will need import fixes — the *defect* each case
  injects is version-independent, the import path is not.
* Cases whose defect lives in a client or host application cannot be replayed by the harness at
  all. They are recorded as `not_exercised` rather than simulated.
