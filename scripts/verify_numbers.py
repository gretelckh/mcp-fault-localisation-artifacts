#!/usr/bin/env python3
"""Recompute every dataset-level number reported in the paper, from the files in this repo.

Run from the repository root:

    python scripts/verify_numbers.py

No third-party packages are required. Every check prints the value computed from the
released files next to the value printed in the manuscript; the script exits with
status 1 if any of them disagree.
"""
import ast
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

    for repeat in (2, 3):
        path = os.path.join(ROOT, "llm", "outputs", f"studyA_label_only_r{repeat}_72.jsonl")
        with open(path, encoding="utf-8") as stream:
            control = list(map(json.loads, stream))
        check(f"label-only control r{repeat}: IDs match", {r["issue"] for r in control} == {int(r["issue"].lstrip("#")) for r in repro}, True)
        check(f"label-only control r{repeat}: correct", sum(r["prediction"] == truth[r["issue"]] for r in control), 38)
        check(f"label-only control r{repeat}: non-Server correct",
              sum(r["prediction"] == truth[r["issue"]] for r in control if truth[r["issue"]] != "Server"), 0)
    check("Study A non-Server predicted Server",
          sum(r["pred"] == "Server" for r in arms["baseline"] if truth[int(r["issue"])] != "Server"), 23)

    print("\n== 7. Study B: 339 inputs, 338 single-layer scores ==")
    scores = load("llm/outputs/studyB_scores_339.csv")
    output_file = os.path.join(ROOT, "llm", "outputs", "studyB_339_predictions.jsonl")
    with open(output_file, encoding="utf-8") as stream:
        predictions = {r["issue"]: r for r in map(json.loads, stream)}
    check("Study B output IDs match the corpus", set(predictions) == set(truth), True)
    check("Study B input count", len(scores), 339)
    check("Study B score IDs match the corpus", {int(r["issue"]) for r in scores} == set(truth), True)
    check("score ground truth and predictions match the source tables",
          all(r["ground_truth"] == truth[int(r["issue"])]
              and r["predicted_layer"] == (predictions[int(r["issue"])]["layer"] or "")
              and int(r["valid"]) == predictions[int(r["issue"])]["valid"]
              and int(r["scored"]) == (r["ground_truth"] != "multi")
              and r["correct"] == (str(int(r["ground_truth"] == r["predicted_layer"])) if r["scored"] == "1" else "")
              for r in scores), True)
    eligible = [r for r in scores if r["scored"] == "1"]
    check("single-layer scores", len(eligible), 338)
    check("correct single-layer predictions", sum(int(r["correct"]) for r in eligible), 154)
    check("invalid predictions counted as incorrect", sum(int(r["valid"]) == 0 and r["correct"] == "0" for r in eligible), 2)
    check("cross-layer issue and prediction",
          [(r["issue"], r["predicted_layer"]) for r in scores if r["scored"] == "0"], [("2564", "Server")])
    for layer, expected in {"Server": (88, 98), "Client": (50, 84), "Transport": (13, 105), "Host": (3, 51)}.items():
        group = [r for r in eligible if r["ground_truth"] == layer]
        check(f"Study B {layer}: correct, total", (sum(int(r["correct"]) for r in group), len(group)), expected)
    non_server = [r for r in eligible if r["ground_truth"] != "Server"]
    check("Study B non-Server: correct, total", (sum(int(r["correct"]) for r in non_server), len(non_server)), (66, 240))
    check("Study B non-Server predicted Server", sum(r["predicted_layer"] == "Server" for r in non_server), 102)

    print("\n== Figure census: archived aggregate consistency ==")
    leaves = load("data/figure_census_aggregate.csv")
    classes = ("names_file_and_exception", "generic_message", "neighbouring_layer", "silent", "hang", "never_started")
    actual_groups = Counter((r["origin_layer"], "reproduced" if r["reproduction_status"] == "reproduced" else "unreproduced") for r in active)
    figure_groups = {(r["origin_layer"], r["status"]): int(r["total"]) for r in leaves}
    check("figure branch sizes match the case ledger", figure_groups == dict(actual_groups), True)
    check("each figure group equals the sum of its leaves", all(sum(int(r[k]) for k in classes) == int(r["total"]) for r in leaves), True)
    totals = [sum(int(r[k]) for r in leaves) for k in classes]
    check("archived figure class totals", totals, [94, 89, 60, 39, 14, 43])
    check("archived Localisable, C1, C2 and C3 totals",
          [totals[0], totals[1] + totals[2], totals[3] + totals[4], totals[5]], [94, 149, 53, 43])

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

    print("\n== 10. Reproducibility: harness entries resolve ==")
    # Build the set of builders actually defined in the released runner files.
    runner_dir = os.path.join(ROOT, "repro", "runner")
    runner_files = sorted(f for f in os.listdir(runner_dir) if f.endswith(".py"))
    symbols = {}
    for fname in runner_files:
        with open(os.path.join(runner_dir, fname), encoding="utf-8") as stream:
            symbols[fname] = {node.name for node in ast.parse(stream.read()).body
                              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def resolves(entry):
        filename, separator, symbol = entry.partition("::")
        return bool(separator and symbol in symbols.get(os.path.basename(filename), set()))

    unresolved = []
    per_issue_count = 0
    for f in caps:
        s = open(os.path.join(capdir, f), encoding="utf-8").read()
        entry = next((l.partition(": ")[2].strip() for l in s.splitlines()
                      if l.startswith("# harness_entry:")), "")
        if re.match(r"issue_\d+\.py::", entry):
            per_issue_count += 1
        if not resolves(entry):
            unresolved.append((f, entry))
    check("capture harness entries that fail to resolve", len(unresolved), 0)
    for f, entry in unresolved:
        print("      %s -> %s" % (f, entry))
    check("harness entries pointing at a per-issue script", per_issue_count, 23)

    print("\n== 11. Reproducibility: per-bug transport recorded ==")
    tpath = os.path.join(ROOT, "data", "transport_72.csv")
    check("transport table present", os.path.exists(tpath), True)
    if os.path.exists(tpath):
        trows = load("data/transport_72.csv")
        check("transport rows", len(trows), 72)
        check("transport table covers the 72 reproduced bugs",
              {r["issue"] for r in trows} == {"#%d" % n for n in hdr}, True)
        known = {"sse", "stdio", "stdio+sse", "streamable-http", "not_applicable"}
        check("transport values drawn from the allowed set",
              sum(1 for r in trows if r["transport"] not in known), 0)
        check("transport rows with no unknown left",
              sum(1 for r in trows if r["transport"] == "unknown"), 0)
        tc = Counter(r["transport"] for r in trows)
        for k, v in [("streamable-http", 56), ("sse", 3), ("stdio", 4),
                     ("stdio+sse", 1), ("not_applicable", 8)]:
            check("transport = %s" % k, tc[k], v)
        check("all 72 rows classified", sum(tc.values()), 72)

    print()
    if FAIL:
        print("FAILED %d check(s): %s" % (len(FAIL), ", ".join(FAIL)))
        return 1
    print("All checks passed: every number above is reproducible from the files in this repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
