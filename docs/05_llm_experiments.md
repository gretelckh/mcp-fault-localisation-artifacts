# The two LLM studies

Both studies ask one question — *given this text, which layer did the fault start in?* — and differ
only in what text the model is allowed to see. Both use the same model, the same proxy, greedy
decoding (`temperature=0`), one call per bug, no few-shot examples, and no access to any label.

Model: DeepSeek-V4-Flash (FP8) through an OpenAI-compatible proxy. Prompts: `llm/prompts.md`.

---

## Study A — runtime text only (n = 72)

**Input.** The captured output of our own reproduction: the `CallToolResult` text when the call
returned, or the exception and traceback when one escaped. Nothing else — no title, no issue body,
no hint about which layer the call belongs to. This is what a monitoring tool or a developer at a
console sees.

**Output.** One token, `Host` / `Client` / `Server` / `Transport`. A second pass asks for
0–100 scores on each layer, used only for the ranked analysis.

**Three arms.** The prompt is identical across arms; only a block appended after the raw output
changes:

| Arm | Appended block | What it tests |
|---|---|---|
| `baseline` | none | what the surface text alone supports |
| `ruleclue` | one fixed paragraph per evidence class (`llm/outputs/clues_72.json`) | whether knowing the *mechanism of the class* helps |
| `analyst` | a layer-blind analyst note per class family | whether a human-written diagnosis procedure helps |

Both appended blocks are layer-blind: the words Host, Client, Server and Transport never appear in
them, and no bug number, file name or fix is mentioned. The clue is chosen by the bug's evidence
class, which is a property of the *output the model is looking at*, not of the answer.

**Result.**

| Arm | all 72 | non-Server (n = 34) |
|---|---|---|
| `baseline` | 41/72 = 56.9 % | 3/34 = 8.8 % |
| `ruleclue` | 46/72 = 63.9 % | 8/34 = 23.5 % |
| `analyst` | 40/72 = 55.6 % | 3/34 = 8.8 % |

Read it as: the model is good at recognising a Server fault and poor at everything else. On the
non-Server bugs it is right about one time in eleven at baseline. A rule-based clue nearly triples
that, a written analyst note does not move it.

Files: `llm/outputs/studyA_arms_72.json` (arm → list of bugs, each with `pred`, `rank`, `scores`,
`raw`).

---

## Study B — the full issue report (n = 247)

**Input.** Title, body (4,000 characters) and the most error-relevant excerpt (2,000 characters)
taken from the body. This is what a maintainer reads when triaging, and it is far more information
than Study A gives: the reporter's prose, their code, their traceback, sometimes their own guess at
the layer.

**Sample.** 247 of the 339: the 184 not-reproduced bugs that have error text, plus 63 reproduced
bugs that also have text. Bugs with no usable text at all (83) are excluded, because there is
nothing to show the model.

**Output.** A JSON object with the layer the model reads in the report (or `unclear`) and the
model's own origin layer.

**Result.**

| true layer | correct / n | accuracy |
|---|---|---|
| Server | 68 / 75 | 90.7 % |
| Client | 41 / 61 | 67.2 % |
| Transport | 8 / 81 | 9.9 % |
| Host | 2 / 29 | 6.9 % |
| `multi` | 0 / 1 | 0 % |
| **all** | **119 / 247** | **48.2 %** |
| **non-Server** | **51 / 172** | **29.7 %** |

The pattern is the same as Study A and stronger: the more text the model gets, the more it is
drawn to whichever layer the text mentions, and Server is the layer the text mentions most. On
Transport and Host — the two layers where the SDK's own reporting is weakest — the model is at
chance or below.

**Reading of the reporter.** The model reported an explicit claim about the layer in 169 of 247
cases and returned `unclear` in 78. That count is the model's reading, not an annotation: hand
coding of the same reports finds a verbal claim in only 53, a further 100 where the layer can be
inferred from an SDK path in the pasted traceback, and 94 with nothing at all. The field is
released as model output only — it is not evidence that the reporter named a layer.

Files: `llm/outputs/studyB_247.jsonl` (input + full reply + true layer),
`llm/outputs/studyB_scores_247.csv` (one row per bug, with `correct`).

---

## Reproducing the tables

```python
import csv
rows = list(csv.DictReader(open("llm/outputs/studyB_scores_247.csv")))
print(sum(int(r["correct"]) for r in rows), "/", len(rows))                    # 119 / 247
non = [r for r in rows if r["true_origin_layer"] != "Server"]
print(sum(int(r["correct"]) for r in non), "/", len(non))                      # 51 / 172
```

For Study A the truth has to be joined in from `data/active_bugs_339.csv`, because the `origin`
field stored inside `studyA_arms_72.json` carries an earlier labelling round. The join is one line:

```python
import json
truth = {int(r["issue"].lstrip("#")): r["origin_layer"]
         for r in csv.DictReader(open("data/active_bugs_339.csv"))}
arms = json.load(open("llm/outputs/studyA_arms_72.json"))
for arm, recs in arms.items():
    print(arm, sum(r["pred"] == truth[int(r["issue"])] for r in recs), "/", len(recs))
# baseline 41 / 72, ruleclue 46 / 72, analyst 40 / 72
```

## What these numbers do not show

* **Not a benchmark of the model.** One model, one prompt family, no tuning. The claim is about
  what the *text* supports, not about DeepSeek.
* **Not a human baseline.** The `analyst` arm is a written procedure, not a person.
* **Not independent of the codebook.** The classes the clue is keyed to were defined by the same
  people who labelled the bugs. The clue is layer-blind, but the class is not.
