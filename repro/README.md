# How to read a reproduction case

## The short version

1. Take an issue number from `../data/active_bugs_339.csv` where `reproduction_status = reproduced`.
2. Open `transcripts/issue_XXXX.txt` first — if the bug kept a traceback (all 40 complete), that is
   the whole story in one page: the request, the frames, and the result the client received.
3. If the bug has no traceback, `captures/issue_XXXX.txt` is the self-contained record: the trigger
   that was run, what the reporter described, the output that was captured, and the layer analysis.
4. `evidence_matrix.csv` answers, per bug, *what was captured* (`text_shape`, `stack_frames`) and
   *why a traceback is missing* (`gap_reason`).
5. If you want to know why a *different* bug was not reproduced, look it up in
   `../data/active_bugs_339.csv` (column `not_reproduced_reason`).

`transcripts/` is the folder to send a reviewer to: 40 files, one per bug that kept a traceback,
each with a three-line header and the body verbatim. Two chained tracebacks in one file mean the
defect and the message the caller got are on different layers — the paper's whole point. The other
32 bugs are silent cases, client-side raises, returned errors and wrong results, where a server
traceback does not exist; `evidence_matrix.csv` gives the per-bug reason.

## Anatomy of a capture

`captures/issue_0507.txt` (abridged):

```text
# issue: #507
# origin_layer: Transport
# exposure_channel: caller-exception
# evidence_class: caller-exception
# evidence_tier: A
# evidence_source: runtime
# harness_entry: runner/repro_pending/repro_sse.py

## 1. What was run          <- harness entry + the trigger code
## 2. What the reporter described
## 3. What we captured      <- the error text, tagged runtime / issue text / none
## 4. Why it happens        <- the layer analysis
## 5. Provenance            <- a one-glance table of where each field came from
```

Read section 3 and the `# evidence_source` line together. `runtime` means the text was produced by
our own run; `issue text` means our replay did not raise it again and the quoted error comes from
the report itself; `none` means the failure produced no diagnostic output at all (a silent failure).
The distinction matters: it is the difference between "we saw this" and "the reporter saw this".

## What was captured, bug by bug

`evidence_matrix.csv` answers the sharper question — **is there a stack trace?** — for all 72:

| `text_shape` | bugs | what was captured |
|---|---|---|
| `stack` | 40 | frames with file and line; all complete, all shipped in `transcripts/` |
| `block` | 10 | four or more lines, no frames |
| `message` | 14 | one to three lines |
| `none` | 8 | the call succeeded; a wrong result is documented instead |

32 of the 72 have no traceback. That is a property of the protocol rather than of our runs: the
server catches the tool exception and returns `is_error=True` with a one-line message, so the frames
stop at the client. Where the frames do exist they are collected in `transcripts/`, one file per
bug, with the request, the frames and the result the client received. To capture one yourself:

```bash
python -m repro.runner.capture_with_server_log 110     # client result + server traceback
```

## Re-running

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r ../requirements.txt
python -m repro.runner.repro_framework --only 234
```

The harness prints the return object, the `is_error` flag and any escaped exception — the same
three things the capture records. Expect differences in:

* `serverInfo.version` and the temporary port number (both differ per run);
* traceback line numbers, if your `mcp` build differs even slightly;
* anything that depends on wall-clock timing (a few cases are timing-sensitive by design).

## A worked example, end to end

Take #3572 (a Host-side argument of the wrong type, surfaced by the Server):

1. `../data/active_bugs_339.csv` → row with `issue = #3572`, `origin_layer = Host`,
   `exposure_channel_raw = pushed-to-Server`, `reproduction_status = reproduced`.
2. `captures/issue_3572.txt` → section 3 says the call returned `Error executing tool lookup: 1
   validation error ...` with `is_error=True`, and the message names the Server while the defect
   sits in the caller.
3. `../data/evidence_class_339.csv` → `evidence_class = pushed-to-server`.
4. `evidence_matrix.csv` → `text_shape = message`, `gap_reason` says why no stack exists for it.

That is the whole method the paper uses: put the trigger and the captured output side by side, and
read the layer off the distinction between where the message points and where the defect is.
