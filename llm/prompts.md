# Evaluation prompts

Both studies use one user message per request, a temperature of 0 and zero-shot prompts with DeepSeek-V4-Flash-FP8.

## Study A

The reference runner appends each diagnostic text in [inputs.jsonl](serverinfo_ablation/inputs.jsonl) to the exact [baseline prompt](serverinfo_ablation/prompt.txt). The rule-clue and label-only conditions append the relevant text from [the hint file](outputs/studyA_hints_72.jsonl). Each request has a 16-token response budget. The [Study A guide](STUDY_A_CONTROL.md) describes the scoring records, and the [serverInfo guide](serverinfo_ablation/README.md) describes that experiment.

## Study B

The [evaluation runner](run_llm_labelling.py) defines the P4 prompt and builds each request from the issue title, body and excerpt. The response budget is 200 tokens. The [Study B guide](STUDY_B_339.md) documents scoring and offline verification of the prompt hashes for all 339 inputs.
