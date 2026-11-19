# Study A label-only control

The baseline uses the diagnostic text preserved in serverinfo_ablation/inputs.jsonl. The rule-clue condition appends a diagnostic hint selected by evidence class. The label-only condition appends the evidence-class label text. The prompts use one user message with temperature 0 and max_tokens 16.

The two archived label-only repeats each score 38/72 overall and 0/34 for non-Server bugs. Their per-bug predictions are in outputs/studyA_label_only_r2_72.jsonl and outputs/studyA_label_only_r3_72.jsonl.

The current reference runner uses the frozen Study A text and archived hint strings in outputs/studyA_hints_72.jsonl. For example:

    python llm/run_llm_labelling.py --mode runtime --condition label_only

The score verifier recomputes both repeats from the published ground truth.
