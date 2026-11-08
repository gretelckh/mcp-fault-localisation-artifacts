# 08 · Evidence coverage for the 72 reproduced bugs

This sheet exists because "did you really reproduce it?" is the first question a reader asks
about an empirical reproduction study, and the honest answer differs from bug to bug. Every number
below is derived from the files in `repro/`, by `scripts/build_evidence_matrix.py`; nothing is
estimated.

The per-bug table is **`repro/evidence_matrix.csv`** (72 rows, one per reproduced bug).

---

## 1. What the captured text actually looks like

| `text_shape` | bugs | what the run-output file contains |
|---|---|---|
| `stack` | **15** | a real stack trace — Python `File "...", line N` frames, or JS `at fn (file:line:col)` |
| `block` | **13** | four or more lines: verdict line, error type, message, and the state the run observed — but no frames |
| `message` | **36** | one to three lines: the message the client received, or the return payload |
| `none` | **8** | the call succeeded (`is_error=False`); the defect is a wrong result, documented instead of an exception |
| | **72** | |

So **15 of 72** runs kept a full console traceback. The rest did not, and section 3 says why.

## 2. The gap, separated by what kind of failure it is

Of the 72, **13 are silent** in the codebook sense (`evidence_class = silent`): the caller saw no
error at all. Of those 13, 8 have no text whatsoever; the other 5 still captured something,
because a background task raised while the call itself returned normally (2 of them have frames,
2 a block, 1 a message).

That leaves **59 non-silent bugs, of which 46 have no stack trace**:

| | without a stack | why |
|---|---|---|
| exception-type (`caller-exception`, `pushed-to-server`, `registration-time`) | **22** | an exception did occur, but only its message reached the client (a one-line message in 15, a block in 7) |
| wrong-result (`single-layer-correct`, `single-layer-masked`) | **24** | the failure is a wrong answer or a missing safeguard; there is no exception to catch |

44 of the 46 do have a verbatim error text (37 runtime + 7 quoted from the report); 2 carry only
the observed output.

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
grep '^#3637,' repro/evidence_matrix.csv         # one bug: shape, files, and the gap reason
sed -n '1,40p' repro/run_output/issue_3637.txt   # the recorded text, verbatim
```

## 6. What would close the gap, and why it is not done

Re-running the 46 with server-side logging on (`PYTHONFAULTHANDLER=1`, or a `logging` handler on the
`mcp` logger) would print the frames. We did not do it, for two reasons, both of which belong in the
record rather than in a footnote:

1. **The runs cannot be repeated faithfully on this machine.** The original runs were made in a
   2025 environment (`C:\Users\kehuichen2\...`, `mcp` 1.x–2.x per bug); replaying the same snippets
   today returns `MCPError: Not Found` before the defect is reached. A traceback from a different
   build would not be the same evidence.
2. **A reconstructed traceback is not a captured one.** Filling 46 files with output produced today,
   under a different interpreter and SDK version, and presenting it as the original run would
   misrepresent the record. The gap is left visible instead.

---

## Appendix · the 22 exception-type bugs without a stack trace

These are the cases where a reader is most entitled to ask for one. Each still has a capture, an
`observed_output`, and a `defect_description`.

| issue | true layer | class | text captured |
|---|---|---|---|
| #79 | Client | caller-exception | message |
| #110 | Client | pushed-to-server | message |
| #326 | Host | caller-exception | block |
| #409 | Client | caller-exception | block |
| #507 | Transport | caller-exception | message |
| #521 | Client | caller-exception | message |
| #577 | Client | caller-exception | message |
| #613 | Transport | caller-exception | message |
| #922 | Client | caller-exception | block |
| #1313 | Client | caller-exception | block |
| #1361 | Client | pushed-to-server | message |
| #2114 | Client | pushed-to-server | message |
| #2727 | Transport | caller-exception | message |
| #2741 | Transport | pushed-to-server | message |
| #3240 | Client | caller-exception | block |
| #3382 | Client | caller-exception | block |
| #3384 | Client | caller-exception | block |
| #3556 | Transport | caller-exception | message |
| #3560 | Transport | caller-exception | message |
| #3572 | Host | pushed-to-server | message |
| #3579 | Host | pushed-to-server | message |
| #3637 | Host | pushed-to-server | message |

(#3572 is a Host-side argument error surfaced by the Server: the captured text is the validation
message the Server returned.)
