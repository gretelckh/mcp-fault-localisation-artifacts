# Capture and runner provenance

The 72 capture records preserve the study ledger. Some linked scripts were reconstructed after the original study. data/broken_harness_entries.csv records the reconstruction status for the affected entries. A matching function symbol verifies the reference in the released file.

| Issue | Published reconstruction symbol | Status |
| --- | --- | --- |
| #76 | issue_0076.py::main | Recorded reconstruction |
| #326 | issue_0326.py::run | Recorded reconstruction |
| #915 | issue_0915.py::main | Recorded reconstruction |
| #3382 | issue_3382.py::main | Incomplete source fragment with no launcher |
| #3384 | issue_3384.py::main | Recorded reconstruction |
| #3434 | issue_3434.py::main | Recorded reconstruction |

Review of the linked issue and capture identified material differences in examples including #234 (the reported error flag was false and the capture flag is true), #507 (the report shows a POST failure and the capture shows a GET failure), #3578 (the report concerns an empty component set and the capture concerns duplicate tool registration), and #3579 (the report concerns resource and prompt routing and the capture concerns a missing tool). The files remain as records of the released runs and classifications. The symbol and numerical checks establish artifact consistency. Issue-level equivalence requires separate evidence.

[Local validation for #3578](validation/issue_3578.md) confirms the empty-component KeyError on mcp 2.2.0. The upstream tracker identifies #3578 as a duplicate of #3384. Both IDs remain in the scored ledger, and this check adds evidence for their shared mechanism.
