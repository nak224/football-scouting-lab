# Architecture

## Implemented through Milestone 5c

The project contains one Python package under `src/football_scouting_lab/`.
`wyscout.py` loads three local JSON arrays: `matches_Germany.json`, `players.json`,
and `teams.json`. `load_season(data_dir)` returns a `SeasonMetadata` object with
the original records indexed by `wyId` and a tuple of `PlayerParticipation` facts.
`python -m football_scouting_lab --data-dir ...` summarizes those records.

`load_events(data_dir, metadata)` separately reads `events_Germany.json` and
returns `SeasonEvents`: raw records indexed by the source `id` and three sets of
event IDs identifying unknown players, missing player metadata, and players not
listed in the corresponding match-team squad. The latter two categories can
overlap. Player ID `0` belongs only to the unknown category. `--events` enables
loading and summary output; without it, the event file is not read.

Event IDs, type/subtype fields, tags, coordinates, periods, timestamps, extra
fields, and source order are retained. Consumed fields, unique event IDs, and
match/team references are validated. An event's team must belong to that specific
loaded match. Player discrepancies are nonfatal and do not alter the event,
metadata affiliation, or match-sheet appearance flags. Finite coordinate outliers
have a separate diagnostic set and remain unchanged. The raw German mirror smoke
identified two outliers; rejecting the entire file at the nominal bounds was
corrected in 1c. No event sorting or coordinate transformation is performed.

`playing_time.py` adds `estimate_playing_time(metadata, match_id, events=None)`.
It returns one match's player minutes, preserved identities, observed period
endpoints, and explicit match/player warnings. It uses match sheets and event
period/card timestamps, excludes unused substitutes, and never fills missing
timing with 90 minutes. Ambiguous or unusable timing produces `None`. See
[playing-time conventions](playing-time.md) for the scoped regular-time rules.

`metrics.py` adds `calculate_metrics(metadata, events)`. It groups raw records
by original player ID and historical team, retaining player-match counts,
minutes, sample sizes and warnings. All observed counts remain separate from
counts on positive-minute appearances; only the latter supply per-90 rates.
The existing estimator is unchanged. Missing outcomes, unknown actors and events
without recorded appearances are reported rather than imputed. The CLI's optional
`--metrics-csv` loads events and writes a new external CSV. See
[metric definitions and the season coverage audit](metrics.md).

`roles.py` adds explicit player/team position reviews and configurable rated-minute
and appearance-coverage thresholds. `score_role` reuses the 2a rated metrics,
excludes incomplete candidates, and returns weighted empirical percentile fits
with measurements, contributions, samples and reference IDs. No broad Midfielder
label or current club is used to infer central midfield. The opt-in local example
contains four documented, manually reviewed positional-proxy entries; expanding
or validating that demonstration cohort remains review work. See [roles](roles.md).

`similarity.py` reuses eligibility assessments and the existing rated metrics,
without consuming role scores or role weights. `compare_styles` fits a shared
min/max scale on complete eligible rows, calculates weighted absolute feature
distances and retains per-feature explanations and exclusions. A missing or
ineligible reference fails explicitly. `replacement_shortlist` ranks the style
results and removes the reference player across all teams before limiting output.
The local demo reuses the same four reviews; [similarity](similarity.md) documents
tiny/constant cohorts, the score transformation, sample context and real smoke.

`recruitment.py` composes `compare_styles` and `score_role` once each on the same
input, joins original player/team rows, and ranks complete non-self candidates
by an adjustable weighted sum (default 50/50). It retains both source results,
their separate normalization contexts, explanations, contributions and exclusions.
Missing scores are never zero-filled, even at priority endpoints. Historical
team statistics stay separate. See [recruitment](recruitment.md) for the local
four-player demo, configuration and real smoke; source algorithms are unchanged.

`streamlit_app.py` adds one local Streamlit process with player exploration and
replacement controls. It calls `rank_replacements`; no scoring algorithm moves
into the frontend. `ui_data.py` prepares fresh presentation rows from existing
metrics. `demo_cohort.py` shares the unchanged four reviews with the examples.
Streamlit is an optional `ui` extra; the backend remains dependency-free.

The data cache stores derived metrics and display names, not raw events. Its
key includes the absolute directory and four file sizes/modification times.
`Force source reload` explicitly clears it on form submission. Copy-on-read isolates nested records; UI
helpers never mutate loaded results. Every control rerun uses this snapshot,
then performs only filtering/presentation and the existing tiny-cohort ranking.
There is no disk cache, external service or automatic data download. See
[local UI](ui.md) for startup, limitations and actual smoke measurements.

`team_fit.py` adds an independent `compare_midfield` function for a hypothetical
4-3-3 midfield trio. A caller-selected complete cohort supplies one min/max scale
per existing passing/defending feature for both lineups. Results retain ordered
player/team IDs, individual values, equal-player means, feature maxima on the
normalized scales, signed weighted coverage changes and source samples/warnings.
It neither infers tactical slots nor modifies style, role or recruitment scores.
The local example uses the unchanged four reviews and explicitly hypothetical
players from different clubs. See [formulas and limitations](team-fit.md).
The separate Midfield simulator tab (4b2) reuses cached metrics, existing
eligibility/profile checks and this comparison API. It fixes the complete reviewed
cohort before lineup/weight selection and reports exclusions. No additional
dependency is introduced.

`fictional_data.py` adds a deterministic, self-contained portfolio fixture (5a).
It generates new local raw-format JSON in a temporary directory, then reuses all
existing loaders and analytics. `ScoutingData.fictional` selects a separate set of
four fictional eligibility assignments; real reviews and source IDs are unchanged.
Versioned markers retain fictional labeling if those files are loaded manually,
and mixed marked/unmarked seasons or unknown/inconsistent versions fail explicitly. The UI offers a prominent
fictional-demo button and a separate local-file form, with independent caches and
source-switch resets. No scoring algorithm, dependency or real cohort entry is added.

`cohort_reviews.py` (5b) loads optional local manual included/excluded decisions
with evidence and notes. `ui_data.py` validates their original player/team IDs
against historical match-sheet pairs retained in the derived cache; no current
club or broad position label supplies affiliation/position evidence. Reviews are
applied after cached metrics, replacing default reviews without modifying source
snapshots or scoring formulas. Review changes update eligibility, ranking and
simulator selections without event recalculation. Fictional assignments remain
separate. Evidence is user-supplied, not independently verified by the app; see
[review schema and interpretation](ui.md#external-manual-reviews-5b).
The 5c review keeps match-sheet pairs even when global player metadata is absent,
reports that discrepancy separately and leaves no-sample entries ineligible.
See the [release checklist](release-readiness.md) for actual verification boundaries.

Participation records preserve match, team, and player IDs and distinguish
starting, being listed on the bench, entering, and leaving as a substitute.
Being an unused substitute is not counted as an appearance. Team affiliation is
derived per match from `teamsData`; `currentTeamId` is retained only as opaque raw
metadata. A player can legitimately represent different teams in different matches.

Consumed fields, season IDs, uniqueness, home/away teams, squad membership, and
substitution list order are validated. Missing player metadata is exposed through
`missing_player_ids` without synthesizing records; unknown teams and structural
inconsistencies raise `MetadataError`. Extra fields remain unchanged and are not
fully validated. A subset can load without claiming complete season coverage.

Synthetic fixtures and focused tests cover metadata/event loading, validation,
player discrepancies, historical affiliation, participation, metric definitions,
matched denominators, transfers, uncertainty and CLI/export modes.
GitHub Actions installs the optional UI extra and runs Ruff and pytest, including
synthetic Streamlit interaction and standalone trio tests. Automatic downloads
are absent; the optional local Streamlit process is the only service.
Third-party files remain outside Git. The 1c raw-mirror smoke loaded 519,407 events and exercised
three match-level estimates. The 2a audit exercised all 306 matches and exported
485 player/team metric rows; neither verifies the whole original event archive.

## MVP v0.1 boundary

The intended users are professional recruitment scouts. The only dataset in
scope is Wyscout Bundesliga 2017/18, and the only player cohort is central
midfielders. The two implemented role templates are Deep-Lying Playmaker and
Ball-Winning Midfielder. The total development budget is 25–40 hours, including
0a–0b; the allocation is in the [README](../README.md).

Use a single Python package and a lightweight local interface in one process.
Local files and in-memory tables should suffice for this bounded dataset.
Streamlit supplies the local UI; no additional service layers are needed.

MVP v0.1 has no LLMs, embeddings, semantic retrieval, FastAPI, PostgreSQL,
graph ML, authentication, or deployment. It needs no separate API service.

## Component status and planned data flow

Local metadata, match-sheet facts, raw-event validation, conservative match-level
minutes, covered event metrics, explicit cohort eligibility and role fits are
implemented, along with independent style similarity and basic replacement
shortlists, plus combined replacement rankings with explicit priorities. The local
explorer and replacement finder are implemented (4a), with a separate hypothetical
midfield-trio comparison API/example (4b1) and simulator UI (4b2). Broader cohort
validation remains planned.

| Component | Intended responsibility | Status |
| --- | --- | --- |
| Source access and normalization | Metadata, raw-mirror event validation, and match-level minutes exist; original event-binary verification and further normalization remain pending | Partly implemented (1a–1c) |
| Cohort and analytics | Event metrics, covered per-90 rates, configurable eligibility thresholds and explicit pair-level reviews exist; the four-player positional-proxy demo needs broader validation | Implemented API / limited demo (2a–2b) |
| Role profiles and weights | Deep-Lying Playmaker and Ball-Winning Midfielder templates, normalized custom weights, cohort percentiles and contributions | Implemented API (2b) and weight controls (4a) |
| Player comparison and replacements | Independent source style/role scores plus an optional weighted replacement ranking preserving both contexts and explanations | Implemented APIs/demos (3a–3b) and local replacement UI (4a); trio comparison stays separate |
| Lineup compatibility | User-selected hypothetical 4-3-3 midfield trio; compare passing/defending feature coverage before/after a replacement against fixed scales | Standalone API/example (4b1) and separate simulator tab (4b2) implemented |
| Local UI and scouting search | Search names and historical teams, distinguish demo reviews, adjust thresholds/weights and inspect replacement explanations | Implemented local Streamlit UI (4a, 4b2) |

The implemented flow is local JSON files → original records, match-sheet
participation facts, and optional event discrepancies → match minutes and
covered player/team metrics → summary CLI / optional CSV or explicit cohort
reviews and eligibility → separate role fit and style distance → optional
priority-weighted replacement ranking / local examples or cached Streamlit
exploration and replacement search. The planned extension adds broader
source/cohort validation. Covered metrics also feed the
independent fixed-cohort midfield comparison; it never enters recruitment scoring.
Scouting search is structured filtering and ranking. Semantic retrieval and an API are outside
this MVP.

## Keep three questions separate

| Result | Question | Basis and status |
| --- | --- | --- |
| Style similarity | Does this candidate play similarly to the selected player? | Implemented: weighted absolute distance between min/max-normalized rated measurements, independent of role scoring |
| Role fit | Does this candidate match the selected role template? | Implemented: weighted cohort-relative percentiles for Deep-Lying Playmaker or Ball-Winning Midfielder; not validated tactical ground truth |
| Team fit | How does the selected replacement change the hypothetical trio profile? | Implemented (4b1): marginal feature coverage with fixed cohort normalization and raw trio means; no tactical-slot or synergy inference |

Similar style does not establish quality, role suitability, or team compatibility.
Replacement recommendations should show these three results alongside minutes,
eligibility, and feature explanations; do not silently combine them into one
opaque score. Changing the lineup affects team fit, not the candidate's underlying
style comparison or selected role definition. Show which weights and assumptions
produced each result.

Team fit is an interpretable coverage heuristic, not a prediction of tactical
chemistry or future performance. Users assign hypothetical midfield slots because
the inspected raw match sheets lack reliable tactical slot coordinates. No
tracking, contracts, wages, or current transfer-market information is supplied
by this event dataset.

## Data constraints and implementation gates

The inspected player metadata provides only broad labels such as `Midfielder`,
not a reliable central-midfielder designation or the two MVP role labels. The
explicit review interface and four-player positional-proxy example address the
demonstration scope; stronger football evidence and broader cohort review remain
necessary. Role profiles are application definitions, not source annotations.

Event `positions` describe action locations on a 0–100 scale, not continuous
player tracking. Confirm coordinate orientation before defining spatial metrics.
The minutes function now derives estimates from participation and timing records.
Per-90 rates now use only matched positive-minute samples with explicit warnings
and missing coverage. The full-season audit retained conservative exclusions in
39 matches and found uneven team coverage. Completeness policy, minimum sample
threshold calibration, missing identities and name encoding still need review
before interpreting role rankings beyond the limited demonstration cohort.

Direct Figshare metadata/download access and rendered socceraction documentation
were blocked during 0b. A GitHub mirror sample and upstream loader source were
accessible. In 1c the primary item licenses and small metadata checksums were
verified; the original event binary still redirects to a blocked S3 host, and its
whole-archive hash remains unverified. The raw event smoke is mirror-derived.
See [data sources](data-sources.md) for evidence and attribution requirements.
The local loader and mirror smoke do not establish original event-binary identity.
Retain provenance and follow the verified data attribution terms for any publication.
Keep data outside Git and add dependencies only with the milestone that needs them.
