# Study A serverInfo experiment

This experiment tests whether removing the serverInfo field changes origin-layer predictions under the Study A baseline prompt. It uses 72 reproduced bugs and compares the original diagnostic text, the text with only serverInfo removed, and a repeat request using identical original text. Thirty-six inputs contain the field. For the other 36, the three conditions have identical input text.

The completed run used CS/DeepSeek-V4-Flash-FP8, one user message per request, temperature 0, and max_tokens 16. Each condition ran three times per bug in shuffled order (seed 20261119), yielding 648 responses. The release stores one successful response per bug, condition, and repeat.

| Condition | Correct | Predicted Server |
| --- | ---: | ---: |
| Original (asis) | 123/216 | 183/216 |
| Field removed (stripped) | 123/216 | 183/216 |
| Original text re-queried (noop) | 123/216 | 183/216 |

Every bug received the same predicted layer across conditions and repeats. All nine bugs with serverInfo and a non-Server ground truth were predicted as Server in every repeat in all three conditions. This result describes the observed predictions for this model, prompt, and dataset.

## Files

- inputs.jsonl contains the Study A diagnostic text used in the experiment.
- prompt.txt is the exact prompt prefix. The input text is appended directly.
- responses.jsonl contains output text, parsed labels, reported model IDs, and SHA-256 hashes of the full prompts.
- run.py verifies the archive or submits a new run. The ground truth comes from data/active_bugs_339.csv, for scoring.

Run the offline verification with Python 3.10 or later:

    python llm/serverinfo_ablation/run.py verify

A new run requires the openai Python package and an OpenAI-compatible endpoint. Set LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL in your environment. To write or resume a separate response file:

    python llm/serverinfo_ablation/run.py run --output serverinfo_rerun.jsonl

New responses can vary with the model and endpoint.
