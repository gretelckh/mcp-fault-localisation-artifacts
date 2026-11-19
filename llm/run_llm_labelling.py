#!/usr/bin/env python3
"""Run Study A using frozen diagnostic text or Study B using the 339 issue reports.

Set LLM_BASE_URL, LLM_MODEL, and LLM_API_KEY to rerun either study.
Use --mode verify-issue-inputs to check Study B prompt hashes offline.
Study B input reconstruction requires openpyxl.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = ["Host", "Client", "Server", "Transport"]

P4_HEAD = (
    "You are diagnosing a fault in a Model Context Protocol (MCP) pipeline, which connects an LLM "
    "(HOST) to external tools (SERVER) via a CLIENT and a TRANSPORT layer. Below is a real GitHub issue "
    "from the modelcontextprotocol/python-sdk repo (title + body + the most error-relevant excerpt).\n\n"
    "Please output a single JSON object with exactly these keys:\n"
    '  "reporter_claim_layer": where the ISSUE REPORTER themselves claims the fault is located. One of '
    '"Host", "Client", "Server", "Transport", or "unclear" if the reporter does not explicitly state a layer.\n'
    '  "our_layer": the layer where you (the analyser) believe the fault ORIGINATED (the true root cause), '
    'NOT where it merely surfaces. One of "Host", "Client", "Server", "Transport".\n'
    '  "reason": a brief justification (<= 40 words).\n\n'
    "Reply with ONLY the JSON object.\n\n"
)


def call(prompt, max_tokens):
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    url = base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")
    body = json.dumps({
        "model": os.environ["LLM_MODEL"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.environ["LLM_API_KEY"],
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"] or ""


def parse_layer(text):
    m = re.search(r"\b(Host|Client|Server|Transport)\b", text or "")
    return m.group(1) if m else "Unknown"


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


def read_jsonl(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def study_a(limit, condition):
    folder = os.path.join(ROOT, "llm", "serverinfo_ablation")
    with open(os.path.join(folder, "prompt.txt"), encoding="utf-8") as stream:
        prefix = stream.read()
    hints = {r["issue"]: r for r in read_jsonl(os.path.join(ROOT, "llm", "outputs", "studyA_hints_72.jsonl"))}
    for rec in read_jsonl(os.path.join(folder, "inputs.jsonl"))[:limit or None]:
        prompt = prefix + rec["surface_text"]
        if condition != "baseline":
            prompt += "\n\nDIAGNOSTIC GUIDANCE (direction only, does NOT state the answer):\n" + hints[rec["issue"]][condition]
        reply = call(prompt, 16)
        print(json.dumps({"issue": rec["issue"], "layer": parse_layer(reply), "raw": reply}))


def study_b_inputs():
    import hashlib
    from openpyxl import load_workbook
    from study_b_excerpt import excerpt

    folder = os.path.join(ROOT, "llm", "outputs")
    manifest = {r["issue"]: r for r in read_jsonl(os.path.join(folder, "studyB_339_input_manifest.jsonl"))}
    workbook = load_workbook(os.path.join(ROOT, "data", "gh_issues_raw_2026-11-09.xlsx"), read_only=True)
    try:
        rows = {r[0]: (str(r[1]), str(r[12] or "")) for r in workbook["issues_raw"].values if r[0] in manifest}
    finally:
        workbook.close()
    if len(rows) != len(manifest):
        raise ValueError("Workbook does not cover the archived Study B inputs")
    inputs = []
    for issue, (title, body) in sorted(rows.items()):
        prompt = (P4_HEAD + "ISSUE TITLE:\n" + title
                  + "\n\nISSUE BODY (up to 4000 characters):\n" + body[:4000]
                  + "\n\nMOST ERROR-RELEVANT EXCERPT:\n" + excerpt(body))
        if hashlib.sha256(prompt.encode("utf-8")).hexdigest() != manifest[issue]["prompt_sha256"]:
            raise ValueError(f"Study B prompt reconstruction mismatch for issue {issue}")
        inputs.append((issue, prompt))
    return inputs


def study_b(limit):
    for issue, prompt in study_b_inputs()[:limit or None]:
        reply = call(prompt, 200)
        print(json.dumps({"issue": issue, "layer": parse_json(reply).get("our_layer"), "raw": reply}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["runtime", "issue", "verify-issue-inputs"], required=True)
    ap.add_argument("--limit", type=int, default=0)  # 0 = all
    ap.add_argument("--condition", choices=["baseline", "rule_clue", "label_only"], default="baseline")
    a = ap.parse_args()
    if a.mode == "verify-issue-inputs":
        print(f"Reconstructed and checked {len(study_b_inputs())} Study B prompts.")
        sys.exit()
    for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        if k not in os.environ:
            sys.exit("missing environment variable: " + k)
    if a.mode == "runtime":
        study_a(a.limit, a.condition)
    else:
        study_b(a.limit)
