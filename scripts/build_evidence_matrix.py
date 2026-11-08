#!/usr/bin/env python3
"""Build repro/evidence_matrix.csv -- one row per reproduced bug.

The point of this file is to let a reader (or a reviewer) answer, for any single
bug, the two questions that come up first:

    what exactly did you capture?   -> text_shape + the file paths
    is anything missing?            -> gap_reason

text_shape is derived from the body of repro/run_output/issue_XXXX.txt, i.e. from
the text that was actually recorded, not from a label chosen in advance:

    stack    at least one real stack frame (Python `File "...", line N`,
             or a JS `at fn (file:line:col)`)
    block    four or more non-blank lines, but no frames
    message  three or fewer non-blank lines
    none     empty body

A bug can have been reproduced and still have no error text: in 8 cases the run
completed and the defect shows up as a wrong result rather than an exception.
That is recorded as text_shape=none, error_text_source=none, and is not a gap --
the capture documents the wrong result instead of a traceback.

Run from the repository root:

    python scripts/build_evidence_matrix.py
"""
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PY_FRAME = re.compile(r'^\s*File ".+", line \d+', re.M)
JS_FRAME = re.compile(r'^\s+at .+:\d+:\d+', re.M)

# the failure kinds in which an exception is expected, as opposed to a wrong result
EXCEPTION_CLASSES = {"caller-exception", "pushed-to-server", "registration-time"}


def body_lines(path):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    cut = [i for i, l in enumerate(lines) if l.startswith("# ---")]
    return lines[cut[0] + 1:] if cut else lines


def shape_of(path):
    text = "\n".join(body_lines(path))
    frames = len(PY_FRAME.findall(text)) + len(JS_FRAME.findall(text))
    n = len([l for l in text.splitlines() if l.strip()])
    if frames:
        return "stack", frames, n
    # a successful call: the payload says so and no error text follows it
    if "is_error=False" in text and "is_error=True" not in text:
        return "none", 0, n
    if n == 0:
        return "none", 0, 0
    if n >= 4:
        return "block", 0, n
    return "message", 0, n


def main():
    idx = list(csv.DictReader(open(os.path.join(ROOT, "repro", "captures_index.csv"), encoding="utf-8")))
    logs = {}
    for p in glob.glob(os.path.join(ROOT, "repro", "logs", "*.txt")):
        logs.setdefault(os.path.basename(p)[:-4], []).append(os.path.basename(p))

    # the 2026-11 re-runs: 39 of the bugs without a stack were re-run, 20 came back with the
    # same payload and the server traceback the 2025 harness never wrote down
    rerun = {}
    rpath = os.path.join(ROOT, "repro", "rerun_2026_11.csv")
    if os.path.exists(rpath):
        for r in csv.DictReader(open(rpath, encoding="utf-8")):
            rerun[r["issue"].lstrip("#")] = r

    out = []
    for r in sorted(idx, key=lambda r: int(r["issue"].lstrip("#"))):
        n = r["issue"].lstrip("#")
        rel_out = "repro/run_output/issue_%04d.txt" % int(n)
        p = os.path.join(ROOT, rel_out)
        shape, frames, nlines = shape_of(p)
        cls = r["evidence_class"]

        if shape == "stack":
            gap = ""
        elif shape == "none":
            gap = ("run completed without an error (is_error=False); the defect is a wrong "
                   "result or a missing safeguard, so there is no exception to show")
        elif cls in EXCEPTION_CLASSES:
            gap = ("client-visible message only; the MCP server turns the exception into a "
                   "TextContent error and the server-side frames were not printed at the log "
                   "level the harness used")
        else:
            gap = ("failure is a wrong result, not an exception; the captured payload is the "
                   "evidence and no stack exists")

        out.append({
            "issue": r["issue"],
            "origin_layer": r["origin_layer"],
            "exposure_channel": r["exposure_channel"],
            "evidence_class": cls,
            "evidence_tier": r["evidence_tier"],
            "error_text_source": r["error_text_source"],
            "text_shape": shape,
            "stack_frames": frames,
            "body_lines": nlines,
            "has_console_log": r["has_console_log"],
            "console_log": ("repro/logs/%s.txt" % n) if n in logs else "",
            "has_raw_payload": r["has_raw_payload"],
            "run_output": rel_out,
            "capture": "repro/captures/issue_%04d.txt" % int(n),
            "gap_reason": gap,
            "rerun_outcome": rerun.get(n, {}).get("outcome", ""),
            "rerun_transcript": rerun.get(n, {}).get("transcript", ""),
            "stack_available": ("2025 record" if shape == "stack"
                                else ("2026-11 re-run" if rerun.get(n, {}).get("transcript") else "")),
        })

    dst = os.path.join(ROOT, "repro", "evidence_matrix.csv")
    with open(dst, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    from collections import Counter
    c = Counter(r["text_shape"] for r in out)
    s = Counter(r["stack_available"] for r in out)
    print("wrote %s (%d rows)" % (os.path.relpath(dst, ROOT), len(out)))
    print("text_shape:", dict(c))
    print("stack available:", dict(s))
    print("without any stack trace:", len(out) - (s["2025 record"] + s["2026-11 re-run"]))
    print("  of which exception-type:", sum(1 for r in out if not r["stack_available"]
                                           and r["evidence_class"] in EXCEPTION_CLASSES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
