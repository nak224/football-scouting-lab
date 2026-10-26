# football-scouting-lab

A portfolio project for explainable football recruitment scouting. MVP v0.1
targets **professional recruitment scouts** exploring historical central
midfielders in **Wyscout Bundesliga 2017/18**. The total development target is
**25–40 hours**, including the foundation and scope-verification milestones.

## Quick start — no dataset download

Requires **Python 3.12+**. Clone this repository, then from its root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[ui]"
python -m streamlit run streamlit_app.py
```

Select **Load FICTIONAL demo** in the sidebar. All three sections work immediately:
search `Casey` in **Player explorer** and select the row to open a profile,
then try **Compare player** or **Similar players**. Change a role/weights in **Replacement
finder**, then swap a player in **Midfield simulator** and inspect feature changes.
Every demo player, club, event and result is **invented — NOT real Bundesliga
statistics**. Scores are calculated by the existing analytics, not canned UI values.

Genuine fictional-demo screenshots: [Player discovery](docs/screenshots/explorer-list.png)
and [Player profile](docs/screenshots/explorer-profile.png).
Also see [Similar players](docs/screenshots/explorer-similar.png) and the
[shared-radar comparison](docs/screenshots/explorer-comparison.png).

This MVP demonstrates explainable metrics, configurable recruitment priorities,
fixed-cohort comparisons, data validation and a usable local Python interface.
Its four-player samples are small; role fits are application templates and lineup
coverage is descriptive, not chemistry or future performance. Optional real-data
mode supports an external manual review file, or retains the four existing
positional-proxy reviews by default. Data-coverage limits remain visible.
See the [UI guide](docs/ui.md) and [data sources](docs/data-sources.md).
On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1`.

## Current status

**Integrated Player Explorer comparison.** A compact list supports player-name, league,
historical-team and original broad-position filters. Native row selection opens
a profile with rated statistics, per-feature percentiles and a radar chart.
Compare with the same position or all players; the comparison population uses
at least 600 rated minutes. Recruitment reviews remain separate from discovery.
**Compare player** searches a second player; **Similar players** suggests up to
five source-wide matches with one-click comparison. Both profiles share one
percentile population and radar. This descriptive similarity is separate from
the original Replacement Finder's style/role scores, which remain unchanged.

Real Wyscout loading remains available under **Use local Wyscout files**. No
real local dataset was accessible for a new redesign smoke. Earlier real
results below are historical audits, not new validation. See [actual checks and
limitations](docs/release-readiness.md). The fictional portfolio demonstration is
reviewable; real-data end-to-end validation and broader football validity remain
outstanding. No GitHub release has been created.

The [2a metrics](docs/metrics.md) retain separate observed and matched per-90
samples. The raw-mirror audit found usable durations in **267/306 matches** and
positive minutes for **7,395/8,501 appearances**, with uneven team coverage.
The conservative estimator is unchanged. Broader cohort validation remains
planned. Tests use synthetic data; real examples and source limits are documented.

The backend has no runtime dependencies; Streamlit and Plotly are in the optional `ui` extra.
There are no third-party datasets in Git. Earlier Figshare item
metadata checks confirmed CC BY 4.0, and the small mirror metadata files matched
published checksums. The original event binary redirected to a blocked S3 host;
the event smoke is **mirror-derived**, not verification of the whole original
event archive. Only the German member was downloaded via byte ranges. See
[data sources](docs/data-sources.md) for actual findings and checksum boundaries.

## Finalized MVP v0.1

Eligibility, role-fit, style-shortlist and combined-ranking Python functions exist.
A local exploration/replacement interface and a standalone hypothetical-trio
comparison API exist, with a separate simulator tab for the trio workflow.

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

CI installs the package with `python -m pip install ".[dev,ui]"` and runs the same
lint, format, and test commands, including synthetic Streamlit interaction tests.
Without the UI extra, backend tests run and Streamlit interaction tests skip.
Development tools are pytest and Ruff; setuptools is the build backend.

## Run the local scouting interface

From the repository root with the environment activated:

```sh
python -m pip install -e ".[ui]"
python -m streamlit run streamlit_app.py
```

For optional real-data mode, open **Use local Wyscout files** and supply a
directory outside Git containing **matches_Germany.json, players.json,
teams.json and events_Germany.json** in the sidebar, then select **Load season**.
The app does not download or bundle data. It binds to the local machine and
caches derived metrics so controls do not reprocess the raw events.

Filter **Player explorer** by name, league, historical team and broad source
position. The only supported league/season is Bundesliga 2017/18. Select a row
for the two-column profile; **Player list** returns to your filters. Raw values
sit beside a percentile radar; missing values remain unavailable. Broad positions
come from `players.json` `role.name`, never from recruitment reviews. Unknown
positions stay unknown. See [comparison method and limits](docs/ui.md#player-discovery-and-profiles).
Use **Compare player** or **Similar players** from a profile. Search Player B by
name, historical club and broad position, or select a suggestion. **Change player B**
keeps A fixed; **Player profile** and **Player list** preserve your navigation.
See [direct comparison and descriptive similarity](docs/ui.md#direct-player-comparison-and-similar-players).

In **Replacement finder**,
choose a reviewed reference and role, adjust priorities/weights/thresholds, then
inspect the separate scores and feature explanations. By default, four players have
reviewed demo positions; unverified players remain visible in exploration and
are excluded from recruitment ranking. Missing measurements stay unavailable.
In **Midfield simulator**, the default hypothetical trio is Thiago / Bayern,
Weigl / Dortmund and Keita / Leipzig, with Vidal / Bayern replacing slot 2.
Change the lineup, slot and four profile weights to inspect signed coverage
changes separately from recruitment scores. At least four distinct, eligible,
complete reviewed players are required; exclusions are explained in the tab.
See [UI setup, example workflow, cache behavior and smoke results](docs/ui.md).

### Optional externally reviewed cohort

In **Use local Wyscout files**, set **Optional local review JSON file** and click
**Load season**. A file replaces the default reviews; omitted player/team pairs
remain unverified. `[]` intentionally includes nobody. Blank restores defaults.
This schema example is **entirely fictional**, not a verified football review and
not configuration for the built-in fictional demo:

```json
[
  {
    "player_id": 101,
    "team_id": 201,
    "status": "included",
    "evidence": "synthetic:documentation-only",
    "note": "Fictional schema example, not real position evidence."
  }
]
```

Use actual original IDs and independently reviewed evidence for your own local
data. Each pair must exist in historical match sheets with a known team;
missing global player metadata is flagged separately rather than invalidating
match-sheet evidence. A review never creates an appearance or metric sample;
`currentTeamId` is never affiliation evidence. Status is `included` or `excluded`;
both require nonblank evidence and note. Duplicate decisions and unknown pairs
fail clearly. Transfer team rows need separate decisions. Keep files outside Git.
The UI shows review counts, evidence, eligibility and exclusion reasons. Revisions
are read on the next interaction without recalculating events; **Force source
reload** explicitly recalculates unchanged source files. External reviews never
apply to fictional data. See [review-file details](docs/ui.md#external-manual-reviews-5b).

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

## Demonstrate combined replacement ranking

```sh
python examples/replacement_ranking.py --data-dir /absolute/path/to/wyscout-metadata
```

This uses Weigl as reference, Deep-Lying Playmaker, `--style-priority 0.5` and
limit 3. Select the other template with `--role ball_winning_midfielder`; adjust
priority within [0, 1], reference, thresholds and limit using the example options.
The `rank_replacements` API also accepts independent metric weights for each
component. It requires both scores even at priorities 0 and 1, retains separate
normalization contexts and never combines transferred players' statistics.
See [recruitment](docs/recruitment.md) for the formula, source explanations,
exclusion rules, custom-weight example and actual smoke results. No team fit is
included in this ranking.

## Demonstrate a hypothetical midfield replacement

```sh
python examples/midfield_lineup.py --data-dir /absolute/path/to/wyscout-metadata
```

This uses the existing four reviews and default eligibility thresholds. The
hypothetical trio is Thiago / Bayern, Weigl / Dortmund and Keita / Leipzig, with
Vidal / Bayern replacing slot 2. This is not a historical starting XI or evidence
that players from different clubs played together. The comparison reports fixed
feature scales, raw means, coverage changes, normalized weights and samples.
See [formula, custom-weight Python example and verification limits](docs/team-fit.md).
Real local data was unavailable for a new 4b1 smoke; tests use synthetic records.
The 4b2 simulator calls this same comparison API; recruitment scores are unchanged.

## Milestones and budget

0a, the 0b source audit, 1a metadata, 1b events, and 1c match-level playing-time
estimates, 2a covered player metrics, 2b eligibility/role fit and 3a style
similarity/basic shortlists, 3b combined replacement ranking, 4a local scouting UI,
4b1 standalone hypothetical midfield comparison, 4b2 simulator integration and
5a fictional portfolio demo/workflow checks, 5b external review configuration and
5c release-quality review are implemented.
Remaining work requires review.
These are budget allocations, not recorded hours;
the ranges sum to the 25–40-hour target.

| Milestone | Scope | Budget | Status |
| --- | --- | --- | --- |
| 0a–0b | Foundation, MVP scope, and source verification | 3–5 h | Foundation and audit implemented; primary-source checks blocked |
| 1 | Resolve source/license checks; ingest, normalize, and validate the German season and cohort | 6–8 h | Metadata, raw-mirror event validation and match minutes implemented; original event-binary identity and broader cohort validation remain pending |
| 2 | Auditable metrics, minutes eligibility, two role profiles, and custom weights | 5–8 h | 2a–2b APIs and limited cohort demo implemented; production cohort and threshold calibration require review |
| 3 | Separate similarity/fit scores, replacement recommendations, and lineup compatibility | 5–8 h | 3a–3b style similarity and adjustable combined replacement ranking implemented; hypothetical trio API implemented in 4b1 with separate 4b2 UI |
| 4 | Lightweight local player exploration and structured scouting search UI | 4–7 h | 4a explorer/replacement finder plus 4b2 midfield simulator implemented; unchanged four-player demo |
| 5 | End-to-end checks, explanations, and portfolio documentation | 2–4 h | 5a–5c demo, external reviews and final validation implemented; real-data smoke remains unavailable locally |

See [architecture](docs/architecture.md) for the design and score boundaries and
the [original v0.1 readiness checklist](docs/release-readiness.md) for dated
completed, partially verified and blocked checks.

The subsequent Player Explorer UX redesign adds discovery/profiles and a separate
statistical comparison view, with no new football metrics or recruitment algorithms.
