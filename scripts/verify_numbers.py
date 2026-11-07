#!/usr/bin/env python3
"""Recompute every dataset-level number reported in the paper, from the files in this repo.

Run from the repository root:

    python scripts/verify_numbers.py

No third-party packages are required. Every check prints the value computed from the
released files next to the value printed in the manuscript; the script exits with
status 1 if any of them disagree.
"""
import csv
import json
import os
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

    print("\n== 8. Reproduction artefacts ==")
    caps = [f for f in os.listdir(os.path.join(ROOT, "repro", "captures")) if f.endswith(".txt")]
    check("per-bug captured-output files", len(caps), 72)
    check("attempt log rows", len(load("repro/attempt_log.csv")), 350)
    check("verdict rows", len(load("repro/repro_verdicts_72.csv")), 72)

    print("\n== 9. Evidence coverage, bug by bug ==")
    idx = load("repro/captures_index.csv")
    check("index rows", len(idx), 72)
    check("bugs with a trigger or reproduction recipe", sum(1 for r in idx if r["has_trigger_code"] == "yes"), 72)
    check("bugs with an error text", sum(1 for r in idx if r["has_error_text"] == "yes"), 63)
    check("  of which captured at runtime", sum(1 for r in idx if r["error_text_source"] == "runtime"), 49)
    check("  of which quoted from the issue", sum(1 for r in idx if r["error_text_source"] == "issue text"), 14)
    check("  of which silent (no diagnostic)", sum(1 for r in idx if r["error_text_source"] == "none"), 9)
    check("bugs with a raw payload", sum(1 for r in idx if r["has_raw_payload"] == "yes"), 54)
    check("bugs with a console dump", sum(1 for r in idx if r["has_console_log"] == "yes"), 18)
    # every capture must actually carry the sections its index row advertises
    missing = []
    for r in idx:
        p = os.path.join(ROOT, "repro", "captures", "issue_%04d.txt" % int(r["issue"].lstrip("#")))
        if not os.path.exists(p):
            missing.append(r["issue"])
            continue
        s = open(p, encoding="utf-8").read()
        if "## 1. What was run" not in s or "## 4. Why it happens" not in s:
            missing.append(r["issue"])
    check("captures missing their mandatory sections", len(missing), 0)
    # one run-output file per reproduced bug, each with its provenance header
    outdir = os.path.join(ROOT, "repro", "run_output")
    names = sorted(os.listdir(outdir)) if os.path.isdir(outdir) else []
    kinds = {"console transcript": 0, "traceback excerpt": 0, "client return payload": 0}
    bad = []
    for r in idx:
        p = os.path.join(outdir, "issue_%04d.txt" % int(r["issue"].lstrip("#")))
        if not os.path.exists(p):
            bad.append(r["issue"])
            continue
        s = open(p, encoding="utf-8").read()
        if "# capture kind: " not in s or "# source: " not in s:
            bad.append(r["issue"])
            continue
        k = [l for l in s.splitlines() if l.startswith("# capture kind: ")][0].split(": ", 1)[1]
        if k in kinds:
            kinds[k] += 1
    check("per-bug run-output files", len(names), 72)
    check("run-output files carrying a provenance header", 72 - len(bad), 72)
    check("  console transcripts", kinds["console transcript"], 18)
    check("  traceback excerpts", kinds["traceback excerpt"], 5)
    check("  client return payloads", kinds["client return payload"], 49)

    print()
    if FAIL:
        print("FAILED %d check(s): %s" % (len(FAIL), ", ".join(FAIL)))
        return 1
    print("All checks passed: every number above is reproducible from the files in this repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
