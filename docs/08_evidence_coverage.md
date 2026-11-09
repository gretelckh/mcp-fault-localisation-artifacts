# 08 · Evidence coverage for the 72 reproduced bugs

This sheet exists because "did you really reproduce it?" is the first question a reader asks
about an empirical reproduction study, and the honest answer differs from bug to bug. Every number
below is derived from the files in `repro/`, by `scripts/build_evidence_matrix.py`; nothing is
estimated.

The per-bug table is **`repro/evidence_matrix.csv`** (72 rows, one per reproduced bug). The flat
copy of every complete traceback is **`repro/transcripts/`** (32 files).

---

## 1. What the captured text looks like

`text_shape` describes the fullest text captured for that bug — the run-output body, or the
transcript in `repro/transcripts/` when that goes deeper:

| `text_shape` | bugs | what was captured |
|---|---|---|
| `stack` | **35** | real frames — Python `File "...", line N`, or JS `at fn (file:line:col)`; 32 of them complete |
| `block` | **13** | four or more lines: verdict line, error type, message, and the state the run observed — but no frames |
| `message` | **16** | one to three lines: the message the client received, or the return payload |
| `none` | **8** | the call succeeded (`is_error=False`); the defect is a wrong result, documented instead of an exception |
| | **72** | |

The 32 complete tracebacks are in `repro/transcripts/`, one file per bug. Of the 35 with frames,
three (#76, #915, #3434) kept only the tail of the traceback and stay in `repro/run_output/`.
The remaining 37 have none, and section 2 says why.

## 2. The gap, separated by what kind of failure it is

Of the 72, **13 are silent** in the codebook sense (`evidence_class = silent`): the caller saw no
error at all. Of those 13, 8 have no text whatsoever; the other 5 still captured something,
because a background task raised while the call itself returned normally (2 of them have frames,
2 a block, 1 a message).

That leaves **59 non-silent bugs, 26 of which have no stack trace**:

| | without a stack | why |
|---|---:|---|
| exception-type (`caller-exception`, `pushed-to-server`, `registration-time`) | **18** | the exception was raised, but in the client or at the HTTP boundary, or only its message reached the client |
| wrong-result (`single-layer-correct`, `single-layer-masked`) | **8** | the failure is a wrong answer or a missing safeguard; there is no exception to catch |

Of the 26, 24 do have a verbatim error text (20 captured at runtime, 4 quoted from the report) and
2 carry only the observed output.

## 3. Why the stack is missing

The MCP server catches a tool exception and converts it into a normal `CallToolResult` with
`is_error=True` and a one-line `TextContent` (`mcp/server/mcpserver/tools/base.py`). The frames go
to the server process's own stderr, and are printed only if that process installs a log handler.

This is a property of the protocol, not of individual bugs, which is why the shape is so uniform:
the 16 `message` rows are the same phenomenon 16 times. Where the server's logger was on, both
sides of the call ended up in the same file — the request, the frames, and the result the client
received — which is what `repro/transcripts/` holds.

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
python scripts/build_evidence_matrix.py            # rebuild the table; prints the shape counts
grep '^#3637,' repro/evidence_matrix.csv           # one bug: shape, files, gap reason
sed -n '1,40p' repro/transcripts/issue_1060.txt    # a complete traceback, if the bug is one of the 32
sed -n '1,40p' repro/run_output/issue_3637.txt     # otherwise: the recorded text, verbatim
python -m repro.runner.capture_with_server_log 891 # capture one yourself: client result + server traceback
```

## 6. What could not be recovered, and why

Nothing was filled in by inference. For the 37 bugs with no traceback, a server-side stack does not
exist at any effort, for one of four reasons:

| | n | why no server traceback exists |
|---|---:|---|
| silent class: the call returned normally | 11 | `is_error=False`; the defect is a wrong answer or a missing safeguard, so there is no exception to show |
| raised in the client | 6 | cancel-scope `CancelledError`, JSON decode — the server never saw an exception |
| HTTP boundary | 2 | 404 on `/sse`, 401 — the request never reached a tool |
| returned, not raised | 3 | validation or unknown-tool error, delivered as `is_error=True` |
| driven by a one-off script that recorded only a verdict | 3 | the harness printed `VERDICT=` and the script is not part of the release |
| trigger did not fire again | 4 | the case no longer reproduces on a current release, so there was nothing to capture |
| wrong-result class | 8 | the failure is a wrong answer; no exception exists |
| | **37** | |

The remaining detail is per bug in `repro/evidence_matrix.csv`, column `gap_reason`, which is
generated from the file bodies rather than typed by hand.

## 7. How much a traceback would have changed

Not much, and this is measurable. The traceback's top frame shows where the exception was *raised*;
the layer label records where the *fix* goes. Those differ for 34 of the 72 — the finding the paper
is about. For the 40 bugs that have an upstream fix PR, the label can be checked against the file
that had to change, with no log at all.

---

## Appendix · the exception-type bugs without a stack trace (18)

These are the cases where a reader is most entitled to ask for one. Each still has a capture, an
`observed_output`, and a `defect_description` in `repro/captures/`.

| issue | true layer | class |
|---|---|---|
| #79 | Client | caller-exception |
| #326 | Host | caller-exception |
| #409 | Client | caller-exception |
| #507 | Transport | caller-exception |
| #521 | Client | caller-exception |
| #577 | Client | caller-exception |
| #613 | Transport | caller-exception |
| #922 | Client | caller-exception |
| #1313 | Client | caller-exception |
| #2727 | Transport | caller-exception |
| #3240 | Client | caller-exception |
| #3382 | Client | caller-exception |
| #3384 | Client | caller-exception |
| #3556 | Transport | caller-exception |
| #3560 | Transport | caller-exception |
| #3572 | Host | pushed-to-server |
| #3579 | Host | pushed-to-server |
| #3637 | Host | pushed-to-server |

Where each of them raised: 6 in the client (cancel-scope `CancelledError`, JSON decode), 2 at the
HTTP boundary (404 on `/sse`, 401), 3 returned a validation or unknown-tool error instead of
raising, and 7 were driven by scripts that recorded only a verdict or did not fire again in this
build. None of them can produce a server traceback.
