# File map

Every file in the package, with its size and what it is for. Rows = data rows, excluding the
header.

```
mcp-fault-artifacts/
├── README.md                      start here
├── ANONYMITY.md                   what was redacted (paths, e-mails), and how to self-check
├── LICENSE / LICENSE-DATA         MIT (code) / CC BY 4.0 (data, docs)
├── requirements.txt               only needed for the reproduction harness
├── data/
│   ├── screening_1343.csv         1,343 rows · the whole mined issue pool + keyword label
│   ├── screening_funnel.csv          7 rows · 1,343 → 339 with the rule at each stage
│   ├── active_bugs_339.csv         339 rows · the analysed dataset, 26 columns
│   ├── evidence_class_339.csv      339 rows · one row per bug: layer, evidence class, tier
│   └── blocking_gaps_83.csv         83 rows · why the 83 evidence-poor reports are blocked
├── repro/
│   ├── README.md                  how to read and re-run a case
│   ├── runner/                    the harness + the case definitions (5 files)
│   ├── captures/issue_XXXX.txt    72 files · one per reproduced bug: trigger, captured output, layer analysis
│   ├── captures_index.csv         72 rows · which kinds of evidence exist for which bug
│   ├── run_output/issue_XXXX.txt  72 files · one per bug: what that run printed, verbatim
│   ├── raw/                       54 files · the raw payload each run wrote to disk
│   ├── raw_map.csv                54 rows · issue number → raw payload file name
│   ├── logs/NNNN.txt              53 files · console dumps (30 of them belong to the 72)
│   ├── repro_verdicts_72.csv      72 rows · the verdict table
│   └── attempt_log.csv           350 rows · every attempt, including the failures
├── llm/
│   ├── prompts.md                 the four prompts, verbatim
│   ├── run_llm_labelling.py       reference implementation of the labelling call
│   └── outputs/
│       ├── studyA_arms_72.json    Study A · 3 arms × 72 bugs, with scores
│       ├── clues_72.json          the clue paragraph each bug received in the ruleclue arm
│       ├── studyB_247.jsonl       Study B · 247 model responses + the input shown
│       └── studyB_scores_247.csv  Study B · flattened, one row per bug
├── docs/
│   ├── 01_file_map.md             this file
│   ├── 02_codebook.md             the labels and the rules that produce them
│   ├── 03_screening_protocol.md   how the pool was filtered
│   ├── 04_reproduction_protocol.md environment, harness, what "reproduced" means
│   ├── 05_llm_experiments.md      the two studies and their results
│   ├── 06_data_dictionary.md      column-by-column reference
│   └── 07_results_snapshot.md     all headline numbers on one page
└── scripts/
    └── verify_numbers.py          78 checks, no dependencies
```

## Where to look for a given question

| Question | File |
|---|---|
| Is issue #1234 in the dataset, and what is it? | `data/active_bugs_339.csv`, column `issue` |
| What happened when you ran #1234? | `repro/run_output/issue_1234.txt` (output) · `repro/captures/issue_1234.txt` (full record) |
| Which bugs have a console log / raw payload? | `repro/captures_index.csv` |
| Why is #1234 not in the 72? | `data/active_bugs_339.csv`, column `not_reproduced_reason`; `repro/attempt_log.csv` |
| How do you decide a bug originates in Transport? | `docs/02_codebook.md`, rules R1–R6 |
| What exactly did you show the model? | `llm/prompts.md` and the `body` field in `llm/outputs/studyB_247.jsonl` |
| Where does 48.2 % come from? | `llm/outputs/studyB_scores_247.csv`, column `correct` |
| Can I check all of it at once? | `python scripts/verify_numbers.py` |
