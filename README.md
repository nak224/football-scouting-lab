# football-scouting-lab

A portfolio project for explainable football recruitment scouting. MVP v0.1
targets **professional recruitment scouts** exploring historical central
midfielders in **Wyscout Bundesliga 2017/18**. The total development target is
**25–40 hours**, including the foundation and scope-verification milestones.

## Current status

**Milestone 3a: explainable style similarity and a basic replacement shortlist.**
Four existing rated measurements now support weighted player-to-player distance,
with raw values and per-feature explanations. Shortlists exclude the reference
player across all teams. Explicit position reviews and configurable sample
thresholds are reused from 2b; tactical role fits remain separate. Local examples
use the unchanged four-player positional-proxy cohort, not verified match-position
labels. See [similarity](docs/similarity.md) and [role fit](docs/roles.md).

The [2a metrics](docs/metrics.md) retain separate observed and matched per-90
samples. The raw-mirror audit found usable durations in **267/306 matches** and
positive minutes for **7,395/8,501 appearances**, with uneven team coverage.
The conservative estimator is unchanged. Broader recommendations, team
compatibility and UI remain planned. Tests use synthetic data; real examples
and source limits are documented.

There are no runtime dependencies or third-party datasets in Git. Figshare item
metadata now confirms CC BY 4.0, and the small mirror metadata files match its
published checksums. The original event binary redirects to a blocked S3 host;
the event smoke is **mirror-derived**, not verification of the whole original
event archive. Only the German member was downloaded via byte ranges. See
[data sources](docs/data-sources.md) for actual findings and checksum boundaries.

## Finalized MVP v0.1

Eligibility, role-fit and style-shortlist Python functions exist. The complete
user workflows and local interface below remain planned.

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
role definitions are application choices. The current small, explicitly reviewed
demonstration cohort is not an exhaustive or independently validated cohort.

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

## Optionally load events

To validate and summarize events, also supply `events_Germany.json` in the same
external directory. Keep the original football data outside Git. The loader does
not download files or extract full archives.

```sh
python -m football_scouting_lab --data-dir /absolute/path/to/wyscout-metadata --events
```

Without `--events`, the event file is neither required nor read. With it, the CLI
also reports event count, matches represented versus loaded metadata, and counts
by source event type ID and match period. A missing/invalid event file or invalid
match/team reference exits 2 before printing a partial summary.

The loader keeps original event IDs, type/subtype fields, tags, positions, periods,
timestamps, extra fields, and input order. It validates unique positive event IDs,
finite nonnegative `eventSec`, known period codes, tags, and finite coordinates.
Values outside the nominal 0–100 range are preserved and reported, not clipped
or used to reject the whole file; two such events occurred in the real smoke.
Empty tag/position arrays and blank subtypes are supported; source type/tag IDs
are not translated or restricted to a hard-coded catalogue. See the complete
consumed-field rules in [data sources](docs/data-sources.md).

Player ID `0` means unknown. Positive IDs missing from player metadata or absent
from the event's match-team lineup/bench are reported as nonfatal discrepancy
categories. Those events remain in the result and the CLI exits 0 with warnings.
Categories can overlap; they are not counts of distinct affected events when added
together. Event loading never changes metadata participation or appearance counts,
and does not itself derive minutes, rates, tactical positions, or metric scores. Event
subsets are accepted, without a claim of complete season/event coverage.

## Estimate one match's playing time

After loading the external files, use the small Python API:

```python
from football_scouting_lab.playing_time import estimate_playing_time
from football_scouting_lab.wyscout import load_events, load_season

metadata = load_season("/absolute/path/to/wyscout-metadata")
events = load_events("/absolute/path/to/wyscout-metadata", metadata)
result = estimate_playing_time(metadata, 2516739, events)
for row in result.players:
    print(row.match_id, row.team_id, row.player_id, row.minutes, row.warnings)
print(result.warnings)
```

Unused substitutes are excluded. These are match-level estimates, not official
minutes or season metrics. Missing/incomplete event periods, invalid timing, and
unresolved clock ambiguity can yield `None`; inspect both match and player
warnings. See [playing-time conventions](docs/playing-time.md) for halftime,
second-half/stoppage clocks, dismissals, and the conservative completeness rule.

## Export player metrics

Supply the same four local JSON files and choose a **new output path outside
Git** in an existing directory:

```sh
python -m football_scouting_lab --data-dir /absolute/path/to/wyscout-metadata \
  --metrics-csv /absolute/path/to/new-player-metrics.csv
```

This implies `--events`, prints coverage and excluded-match reasons, and writes
one row per original player ID and historical team. Existing files are never
overwritten. Metadata-only and `--events` commands keep their existing behavior.
The CSV separates `observed_*` counts from `rated_*` counts on the same matches
as `rated_minutes`; only the latter supply per-90 numerators. Match IDs, sample
sizes and warnings are included. Empty values mean unknown, not zero.

The Python API is `calculate_metrics(metadata, events)` from
`football_scouting_lab.metrics`; each returned season row retains its individual
player-match rows. Read [metrics](docs/metrics.md) for exact Wyscout definitions,
missing outcomes, source verification, real output and sampling bias. These are
partial-season observations across all positions, not reviewed midfielder
eligibility or rankings. The separate role API applies explicit review decisions
and eligibility thresholds as described below.

## Demonstrate midfielder role fit

Use the same external files after local setup:

```sh
python examples/midfield_roles.py --data-dir /absolute/path/to/wyscout-metadata
```

The example explicitly opts into four documented positional-proxy reviews,
defaults to 600 rated minutes and 60% appearance coverage, and prints both role
scores, contributions and exclusion counts. It accepts `--min-rated-minutes`
and `--min-appearance-coverage`; custom weights are available through the small
`score_role` Python API. Unreviewed players remain unverified. Missing required
measurements receive no score. These are cohort-relative fits, not league-wide
rankings or verified tactical positions. See [roles](docs/roles.md) for source
evidence, the normalization formula, a custom-weight example and actual smoke
results. The existing metadata/event/CSV commands keep their behavior.

## Demonstrate playing-style similarity

Use the same external files and reviewed demonstration cohort:

```sh
python examples/player_similarity.py --data-dir /absolute/path/to/wyscout-metadata
```

The default reference is Weigl `(224677, 2447)`. The example prints a style-only
shortlist, raw measurements, normalized differences, distance contributions,
coverage and runtime. Configure the reference, sample thresholds and limit with
the documented options; custom metric weights are available through
`compare_styles`. Missing/ineligible references fail explicitly, and incomplete
candidates receive no score. [Similarity documentation](docs/similarity.md)
explains the bounded score, constant/tiny cohorts, transfers and actual real-data
results. Scores are relative to this limited cohort and are not probabilities.

## Milestones and budget

0a, the 0b source audit, 1a metadata, 1b events, and 1c match-level playing-time
estimates, 2a covered player metrics, 2b eligibility/role fit and 3a style
similarity/basic shortlists are implemented. Remaining work requires review.
These are budget allocations, not recorded hours;
the ranges sum to the 25–40-hour target.

| Milestone | Scope | Budget | Status |
| --- | --- | --- | --- |
| 0a–0b | Foundation, MVP scope, and source verification | 3–5 h | Foundation and audit implemented; primary-source checks blocked |
| 1 | Resolve source/license checks; ingest, normalize, and validate the German season and cohort | 6–8 h | Metadata, raw-mirror event validation and match minutes implemented; original event-binary identity and broader cohort validation remain pending |
| 2 | Auditable metrics, minutes eligibility, two role profiles, and custom weights | 5–8 h | 2a–2b APIs and limited cohort demo implemented; production cohort and threshold calibration require review |
| 3 | Separate similarity/fit scores, replacement recommendations, and lineup compatibility | 5–8 h | 3a independent style similarity and basic shortlist implemented; combined workflows and team compatibility remain planned |
| 4 | Lightweight local player exploration and structured scouting search UI | 4–7 h | Planned |
| 5 | End-to-end checks, explanations, and portfolio documentation | 2–4 h | Planned |

See [architecture](docs/architecture.md) for the planned design and score
boundaries. Milestone 3a stops here; further implementation requires review.
