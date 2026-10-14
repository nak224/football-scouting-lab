# football-scouting-lab

A portfolio project for explainable football recruitment scouting. MVP v0.1
targets **professional recruitment scouts** exploring historical central
midfielders in **Wyscout Bundesliga 2017/18**. The total development target is
**25–40 hours**, including the foundation and scope-verification milestones.

## Current status

**Milestone 0b: MVP scope aligned and Wyscout feasibility reviewed.** The Python
src-layout package, one import smoke test, Ruff, pytest, and GitHub Actions from
0a are implemented. This milestone updates documentation and inspects external
samples; it does not implement ingestion, metrics, matching, or a UI.

There are no runtime dependencies or third-party datasets in Git. Direct Figshare
access is currently blocked by the cloud proxy. A small sample from a documented
GitHub mirror was inspected outside the checkout; primary release metadata and
license verification remain pending. See [data sources](docs/data-sources.md)
for the evidence, exact filenames, schema limitations, and access blockers.

## Finalized MVP v0.1 — planned

- Explore central midfielders and use structured scouting search and filters.
- Compare **Deep-Lying Playmaker** and **Ball-Winning Midfielder** profiles with
  customizable metric weights and visible explanations.
- Recommend replacements for a selected player within the eligible cohort.
- Present **style similarity**, **role fit**, and **team fit** separately.
- Provide lightweight team compatibility using a customizable lineup and explicit
  profile-balance assumptions.

The dataset is historical, so this is a recruitment-workflow demonstration rather
than a current transfer-market service. Broad Wyscout position labels do not
identify central midfielders or these two roles directly; cohort inclusion and
role definitions must be documented before scoring.

MVP v0.1 excludes LLMs, embeddings, semantic retrieval, FastAPI, PostgreSQL,
graph ML, authentication, and deployment. It also excludes additional leagues,
seasons, positions, and roles. Scouting search means structured filters and
transparent rankings, not natural-language or semantic search.

## Local setup

Requires Python 3.12 or newer. From the repository root on macOS or Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

Use another installed Python 3.12+ executable if needed. On Windows, create the
environment with `py -3.12 -m venv .venv` and activate it in PowerShell with
`.venv\Scripts\Activate.ps1`; the remaining commands are the same.

An import check is also available:

```sh
python -c "import football_scouting_lab"
```

CI installs the package with `python -m pip install ".[dev]"` and runs the same
lint, format, and test commands. Development tools are pytest and Ruff; setuptools
is the build backend.

## Milestones and budget

Only 0a and the 0b documentation/sample audit are implemented. The remaining
implementation is planned and requires review. These are budget allocations,
not recorded hours; the ranges sum to the total 25–40-hour target.

| Milestone | Scope | Budget | Status |
| --- | --- | --- | --- |
| 0a–0b | Foundation, MVP scope, and source verification | 3–5 h | Foundation and audit implemented; primary-source checks blocked |
| 1 | Resolve source/license checks; ingest, normalize, and validate the German season and cohort | 6–8 h | Planned |
| 2 | Auditable metrics, minutes eligibility, two role profiles, and custom weights | 5–8 h | Planned |
| 3 | Separate similarity/fit scores, replacement recommendations, and lineup compatibility | 5–8 h | Planned |
| 4 | Lightweight local player exploration and structured scouting search UI | 4–7 h | Planned |
| 5 | End-to-end checks, explanations, and portfolio documentation | 2–4 h | Planned |

See [architecture](docs/architecture.md) for the planned design and score
boundaries. Milestone 0b stops here; further implementation requires review.
