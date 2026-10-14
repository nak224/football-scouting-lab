# football-scouting-lab

A portfolio project for explainable football recruitment scouting. MVP v0.1
targets **professional recruitment scouts** exploring historical central
midfielders in **Wyscout Bundesliga 2017/18**. The total development target is
**25–40 hours**, including the foundation and scope-verification milestones.

## Current status

**Milestone 1a: local Wyscout match metadata loading.** A standard-library loader
reads matches, players, and teams, preserves original IDs, validates consumed
structures and match-sheet relationships, and derives historical participation.
A small CLI summarizes the loaded season. Tests use explicitly synthetic records.
Ruff, pytest, and GitHub Actions remain configured. Events, minutes, metrics,
matching, and UI are not implemented.

There are no runtime dependencies or third-party datasets in Git. The 1a real-data
smoke test loaded cached raw metadata from the documented GitHub mirror outside
the checkout. Primary Figshare release metadata and license verification remain
pending following the blocked 0b probes. See [data sources](docs/data-sources.md)
for the actual smoke results, provenance, schema limitations, and access blockers.

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

## Load local match metadata

Supply these **extracted JSON files** together in a directory outside the
checkout, after reviewing their source and usage terms:

```text
/absolute/path/to/wyscout-metadata/
├── matches_Germany.json
├── players.json
└── teams.json
```

The loader does not download or extract files. No event or competition file is
required. With the environment activated, run:

```sh
python -m football_scouting_lab --data-dir /absolute/path/to/wyscout-metadata
```

The CLI counts loaded matches, teams referenced by those matches, and distinct
referenced players, including unused bench players. It separately reports players
recorded as appearing (starters or substitutes entering). Global metadata records
for unrelated competitions are not counted as season participants.

Missing files, malformed consumed structures, duplicate/invalid IDs, wrong season
IDs, unknown teams, and inconsistent squads/substitutions fail with exit code 2.
Positive match-sheet player IDs missing from `players.json` are retained and
reported as a warning; this known source gap does not fabricate player records
or change the counts, and the CLI exits 0. Historical affiliation always comes
from `teamsData`, never `currentTeamId`.

This validates the fields needed for 1a, not every optional source field, official
release authenticity, license terms, or complete season coverage. Small local
subsets are accepted; the loader does not require exactly 306 matches. All Git
fixtures are fictional and documented under `tests/fixtures/wyscout/`.

## Milestones and budget

0a, the 0b documentation/sample audit, and the 1a local metadata loader are
implemented. Remaining implementation requires review. These are budget
allocations, not recorded hours; the ranges sum to the 25–40-hour target.

| Milestone | Scope | Budget | Status |
| --- | --- | --- | --- |
| 0a–0b | Foundation, MVP scope, and source verification | 3–5 h | Foundation and audit implemented; primary-source checks blocked |
| 1 | Resolve source/license checks; ingest, normalize, and validate the German season and cohort | 6–8 h | 1a metadata loader implemented; primary-source checks, events, minutes, and cohort remain pending |
| 2 | Auditable metrics, minutes eligibility, two role profiles, and custom weights | 5–8 h | Planned |
| 3 | Separate similarity/fit scores, replacement recommendations, and lineup compatibility | 5–8 h | Planned |
| 4 | Lightweight local player exploration and structured scouting search UI | 4–7 h | Planned |
| 5 | End-to-end checks, explanations, and portfolio documentation | 2–4 h | Planned |

See [architecture](docs/architecture.md) for the planned design and score
boundaries. Milestone 1a stops here; further implementation requires review.
