# Anonymity statement

This repository accompanies a manuscript submitted for **double-blind review**. It was prepared so
that a reviewer can check every number without learning who wrote it.

## What was removed

| Removed | How | Where it appeared |
|---|---|---|
| Author names, affiliations, grant numbers | never written into the artefact | — |
| Absolute local paths (`C:\Users\<name>\...`, `/home/<name>/...`) | replaced with `<user>` | console logs, captured tracebacks, harness output |
| Machine account names embedded in tracebacks (`C:\Users\<acct>~1\...`) | replaced with `<user>` | captured tracebacks |
| The name of the institution that hosted the inference endpoint | replaced with *the institutional API proxy* | LLM experiment notes |
| E-mail addresses found in issue bodies | replaced with `<email-redacted>` | issue excerpts |
| Git author identity | commits are made with a neutral identity, no `Co-authored-by` trailer | `.git` |

## What was deliberately kept

* **GitHub issue numbers and URLs.** They are public identifiers of third-party reports, not of the
  authors, and they are what makes the dataset auditable. Removing them would make the artefact
  unverifiable.
* **Third-party user names that appear inside issue bodies** (e.g. a path or a handle inside a
  traceback pasted by the reporter). These identify the reporter, not the authors.
* **The pinned SDK version, operating system and Python version** used for reproduction. They are
  needed to interpret the results and are shared by thousands of projects.

## Self-check a reviewer can run

```bash
# no author name, institution name, e-mail domain or absolute home path should match
grep -rInE "Users\\\\[A-Za-z]|/home/[a-z]|/Users/[A-Za-z]|\.(edu|ac\.[a-z]{2})\b" . \
  | grep -v "^\./\.git/" | grep -v "C:\\\\Users\\\\<user>"
```

This should return nothing. The same check was run on the released files before packaging.

If you believe something in this repository still identifies the authors, please say so in the
review — the repository can be amended before publication.
