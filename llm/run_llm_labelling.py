#!/usr/bin/env python3
"""Reference implementation of the layer-labelling call used in the paper.

Two modes:

    --mode runtime   Study A. Reads repro/captures/issue_XXXX.txt, sends the captured output
                     with prompt P1, expects one layer token. Matches llm/outputs/studyA_arms_72.json.
    --mode issue     Study B. Reads llm/outputs/studyB_247.jsonl, sends title + body + excerpt
                     with prompt P4, expects a JSON object. Matches llm/outputs/studyB_247.jsonl.

Any OpenAI-compatible endpoint works:

    export LLM_BASE_URL="https://<host>/v1"
    export LLM_MODEL="<model-name>"
    export LLM_API_KEY="<key>"
    python llm/run_llm_labelling.py --mode issue --limit 5

Decoding is greedy (temperature 0), one call per bug, no system prompt, no few-shot examples —
the same settings as the study. The prompts are reproduced verbatim in llm/prompts.md.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = ["Host", "Client", "Server", "Transport"]

P1_HEAD = (
    "You are diagnosing a failure in a Model Context Protocol (MCP) pipeline, which connects an LLM "
    "(Host) to external tools (Server) via a Client and a Transport layer. Given only the raw error / "
    "SDK output below, predict the layer at which the fault ORIGINATED (the true root cause), not where "
    "it is merely reported.\n"
    "Choose exactly one of: Host, Client, Server, Transport.\n"
    "If the output shows a successful result (no error) yet you suspect a silent logical fault, still "
    "pick the layer you believe the fault originated in; if you genuinely cannot tell, pick the layer "
    "the message points to.\n"
    "Reply with a single token: Host, Client, Server, or Transport.\n\n"
    "RAW SDK OUTPUT:\n"
)

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


def study_a(limit):
    caps = sorted(os.listdir(os.path.join(ROOT, "repro", "captures")))
    caps = [c for c in caps if c.endswith(".txt")][: limit or None]
    for c in caps:
        text = open(os.path.join(ROOT, "repro", "captures", c), encoding="utf-8").read()
        raw = text.split("## captured return value", 1)[-1].split("##", 1)[0]
        reply = call(P1_HEAD + raw.strip(), 24)
        print(c, "->", parse_layer(reply))


def study_b(limit):
    path = os.path.join(ROOT, "llm", "outputs", "studyB_247.jsonl")
    with open(path, encoding="utf-8") as f:
        recs = [json.loads(line) for line in f if line.strip()]
    for rec in recs[: limit or None]:
        prompt = (P4_HEAD + "ISSUE TITLE:\n" + rec["title"]
                  + "\n\nISSUE BODY (truncated):\n" + rec["body"]
                  + "\n\nMOST ERROR-RELEVANT EXCERPT:\n" + rec.get("snippet", ""))
        reply = call(prompt, 200)
        got = parse_json(reply)
        print(rec["issue"], "->", got.get("our_layer"), "| truth:", rec.get("true_origin_layer"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["runtime", "issue"], required=True)
    ap.add_argument("--limit", type=int, default=0)  # 0 = all
    a = ap.parse_args()
    for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        if k not in os.environ:
            sys.exit("missing environment variable: " + k)
    (study_a if a.mode == "runtime" else study_b)(a.limit)
