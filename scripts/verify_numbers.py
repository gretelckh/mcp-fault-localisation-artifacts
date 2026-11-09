#!/usr/bin/env python3
"""Recompute every dataset-level number reported in the paper, from the files in this repo.

Run from the repository root:

    python scripts/verify_numbers.py

No third-party packages are required. Every check prints the value computed from the
released files next to the value printed in the manuscript; the script exits with
status 1 if any of them disagree.
"""
import csv
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check(label, got, want, unit=""):
    ok = got == want
    if not ok:
        FAIL.append(label)
    print(f"  [{'ok ' if ok else 'FAIL'}] {label:<58} {got}{unit}  (paper: {want}{unit})")


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def main():
    print("\n== 1. Screening funnel ==")
    funnel = {r["stage"]: int(r["count"]) for r in load("data/screening_funnel.csv")}
    pool = load("data/screening_1343.csv")
    active = load("data/active_bugs_339.csv")
    check("issues in the mined pool", len(pool), 1343)
    check("keyword screen flags BUG", sum(1 for r in pool if r["keyword_label"] == "BUG"), 439)
    check("manual review confirms a defect report", funnel["3"], 398)
    check("removed: already fixed on mcp 2.2.0", funnel["4"], 59)
    check("ACTIVE dataset", len(active), 339)
    check("funnel arithmetic: 398 - 59 = 339", funnel["3"] - funnel["4"], 339)

    print("\n== 2. Origin layer of the 339 active bugs ==")
    layers = Counter(r["origin_layer"] for r in active)
    for k, v in [("Transport", 105), ("Server", 98), ("Client", 84), ("Host", 51), ("multi", 1)]:
        check(f"origin_layer = {k}", layers[k], v)
    check("layers sum to the dataset", sum(layers.values()), 339)

    print("\n== 3. The 72 reproduced bugs ==")
    repro = [r for r in active if r["reproduction_status"] == "reproduced"]
    check("reproduced bugs", len(repro), 72)
    rl = Counter(r["origin_layer"] for r in repro)
    for k, v in [("Server", 38), ("Client", 21), ("Host", 5), ("Transport", 8)]:
        check(f"reproduced, origin_layer = {k}", rl[k], v)
    rc = Counter(r["exposure_channel_raw"] for r in repro)
    for k, v in [("pushed-to-Server", 8), ("silent", 13), ("caller-exception", 18),
                 ("single-layer-genericised", 18), ("single-layer-correct", 12), ("registration", 3)]:
        check(f"evidence class = {k}", rc[k], v)
    tiers = Counter(r["evidence_tier"] for r in active)
    for k, v in [("A", 181), ("B", 66), ("C", 25), ("D", 67)]:
        check(f"evidence tier {k} (all 339)", tiers[k], v)

    print("\n== 4. The 267 not reproduced ==")
    with_err = [r for r in active if r["reproduction_status"] == "not_reproduced__error_text_present"]
    no_err = [r for r in active if r["reproduction_status"] == "not_reproduced__no_error_text"]
    check("not reproduced, error text present", len(with_err), 184)
    check("not reproduced, no error text", len(no_err), 83)
    check("not reproduced, total", len(with_err) + len(no_err), 267)
    check("72 + 267 = 339", len(repro) + len(with_err) + len(no_err), 339)

    print("\n== 5. Why the 83 evidence-poor reports are blocked ==")
    gaps = load("data/blocking_gaps_83.csv")
    gc = Counter(r["gap_id"] for r in gaps)
    check("blocked reports analysed", len(gaps), 83)
    for k, v in [("A", 16), ("B", 7), ("C", 14), ("D", 15), ("E", 9), ("F", 19), ("G", 3)]:
        check(f"capability gap {k}", gc[k], v)

    print("\n== 6. Study A: three arms on the 72 reproduced bugs ==")
    truth = {int(r["issue"].lstrip("#")): r["origin_layer"] for r in active}
    arms = json.load(open(os.path.join(ROOT, "llm", "outputs", "studyA_arms_72.json"), encoding="utf-8"))
    for arm, want_all, want_ns, want_ns_n in [("baseline", 41, 3, 34), ("ruleclue", 46, 8, 34)]:
        recs = arms[arm]
        hit = sum(1 for r in recs if r["pred"] == truth.get(int(r["issue"])))
        non_srv = [r for r in recs if truth.get(int(r["issue"])) != "Server"]
        hit_ns = sum(1 for r in non_srv if r["pred"] == truth.get(int(r["issue"])))
        check(f"arm {arm}: correct", hit, want_all)
        check(f"arm {arm}: accuracy (%)", pct(hit, len(recs)), round(100.0 * want_all / 72, 1))
        check(f"arm {arm}: non-Server correct", hit_ns, want_ns)
        check(f"arm {arm}: non-Server accuracy (%)", pct(hit_ns, len(non_srv)),
              round(100.0 * want_ns / want_ns_n, 1))

    print("\n== 7. Study B: issue text only, n = 247 ==")
    scores = load("llm/outputs/studyB_scores_247.csv")
    ok = sum(int(r["correct"]) for r in scores)
    check("bugs scored", len(scores), 247)
    check("correct", ok, 119)
    check("accuracy (%)", pct(ok, len(scores)), 48.2)
    by = defaultdict(lambda: [0, 0])
    for r in scores:
        by[r["true_origin_layer"]][0] += int(r["correct"])
        by[r["true_origin_layer"]][1] += 1
    for k, (a, b) in [("Server", (68, 75)), ("Client", (41, 61)), ("Transport", (8, 81)), ("Host", (2, 29))]:
        check(f"true layer {k}: correct", by[k][0], a)
        check(f"true layer {k}: accuracy (%)", pct(by[k][0], by[k][1]), pct(a, b))
    ns = [r for r in scores if r["true_origin_layer"] != "Server"]
    check("non-Server correct", sum(int(r["correct"]) for r in ns), 51)
    check("non-Server accuracy (%)", pct(sum(int(r["correct"]) for r in ns), len(ns)), 29.7)
    check("model abstained on the reporter's claim", sum(1 for r in scores if not r["model_reporter_claim"]), 78)

    print("\n== 8. Per-bug captured output ==")
    capdir = os.path.join(ROOT, "repro", "captures")
    caps = sorted(f for f in os.listdir(capdir) if f.endswith(".txt"))
    check("per-bug capture files", len(caps), 72)
    missing, hdr = [], {}
    for f in caps:
        s = open(os.path.join(capdir, f), encoding="utf-8").read()
        if ("## 1. What was run" not in s or "## 3. What we captured" not in s
                or "## 4. Why it happens" not in s):
            missing.append(f)
        head = {}
        for line in s.splitlines():
            if not line.startswith("# "):
                break
            k, _, v = line[2:].partition(": ")
            head[k.strip()] = v.strip()
        hdr[int(f[6:10])] = head
    check("captures missing a mandatory section", len(missing), 0)
    check("captures whose header names another issue",
          sum(1 for n, h in hdr.items() if h.get("issue") != "#%d" % n), 0)
    check("capture headers carrying an origin layer",
          sum(1 for h in hdr.values() if h.get("origin_layer")), 72)
    hl = Counter(h["origin_layer"] for h in hdr.values() if h.get("origin_layer"))
    for k, v in [("Server", 38), ("Client", 21), ("Transport", 8), ("Host", 5)]:
        check(f"captures, origin_layer = {k}", hl[k], v)
    hc = Counter(h["exposure_channel"] for h in hdr.values() if h.get("exposure_channel"))
    for k, v in [("pushed-to-Server", 8), ("silent", 13), ("caller-exception", 18),
                 ("single-layer-genericised", 18), ("single-layer-correct", 12), ("registration", 3)]:
        check(f"captures, evidence class = {k}", hc[k], v)

    print("\n== 9. Per-bug evidence classification and run logs ==")
    mat = load("repro/evidence_matrix.csv")
    check("evidence-matrix rows", len(mat), 72)
    check("evidence-matrix rows that match a capture",
          len({r["issue"] for r in mat} & {"#%d" % n for n in hdr}), 72)
    check("evidence-matrix rows whose layer disagrees with the capture header",
          sum(1 for r in mat if r["origin_layer"] != hdr[int(r["issue"].lstrip("#"))]["origin_layer"]), 0)
    shapes = Counter(r["text_shape"] for r in mat)
    for k, v in [("stack", 40), ("block", 10), ("message", 14), ("none", 8)]:
        check(f"text shape = {k}", shapes[k], v)
    check("text shapes sum to the 72 reproduced bugs", sum(shapes.values()), 72)
    nonsilent = [r for r in mat if r["evidence_class"] != "silent"]
    check("non-silent bugs without a stack trace",
          sum(1 for r in nonsilent if r["text_shape"] != "stack"), 21)
    exc = {"caller-exception", "pushed-to-server", "registration-time"}
    check("  of which exception-type",
          sum(1 for r in nonsilent if r["text_shape"] != "stack" and r["evidence_class"] in exc), 13)
    check("every non-stack row carries a reason",
          sum(1 for r in mat if r["text_shape"] != "stack" and not r["gap_reason"]), 0)
    check("stack rows with neither a run log nor a reason",
          sum(1 for r in mat if r["text_shape"] == "stack"
              and not r["transcript"] and not r["gap_reason"]), 0)
    check("a gap reason on a row that has a run log",
          sum(1 for r in mat if r["transcript"] and r["gap_reason"]), 0)
    check("  rows that point at a run log", sum(1 for r in mat if r["transcript"]), 40)
    check("matrix rows pointing at a run log that is missing",
          sum(1 for r in mat if r["transcript"]
              and not os.path.exists(os.path.join(ROOT, r["transcript"]))), 0)
    check("matrix rows pointing at a capture that is missing",
          sum(1 for r in mat if r["capture"]
              and not os.path.exists(os.path.join(ROOT, r["capture"]))), 0)

    # the run logs: one file per bug whose traceback is complete
    tdir = os.path.join(ROOT, "repro", "transcripts")
    tfiles = sorted(glob.glob(os.path.join(tdir, "issue_*.txt")))
    check("files in repro/transcripts/", len(tfiles), 40)
    tbodies = {}
    for p in tfiles:
        s = open(p, encoding="utf-8", errors="replace").read()
        tbodies[int(os.path.basename(p)[6:10])] = s
    check("run logs whose header is not the 3-line form",
          sum(1 for s in tbodies.values()
              if not re.match(r"^# issue #\d+ -- reproduction run log\n# stack: complete, \d+ frames\n# -+\n", s)), 0)
    check("run logs with no traceback in the body",
          sum(1 for s in tbodies.values() if "Traceback (most recent call last):" not in s), 0)
    check("run logs whose body has no file/line frame",
          sum(1 for s in tbodies.values() if not re.search(r'File ".+", line \d+', s)), 0)
    check("run logs naming a pass, a date or a local path",
          sum(1 for s in tbodies.values()
              if re.search(r"re-?run|2025|2026|Gretel|kehuichen|Desktop", s, re.I)), 0)
    check("run logs in the folder that the matrix does not point at",
          sum(1 for n in tbodies
              if not next(r for r in mat if r["issue"] == "#%d" % n)["transcript"]), 0)
    check("frame counts in the header disagreeing with the body",
          sum(1 for s in tbodies.values()
              if int(re.search(r"# stack: complete, (\d+) frames", s).group(1))
              != len(re.findall(r'File ".+", line \d+', s))), 0)

    print()
    if FAIL:
        print("FAILED %d check(s): %s" % (len(FAIL), ", ".join(FAIL)))
        return 1
    print("All checks passed: every number above is reproducible from the files in this repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
