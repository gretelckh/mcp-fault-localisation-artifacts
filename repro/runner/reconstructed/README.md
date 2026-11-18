# Reconstructed reproductions

The 23 scripts in this folder, plus the three builders appended to
`repro_cases.py` (`case_jsonrpc_code`, `case_outputschema_mode`, `case_extra_arg`),
reconstruct 26 reproductions whose `harness_entry` originally pointed at scripts
that were **never released** (`runner/repro_pending/*`, `attempt_repro_external.py`,
`attempt_repro_targeted.py`). Those files never existed in the repository's git
history — they were one-off scripts the authors ran locally and did not ship.

Every script here is **RECONSTRUCTED** from two things that *are* in the release:

- the trigger recorded in section 1 of the corresponding `repro/captures/issue_XXXX.txt`;
- the output recorded in section 3 of that capture.

They use the real `mcp` 2.2.0 API (the version pinned in `requirements.txt`).
They are **not** the authors' original scripts and must not be cited as such.
Their purpose is to make every `harness_entry` resolve to a real, inspectable file
and to let a reader reproduce the documented behaviour on the pinned SDK.

Status of the 26 (see `data/broken_harness_entries.csv`):

| status | count | meaning |
|---|---:|---|
| `reconstructed_verified` | 18 | rebuilt and run against real mcp 2.2.0; the documented defect/behaviour reproduces |
| `reconstructed_as_evidence` | 6 | the capture embedded the original snippet verbatim, but it imports internal/renamed modules that do not exist in 2.2.0; archived as evidence, **not runnable** |
| `reconstructed_clean` | 2 | rebuilt, but 2.2.0 no longer raises (the capture itself already recorded the replay as clean) |

Run a script directly, e.g.:

```bash
python -m repro.runner.reconstructed.issue_2216
```

The capture's `harness_entry` is `reconstructed/issue_XXXX.py::repro_XXXX` for the
23 standalone scripts and `repro_cases.py::case_xxx` for the three builders.
