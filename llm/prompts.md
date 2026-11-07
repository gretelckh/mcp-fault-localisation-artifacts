# Prompts, verbatim

Four prompts were used. All calls are single-turn (`user` role only), no system message, no
few-shot examples, `temperature=0`, one call per bug. The model never sees the ground-truth layer,
the issue's own label, or any other bug.

| Prompt | Used in | `max_tokens` |
|---|---|---|
| P1 origin-layer question, runtime text | Study A, `baseline` arm | 24 |
| P2 same, with the rule-based clue appended | Study A, `ruleclue` arm | 24 |
| P3 same, with the analyst note appended | Study A, `analyst` arm | 24 |
| P4 reporter-claim + origin-layer, full issue report | Study B | 200 |

Model: DeepSeek-V4-Flash (FP8) served through an OpenAI-compatible inference proxy. The endpoint is
referred to here as "the institutional API proxy" because it is an internal service that is not
reachable from outside; the model name, the request format and the decoding settings are otherwise
exactly those used in the study.

---

## P1 — Study A baseline (`llm/outputs/studyA_arms_72.json`, key `baseline`)

```text
You are diagnosing a failure in a Model Context Protocol (MCP) pipeline, which connects an LLM
(Host) to external tools (Server) via a Client and a Transport layer. Given only the raw error /
SDK output below, predict the layer at which the fault ORIGINATED (the true root cause), not where
it is merely reported.
Choose exactly one of: Host, Client, Server, Transport.
If the output shows a successful result (no error) yet you suspect a silent logical fault, still
pick the layer you believe the fault originated in; if you genuinely cannot tell, pick the layer
the message points to.
Reply with a single token: Host, Client, Server, or Transport.

RAW SDK OUTPUT:
<the captured return value or exception, as recorded in repro/captures/issue_XXXX.txt>
```

The ranked variant used to compute the score of each layer is identical except for the last two
lines:

```text
You are diagnosing a failure in a Model Context Protocol (MCP) pipeline, which connects an LLM
(Host) to external tools (Server) via a Client and a Transport layer. Given only the raw error /
SDK output below, score how likely the fault ORIGINATED in each of the four layers. Scores are
integers 0-100; they need not sum to 100.
Return ONLY a JSON object with the four keys Host, Client, Server, Transport, e.g.
{"Host":10,"Client":0,"Server":90,"Transport":0}.

RAW SDK OUTPUT:
<same>
```

## P2 — Study A, rule-based clue (`ruleclue` arm)

P1 with this block appended after the raw output. The clue is selected **by evidence class**, not
by bug: one of six fixed paragraphs, `llm/outputs/clues_72.json` column `hint`. It describes the
mechanism of the class and never names the layer or the bug.

```text
DIAGNOSTIC GUIDANCE (direction only, does NOT state the answer):
CLUE: The failure surfaced as a RAW Python EXCEPTION in the calling code (e.g. CancelledError,
TimeoutError, ExceptionGroup, or a "Client must be used within an async context manager"
RuntimeError), bypassing the MCP is_error protocol. This signature is characteristic of the
connection/session lifecycle rather than a tool's logic: check session and connection state,
request cancellation, timing/ordering of initialisation calls, and whether the client was used
inside the correct async context. The exception is raised by the runtime, so correlate it with
transport/session state, not tool code.
```

The six clues, one per evidence class, are in `llm/outputs/clues_72.json`. They are mechanically
generated from the class definition in `docs/02_codebook.md`; no clue mentions a layer name, a bug
number or a file.

## P3 — Study A, analyst note (`analyst` arm)

P1 with a four-way analyst note instead of the clue, keyed to the class family rather than to the
class: `names` (for `single-layer-correct` and `registration`), `generic` (for
`single-layer-masked` and `pushed-to-Server`), `neighbour` (for `caller-exception`), `silent`. The
notes are written from the study's findings and are layer-blind — the words Host, Client, Server
and Transport never appear in them. Full text in `llm/outputs/studyA_arms_72.json` is not enough to
reconstruct them, so they are reproduced here in full:

```text
[names]
ANALYST NOTE (mechanism only, does not state the answer).
This output names a concrete file, function or parameter together with an exception type. That is
the strongest evidence the SDK produces, but one caveat applies: an exception raised while a tool,
resource or prompt is being registered is attributed to the component being registered, not to the
code that later calls it, and the same is true of a validation error raised on a parameter model.
The reported layer and the origin coincide only when the exception was raised during the call
itself. Check whether the traceback's first frame is registration-time code or request-time code
before you decide.

[generic]
ANALYST NOTE (mechanism only, does not state the answer).
A single constant string with no stack means the SDK caught an exception somewhere and replaced it
with fixed text; the original frame is gone. The identical constant is produced for three different
situations: a fault inside the tool body, a fault in the arguments the caller built, and a fault
that crossed a process boundary before it ever reached the tool. So the layer implied by the text
is an artefact of where the catcher sits, not evidence about the defect. Ask instead what had to be
true before the call reached the handler: a wrong argument type or a bad field name points upstream
of the tool, a failure to decode or serialise the payload points at the boundary the message
crossed.

[neighbour]
ANALYST NOTE (mechanism only, does not state the answer).
A bare Python or HTTP exception raised in the calling frame means the SDK declined to wrap it. It is
raised by the code that called in, one layer away from the defect, so the traceback names the
caller rather than the cause. These signatures cluster around connection and session lifecycle:
cancellation, ordering of initialisation and teardown, authorisation refresh, and endpoints that
answer with an HTTP status instead of a JSON-RPC body. Read the exception type and the URL and verb
in the message, not the top frame of the traceback.

[silent]
ANALYST NOTE (mechanism only, does not state the answer).
This call returned a plausible result with no error at all. That is not evidence that anything is
correct: the SDK reports success whenever a handler returned a value, including a stale value, a
truncated value, or the result of a lost update. Compare the returned value with what the call
should produce, and ask which component could corrupt it without raising: shared state and caches,
argument names that were silently dropped, or a missing expiry check.
```

## P4 — Study B (`llm/outputs/studyB_247.jsonl`)

Model input: the issue title, the body (truncated to 4,000 characters) and the most
error-relevant excerpt (2,000 characters) extracted from the body.

```text
You are diagnosing a fault in a Model Context Protocol (MCP) pipeline, which connects an LLM (HOST)
to external tools (SERVER) via a CLIENT and a TRANSPORT layer. Below is a real GitHub issue from the
modelcontextprotocol/python-sdk repo (title + body + the most error-relevant excerpt).

Please output a single JSON object with exactly these keys:
  "reporter_claim_layer": where the ISSUE REPORTER themselves claims the fault is located. One of
  "Host", "Client", "Server", "Transport", or "unclear" if the reporter does not explicitly state a
  layer.
  "our_layer": the layer where you (the analyser) believe the fault ORIGINATED (the true root
  cause), NOT where it merely surfaces. One of "Host", "Client", "Server", "Transport".
  "reason": a brief justification (<= 40 words).

Reply with ONLY the JSON object.

ISSUE TITLE:
<title>

ISSUE BODY (truncated):
<body>

MOST ERROR-RELEVANT EXCERPT:
<excerpt>
```

---

## Post-processing

* The reply is scanned for the first occurrence of `Host|Client|Server|Transport` (Study A) or for
  the first `{...}` block, parsed as JSON (Study B). Replies that could not be parsed are visible as
  such in the raw output files; no label was ever imputed by hand.
* `our_layer` is compared with `origin_layer` from `data/active_bugs_339.csv`, not with the
  `origin` field stored inside the model output files (that field carries an earlier labelling
  round). This is why the accuracies in `docs/05_llm_experiments.md` are slightly different from a
  naive read of the JSON.
* `reporter_claim_layer` is kept as the model's *reading of the reporter*, not as a hand annotation;
  an empty value in `studyB_scores_247.csv` means the model returned `unclear` (78 of 247).
