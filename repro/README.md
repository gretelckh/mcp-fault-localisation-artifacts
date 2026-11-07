# How to read (and re-run) a reproduction case

## The short version

1. Take an issue number from `../data/active_bugs_339.csv` where `reproduction_status = reproduced`.
2. Open `captures/issue_XXXX.txt`. It tells you what the run produced.
3. If you want the trigger, look up the same number in `runner/repro_cases.py` (`Case(issue=...)`).
4. If you want to know why a *different* bug was not reproduced, look it up in
   `../data/active_bugs_339.csv` (`not_reproduced_reason`) and in `attempt_log.csv`.

## Anatomy of a capture

`captures/issue_0234.txt`:

```text
# issue: #234
# origin_layer: Server
# evidence_class: single-layer-correct
# evidence_tier: B
# transport: streamable-http
# harness_entry: repro_cases.py::b_234
# defect_captured: True

## captured return value / raised exception (repro_progress.json)

meta={'io.modelcontextprotocol/serverInfo': ...} content=[TextContent(type='text',
text='Unknown tool: no_such_tool', ...)] is_error=True result_type='complete'

## raw payload written by the run (data/real_raw/real_234.txt)

<same text, as the harness wrote it to disk>
```

Read the header first: it says which layer the defect is in, which evidence class the output
belongs to, and what the run looked like. The body is the evidence — verbatim, not summarised.

## The three source layers of evidence

| In the capture | Comes from | Why three |
|---|---|---|
| `captured return value / raised exception` | the harness's per-bug progress record | present for all 72 |
| `raw payload` | `raw/real_<n>.txt` | written for 36 of the 72 |
| `raw payload` under a scenario name | `raw/real_r_<scenario>.txt` | 18 more, written by the standalone replays |
| `console log` | `logs/<n>.txt` | written for 18 of the 72 |

The harness gained the separate log dump partway through the study, which is why the three
coverages differ. Where a source does not exist for a bug, the section is simply absent.

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
2. `captures/issue_3572.txt` → the call returned `Error executing tool lookup: 1 validation
   error ...`, `is_error=True`. The message names the Server, the defect is in the caller.
3. `runner/repro_cases.py` → `Case(issue=3572, ...)` shows the tool call, the argument and the
   injected defect.
4. `../docs/02_codebook.md` → why that is `pushed-to-Server` and not `single-layer-correct`.

That is the whole method the paper uses: put the trigger and the captured output side by side, and
read the layer off the distinction between where the message points and where the defect is.
