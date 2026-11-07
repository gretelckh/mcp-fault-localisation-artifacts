# Codebook

Three label sets are used in the dataset: the **origin layer** (where the defect is), the
**evidence class** (what the developer is actually shown), and the **evidence tier** (how much
error text the report contains). They answer three different questions and must not be confused.

---

## 1. Origin layer — where the defect is

| Label | Fault originates in | Typical shape |
|---|---|---|
| `Host` | the host application or the LLM caller | invoking a tool that does not exist, misspelled or missing arguments, wrong argument type |
| `Client` | the client-side JSON-RPC assembly and session handling | redundant parameters, wrong nesting, invalid enum value, swallowed exception |
| `Server` | the server's tool / resource / prompt implementation or its registration | division by zero, assertion, custom exception, duplicate registration, permission check |
| `Transport` | the session and message-passing layer | call after the session closed, cancelled in-flight request, malformed frame, call before initialise |
| `multi` | no single fix point: the fix has to touch two layers | one bug only (issue #3644) |

### The six rules that produce the labels (R1–R6)

These rules were fixed before labelling and applied mechanically; they are what makes the label
reproducible rather than a matter of taste.

| Rule | Statement |
|---|---|
| **R1** | Files that implement transport or wire format — `client|server` `stdio`, `sse`, `streamable_http*`, `_transport`, `types`, `shared/message` — are **Transport**. |
| **R2** | JSON-RPC session, framing and response construction inside `shared/` is **Transport**: both ends use it, so neither end alone can be blamed. |
| **R3** | Everything else under `client/**` is **Client**; everything else under `server/**` is **Server**. |
| **R4** | Third-party clients (Claude Desktop, VS Code, the Inspector), OS-level adaptation, `os/**`, examples and packaging are **Host**. |
| **R5** | The trigger does not decide the label. If the caller is the client, the fault is still **Client** only if the client is the component that must change. |
| **R6** | If two layers must change, take the minimal sufficient fix point; if none exists, label `multi`. |

The single most common labelling error is to record the layer where the exception *surfaces*
instead of the layer that must be *changed* — for example recording a bug in `server/stdio.py` as
`Server` when the file is transport implementation and the label is `Transport`.

---

## 2. Evidence class — what the developer is shown

This label is assigned only to the 72 bugs that were reproduced, because it is read off the
runtime output. The other 267 carry `not_exercised_not_inferable`: without a run there is nothing
to read.

| Label in this repo | Label in the paper | n | Definition |
|---|---|---|---|
| `pushed-to-Server` | pushed-to-server | 8 | The origin is upstream (Host, Client or Transport) but the call returns `Error executing tool X` with `is_error=True`, i.e. the server tool-dispatch layer takes the blame. |
| `silent` | silent | 13 | `is_error=False` and a plausible value is returned; the logical error never surfaces. |
| `caller-exception` | caller-exception | 18 | A bare Python or HTTP exception (`CancelledError`, `RuntimeError`, an HTTP status) escapes into the calling frame instead of being wrapped into the `is_error` channel. |
| `single-layer-genericised` | single-layer-masked | 18 | The error is reported in the right layer but as one constant string with no stack, so the frame that failed is erased. |
| `single-layer-correct` | single-layer-correct | 12 | The error names the file, the function and the exception type, in the layer where the defect is. |
| `registration` | registration-time | 3 | The exception is raised while a tool, resource or prompt is registered, so it is attributed to the component being registered rather than to the code that later calls it. |

Two derived metrics are used in the paper, and both are counted from this table rather than from a
separate file:

* **manifestation–root-cause mismatch** — a non-Server bug whose evidence class names another
  layer, i.e. `pushed-to-Server` or `caller-exception` while `origin_layer` is not `Server`.
* **silent failure** — evidence class `silent` (13 of 72).

To recompute them:

```python
import csv
rows = [r for r in csv.DictReader(open("data/active_bugs_339.csv"))
        if r["reproduction_status"] == "reproduced"]
non_server = [r for r in rows if r["origin_layer"] != "Server"]
mismatch = [r for r in non_server
            if r["exposure_channel_raw"] in ("pushed-to-Server", "caller-exception")]
print(len(mismatch), "/", len(non_server))          # 24 / 34
print(sum(r["exposure_channel_raw"] == "silent" for r in rows), "/", len(rows))   # 13 / 72
```

---

## 3. Evidence tier — how much error text the report carries

Assigned to all 339 bugs, from the issue text and, where available, the runtime capture.

| Tier | Meaning | n (of 339) |
|---|---|---|
| `A` | the report contains a complete error: traceback or exception with a file and a type | 181 |
| `B` | the report contains a fragment: an error line without a stack, or a screenshot transcription | 66 |
| `C` | the report only describes the failure in prose | 25 |
| `D` | the report contains no evidence of failure | 67 |

Tier is a property of the *report*, not of the bug: a tier-D report can describe a real defect
whose reproduction would surface it. That is why the analysis of the 83 evidence-poor reports
(`data/blocking_gaps_83.csv`) works from what reproduction would *require*, not from what the
report says.

---

## 4. Reproduction status — what happened when we tried

| Value | Meaning |
|---|---|
| `reproduced` | a run on this machine produced the failure the report describes; the captured output is in `repro/captures/` |
| `not_reproduced__error_text_present` | a run was attempted and did not reproduce, but the report itself contains an analysable error |
| `not_reproduced__no_error_text` | a run was attempted and did not reproduce, and the report contains no analysable error either |

Nothing is labelled `reproduced` without a capture file. Nothing is labelled with an evidence
class without a run.
