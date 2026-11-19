# Study B. Issue-report evidence for 339 bugs

The current run submitted a single user message per bug to CS/DeepSeek-V4-Flash-FP8 at temperature 0 and max_tokens 200. The message contains the P4 classification instructions, the issue title, up to 4,000 characters of the issue body, and an excerpt of up to 2,000 characters copied from the same issue body. The extraction rule prioritizes a traceback or exception, then an actual-behaviour or error section, then selected error messages. The excerpt slot was filled for 152 reports and empty for 187. The ground truth is used for scoring.

- outputs/studyB_339_input_manifest.jsonl holds the 339 issue IDs and the SHA-256 hash of each prompt. The prompts can be reconstructed from the released raw issue workbook using the runner and study_b_excerpt.py. The manifest hashes are derived from the frozen workbook and recorded request-construction code.
- outputs/studyB_339_predictions.jsonl contains the 339 archived predictions and model metadata. It exports the parsed predictions rather than the free-text justifications.
- outputs/studyB_scores_339.csv joins the predictions to the original ground truth labels.

Accuracy is 154/338 (45.6%). Non-Server accuracy is 66/240 (27.5%), with 102/240 predicted as Server. Two invalid predictions count as incorrect. The cross-layer bug #2564 received a Server prediction and is listed separately from the single-layer scores.

Run the score verifier with Python:

    python scripts/verify_numbers.py

Install openpyxl to verify each reconstructed input without querying the model:

    python llm/run_llm_labelling.py --mode verify-issue-inputs

To rerun the 339 requests, use mode issue with LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL configured locally.
