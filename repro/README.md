# How to read (and re-run) a reproduction case

## The short version

1. Take an issue number from `../data/active_bugs_339.csv` where `reproduction_status = reproduced`.
2. Open `run_output/issue_XXXX.txt` for what the run printed, or `captures/issue_XXXX.txt` for the
   self-contained record: the trigger that was run, what the reporter described, the output that was
   captured, and the layer analysis.
3. Use `captures_index.csv` if you want to see, at a glance, which of the 72 bugs have which kinds
   of evidence.
4. If you want to know why a *different* bug was not reproduced, look it up in
   `../data/active_bugs_339.csv` (`not_reproduced_reason`) and in `attempt_log.csv`.

`run_output/` holds one file per reproduced bug (72). Its first six lines are a header — harness,
kind of capture, source of the text, and where the diagnostic came from — and everything below is
the output, verbatim. The header's `capture kind` names the *source* of the text (a console log for
30, a traceback excerpt for 5, the client's return payload for 37). It is not a statement about
completeness: judged by content, 15 files contain a real stack trace, 13 a multi-line error block
with no frames, 36 a one-to-three-line message, and 8 no error at all. `evidence_matrix.csv` has
that, and the reason for any gap, bug by bug.

## Anatomy of a capture

`captures/issue_0079.txt` (abridged):

```text
# issue: #79
# origin_layer: Client
# exposure_channel: caller-exception
# evidence_class: caller-exception
# evidence_tier: A
# evidence_source: runtime
# harness_entry: runner/repro_pending/repro_79.py
# console_log: logs/79.txt
# raw_payload: not retained

## 1. What was run          <- harness entry + the trigger code
## 2. What the reporter described
## 3. What we captured      <- the error text, tagged runtime / issue text / none
## 4. Why it happens        <- the layer analysis
## 5. Provenance            <- a one-glance table of where each field came from

## A. Harness progress record     (when the runner wrote one)
## B. Raw console log             (when one was kept)
## C. Raw payload                 (when one was kept)
```

Read section 3 and the `# evidence_source` line together. `runtime` means the text was produced by
our own run; `issue text` means our replay did not raise it again and the quoted error comes from
the report itself; `none` means the failure produced no diagnostic output at all (a silent failure).
The distinction matters: it is the difference between "we saw this" and "the reporter saw this".

## What evidence exists, bug by bug

`captures_index.csv` has one row per bug. The counts across the 72:

| Column | `yes` | What it means |
|---|---|---|
| `has_trigger_code` | 72 | every bug has the code or the reproduction recipe that was run |
| `has_error_text` | 63 | an error text is recorded (49 runtime, 14 quoted from the issue) |
| `has_raw_payload` | 54 | the raw object returned by the run was written to `raw/` |
| `has_console_log` | 30 | a separate console log file was kept |
| `has_harness_record` | 54 | the runner's progress file has an entry for the bug |

The four kind of evidence accumulated at different points in the study, which is why the coverages
differ: the runner's progress record came first, the per-bug raw dump came next, and the separate
console-log dump was added partway through, so only the bugs run after that point have one. Where a
source does not exist for a bug, the corresponding appendix is absent rather than empty. Nothing is
imputed.

`evidence_matrix.csv` answers the sharper question — **is there a stack trace?** — for all 72:

| `text_shape` | bugs | what the file contains |
|---|---|---|
| `stack` | 15 | frames with file and line |
| `block` | 13 | four or more lines, no frames |
| `message` | 36 | one to three lines |
| `none` | 8 | the call succeeded; a wrong result is documented instead |

So 57 of the 72 have no traceback in the 2025 record. That is a property of the protocol rather than
of our runs: the server catches the tool exception and returns `is_error=True` with a one-line
message, so the frames never reach the client.

`logs_rerun_2026_11/` closes part of that gap. On 2026-11-09 the 57 stack-less bugs that have a
`Case` (39 of them) were re-run with the server's logger at DEBUG:

```bash
python -m repro.runner.rerun_with_server_log 110     # prints client result + server traceback
```

20 came back with the same client-visible payload and the traceback; 12 with the same payload and
nothing raised; 7 did not fire. The 20 are labelled as re-runs in their header and are never mixed
with the 2025 captures. `evidence_matrix.csv` keeps `text_shape` (2025) and `stack_available` (which
run the frames come from) apart, and `rerun_2026_11.csv` lists all 39 attempts with the outcome.

`../docs/08_evidence_coverage.md` breaks the rest down and says what was captured instead. Nothing
was reconstructed to fill the remaining 37.

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
4. `../docs/02_codebook.md` → why that is `pushed-to-Server` and not `single-layer-correct`.

That is the whole method the paper uses: put the trigger and the captured output side by side, and
read the layer off the distinction between where the message points and where the defect is.
