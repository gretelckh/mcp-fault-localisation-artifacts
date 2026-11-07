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
| OS | Linux x86-64 |
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
2. or the exception that escaped, with its traceback;
3. the transport-level record (HTTP status, headers) where the failure is at that level.

## What is in `repro/`

| Item | Count | Content |
|---|---:|---|
| `captures/issue_XXXX.txt` | 72 | one per reproduced bug: header + captured return value or exception + the raw payload and console log where the run wrote one |
| `logs/NNNN.txt` | 41 | the console log as the harness wrote it, including runs that did not reproduce |
| `repro_verdicts_72.csv` | 72 | verdict table: origin layer, evidence class, evidence tier, error vs silent, path to the capture |
| `attempt_log.csv` | 350 | every attempt the harness recorded: 49 `done` (reproduced) and 301 `limited` (attempted, obstacle recorded) |

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
