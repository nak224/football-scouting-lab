# football-scouting-lab

A portfolio project for AI-assisted football scouting and player comparison.
The goal is to ingest football event data, calculate player-performance metrics,
explain player similarity and recommendations, and support semantic search
across scouting observations.

## Current status

**Milestone 0a: minimal project foundation.** Implemented: a Python src-layout
package, one import smoke test, Ruff and pytest configuration, and a GitHub
Actions workflow for linting, formatting, and tests on Python 3.12 and 3.13.
There are no runtime dependencies or scouting features yet. No third-party
football data is downloaded or included.

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

## Planned milestones

Only 0a is implemented. Later milestones are proposals, subject to review:

| Milestone | Scope | Status |
| --- | --- | --- |
| 0a | Package, tooling, CI, and foundation documentation | Implemented |
| 1 | Review data terms; ingest and normalize a small permitted dataset | Planned |
| 2 | Performance metrics and transparent player comparisons | Planned |
| 3 | Explainable player matching and recommendations | Planned |
| 4 | Semantic retrieval across scouting observations | Planned |
| 5 | API and UI for the validated workflows | Planned |

See [architecture](docs/architecture.md) for the proposed components and
[data sources](docs/data-sources.md) for data usage prerequisites.
Milestone 0a stops here; further implementation requires review.
