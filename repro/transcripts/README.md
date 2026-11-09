# Stack-trace transcripts

One file per reproduced bug whose run kept a **complete Python traceback**: 32 of the 72. Files are
verbatim, redacted, and named `issue_XXXX.txt`.

Each opens with a three-line header:

```
# issue #244 -- reproduction run log
# stack: complete, 7 frames
# ------------------------------------------------------------------
```

Where the body starts with `CLIENT ->`, `SERVER !!` and ends with `CLIENT <-`, those three lines are
the request that was sent, the exception the server caught, and the result the client received:

```
CLIENT -> jsonrpc='2.0' id=2 method='tools/call' params={'name': 'bad', 'arguments': {}, '_meta': {}}
SERVER !! Tool 'bad' raised an unexpected exception
Traceback (most recent call last):
  File ".../mcp/server/mcpserver/tools/base.py", line 189, in run
  ...
pydantic_core._pydantic_core.PydanticSerializationError: Error serializing to JSON: invalid utf-8
sequence of 1 bytes from index 0

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
mcp.server.mcpserver.exceptions.UnexpectedToolError: Error executing tool bad
CLIENT <- {'content': [{'text': 'Error executing tool bad', 'type': 'text'}], 'isError': True}
```

The two chained tracebacks are the point: the first shows *where the defect is* (`_convert_to_content`),
the second *what the caller is told* (`Error executing tool bad`). When those two sit on different
layers you have the phenomenon the study measures — the party that has to fix it is not the party
the message names.

## Missing files are missing for a reason

There are 32 files, not 72. Here is where the other 40 went:

| | n | where / why |
|---|---:|---|
| complete traceback | **32** | this folder |
| only the tail of the traceback | 3 | #76, #915, #3434 — left in `../run_output/` rather than padded out here |
| no traceback at all | 37 | 11 silent (the call returned normally, `is_error=False`: the defect is a wrong answer or a missing safeguard); 26 non-silent but no frames exist — the server returned `isError=True` with a one-line message instead of raising, the exception was raised in the client (cancel scope, JSON decode), or there was no exception because the result was simply wrong |

Per-bug detail is in `../evidence_matrix.csv` (`text_shape`, `gap_reason`) and
`../../docs/08_evidence_coverage.md`. Three bugs (#76, #915, #3434) kept only the **tail** of their
traceback; those are left in `../run_output/` rather than padded out here.

Server-side frames appear only where the server process printed its own traceback; where it did
not, the client got a one-line message and nothing else, and those bugs are not in this folder.
Local paths and account names were replaced with `<workspace>`, `<python-env>` and `<user>`;
nothing else was altered.

## Check them

```bash
ls issue_*.txt | wc -l                    # 32
grep -c 'Traceback (most recent call last)' issue_0244.txt
sed -n '4,40p' issue_1060.txt             # the frames
```
