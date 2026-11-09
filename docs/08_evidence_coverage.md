# 08 · Evidence coverage for the 72 reproduced bugs

This sheet exists because "did you really reproduce it?" is the first question a reader asks
about an empirical reproduction study, and the honest answer differs from bug to bug. Every number
below is derived from the files in `repro/`, by `scripts/build_evidence_matrix.py`; nothing is
estimated.

The per-bug table is **`repro/evidence_matrix.csv`** (72 rows, one per reproduced bug). The flat,
reader-facing copy of every complete traceback is **`repro/transcripts/`** (32 files).

---

## 1. What the captured text actually looks like

| `text_shape` | bugs | what the run-output file contains |
|---|---|---|
| `stack` | **15** | a real stack trace — Python `File "...", line N` frames, or JS `at fn (file:line:col)` |
| `block` | **13** | four or more lines: verdict line, error type, message, and the state the run observed — but no frames |
| `message` | **36** | one to three lines: the message the client received, or the return payload |
| `none` | **8** | the call succeeded (`is_error=False`); the defect is a wrong result, documented instead of an exception |
| | **72** | |

So **15 of 72** run-output files carry frames, 12 of them complete. Capturing the same cases again
with the server logger on added 20 more (§6), so **32 of 72 have a complete traceback** and they are
collected in `repro/transcripts/`; three more (#76, #915, #3434) kept only the tail. The rest did
not, and section 3 says why.

## 2. The gap, separated by what kind of failure it is

Of the 72, **13 are silent** in the codebook sense (`evidence_class = silent`): the caller saw no
error at all. Of those 13, 8 have no text whatsoever; the other 5 still captured something,
because a background task raised while the call itself returned normally (2 of them have frames,
2 a block, 1 a message).

That leaves **59 non-silent bugs**. In the 2025 record 46 of them had no stack trace; the re-run
closed 20, leaving 26:

| | 2025 only | after the 2026-11 re-run | why |
|---|---|---|---|
| exception-type (`caller-exception`, `pushed-to-server`, `registration-time`) | 22 | **18** | the exception was raised, but in the client or at the HTTP boundary, or only its message reached the client |
| wrong-result (`single-layer-correct`, `single-layer-masked`) | 24 | **8** | the failure is a wrong answer or a missing safeguard; there is no exception to catch |

Of the 26 that still have no stack, 24 do have a verbatim error text (20 captured at runtime, 4
quoted from the report) and 2 carry only the observed output.

## 3. Why the stack is missing

The MCP server catches a tool exception and converts it into a normal `CallToolResult` with
`is_error=True` and a one-line `TextContent` (`mcp/server/mcpserver/tools/base.py`). The frames go
to the server process's own stderr, and are printed only if that process installs a log handler.
Our harness worked from the client side, so what it could record was the message in the result —
`Error executing tool ext`, `MCPError: Connection closed`, and so on — not the traceback behind it.

This is a property of the protocol, not of individual bugs, which is why the shape is so uniform:
the 36 `message` rows are the same phenomenon 36 times.

## 4. What a reader can still check for every bug

`stack` is not the only way in. For all 72:

| artefact | coverage | what it shows |
|---|---|---|
| `repro/captures/issue_XXXX.txt` | 72/72 | the trigger that was run, what the reporter described, the captured output, and the layer verdict, in one file |
| `data/active_bugs_339.csv` → `observed_output` | 72/72 | the output of our run, as entered during the study |
| `data/active_bugs_339.csv` → `defect_description` | 72/72 | the defect, stated independently of the message text |
| `data/active_bugs_339.csv` → `related_pr` | 40/72 | the upstream fix, i.e. the file that had to change — the layer label can be checked against it without any log |
| `data/evidence_class_339.csv` | 72/72 | which of the six failure kinds the bug belongs to, with the rule applied |

The layer label is assigned from *where the fix belongs* (`docs/02_codebook.md`), and for the 40
bugs with a fix PR that is an artefact outside our own judgement. A missing traceback weakens the
"how do you know it is on layer X" argument much less than it looks: the top frame of a Python
traceback shows where the exception was raised, not where the fix goes — and for 34 of the 72 the
fix is not in the layer the message names.

## 5. Checking any single bug in 30 seconds

```bash
python scripts/build_evidence_matrix.py          # rebuild the table; prints the shape counts
grep '^#3637,' repro/evidence_matrix.csv         # one bug: shape, files, gap reason, which run has the stack
sed -n '1,40p' repro/run_output/issue_3637.txt   # the recorded text, verbatim
ls repro/logs_rerun_2026_11/ | wc -l             # 20 re-run transcripts
python -m repro.runner.rerun_with_server_log 891 # re-do one yourself; prints client result + server traceback
```

## 6. The 2026-11 re-run: what it recovered and what it could not

The 2025 harness recorded the client side. Turning the *server's* logger up would have printed the
frames it caught, so on 2026-11-09 every one of the 57 stack-less bugs that has a `Case` definition
was re-run with `mcp` logging at DEBUG (`repro/runner/rerun_with_server_log.py`). 39 bugs were
re-run; the rest have no case definition (they were driven by one-off scripts that are not in the
release).

| Outcome | n | what it means |
|---|---:|---|
| A · same payload + server traceback | **20** | the same client-visible result came back and the server printed the traceback: `repro/logs_rerun_2026_11/issue_N.txt` |
| B · same payload, no traceback | 12 | the failure is a returned error (validation, unknown tool, a wrong value); the server never raised, so there is nothing to print |
| C · not re-observed | 7 | the trigger did not fire in this build, or the endpoint the case targets answers 404 |

The 20 are labelled as re-runs in every file: the header says `source: live re-run on this machine,
2026-11-09 (not the 2025 record)`. They are **not** presented as the original capture, and
`repro/evidence_matrix.csv` keeps the two apart (`text_shape` = 2025, `stack_available` = which
run the traceback comes from).

Nothing was filled in for the other 37. Two reasons, both in the record rather than a footnote:

1. **Most remaining cases never had a server-side exception.** Of the 37 still without a stack:
   11 are the silent class; of the other 26, 6 raise in the client (cancel-scope `CancelledError`,
   JSON decode), 2 are HTTP-boundary errors (404/401), 3 return an error instead of raising, 4 did
   not fire when re-run, 8 are wrong-result cases, and 3 were driven by custom harnesses that only
   recorded a verdict. A server traceback does not exist for them at any effort.
2. **A traceback reconstructed by hand is not a capture.** No file was written from expectations;
   every line in `logs_rerun_2026_11/` came out of a process that ran on this machine.

## 7. How much a traceback would have changed

Not much, and this is measurable. The traceback's top frame shows where the exception was *raised*;
the layer label records where the *fix* goes. Those differ for 34 of the 72 — the finding the paper
is about. For the 40 bugs that have an upstream fix PR, the label can be checked against the file
that had to change, with no log at all.

---

## Appendix · the exception-type bugs that still have no stack trace (18)

These are the cases where a reader is most entitled to ask for one. Each still has a capture, an
`observed_output`, and a `defect_description`; the last column says whether the 2026-11 re-run was
attempted and what happened.

| issue | true layer | class | re-run |
|---|---|---|---|
| #79 | Client | caller-exception | not re-run |
| #326 | Host | caller-exception | re-run: did not fire |
| #409 | Client | caller-exception | not re-run |
| #507 | Transport | caller-exception | not re-run |
| #521 | Client | caller-exception | not re-run |
| #577 | Client | caller-exception | not re-run |
| #613 | Transport | caller-exception | not re-run |
| #922 | Client | caller-exception | not re-run |
| #1313 | Client | caller-exception | not re-run |
| #2727 | Transport | caller-exception | not re-run |
| #3240 | Client | caller-exception | not re-run |
| #3382 | Client | caller-exception | not re-run |
| #3384 | Client | caller-exception | re-run: did not fire |
| #3556 | Transport | caller-exception | re-run: did not fire |
| #3560 | Transport | caller-exception | re-run: did not fire |
| #3572 | Host | pushed-to-server | re-run: no exception raised |
| #3579 | Host | pushed-to-server | re-run: no exception raised |
| #3637 | Host | pushed-to-server | re-run: no exception raised |

Where each of them raised: 6 in the client (cancel-scope `CancelledError`, JSON decode), 2 at the
HTTP boundary (404 on `/sse`, 401), 4 did not fire in the current build, 3 returned a validation or
unknown-tool error instead of raising, and 3 were driven by custom harnesses that recorded only a
verdict. Only the last group could in principle produce a server traceback, and those scripts are
not part of the release.
