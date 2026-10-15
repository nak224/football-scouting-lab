# Architecture

## Implemented through Milestone 2a

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
GitHub Actions runs Ruff and pytest. There are no added runtime dependencies,
automatic downloads, role scores, matching, services, or UI. Third-party files
remain outside Git. The 1c raw-mirror smoke loaded 519,407 events and exercised
three match-level estimates. The 2a audit exercised all 306 matches and exported
485 player/team metric rows; neither verifies the whole original event archive.

## MVP v0.1 boundary

The intended users are professional recruitment scouts. The only dataset in
scope is Wyscout Bundesliga 2017/18, and the only player cohort is central
midfielders. The two planned role profiles are Deep-Lying Playmaker and
Ball-Winning Midfielder. The total development budget is 25–40 hours, including
0a–0b; the allocation is in the [README](../README.md).

Use a single Python package and a lightweight local interface in one process.
Local files and in-memory tables should suffice for this bounded dataset.
Choose concrete modules and the UI toolkit when implementation requires them;
no empty layers or framework dependencies are needed now.

MVP v0.1 has no LLMs, embeddings, semantic retrieval, FastAPI, PostgreSQL,
graph ML, authentication, or deployment. It needs no separate API service.

## Component status and planned data flow

Local metadata, match-sheet facts, raw-event validation, conservative match-level
minutes and covered event metrics are implemented. Cohort eligibility, scoring
and UI remain planned.

| Component | Intended responsibility | Status |
| --- | --- | --- |
| Source access and normalization | Metadata, raw-mirror event validation, and match-level minutes exist; original event-binary verification and further normalization remain pending | Partly implemented (1a–1c) |
| Cohort and analytics | Event metrics, sample coverage and matched per-90 rates exist; reviewed central-midfielder eligibility, minimum sample threshold and cohort normalization remain pending | Partly implemented (2a) |
| Role profiles and weights | Define explicit Deep-Lying Playmaker and Ball-Winning Midfielder profiles; let scouts customize metric weights and see the effects | Planned |
| Player comparison and replacements | Return separate style-similarity, role-fit, and team-fit results with feature contributions and eligibility filters | Planned |
| Lineup compatibility | Let scouts choose a historical team baseline, edit lineup membership and assigned roles, and inspect candidate profile balance in the selected slot | Planned |
| Local UI and scouting search | Explore players, filter the eligible cohort, adjust weights and lineup context, and inspect comparison/replacement explanations | Planned |

The implemented flow is local JSON files → original records, match-sheet
participation facts, and optional event discrepancies → match minutes and
covered player/team metrics → summary CLI / optional CSV. The planned extension
is reviewed source completeness and cohort eligibility → eligible player metrics →
separate comparison/fit results → local exploration and search. Scouting search
is structured filtering and ranking. Semantic retrieval and an API are outside
this MVP.

## Keep three questions separate

| Result | Question | Planned basis |
| --- | --- | --- |
| Style similarity | Does this candidate play similarly to the selected player? | Distance between comparable, normalized playing-style features, with explicit selected metric weights |
| Role fit | Does this candidate meet the selected role profile? | Transparent metric targets and weights for Deep-Lying Playmaker or Ball-Winning Midfielder |
| Team fit | Does this candidate complement the chosen lineup in the intended slot? | Lightweight profile coverage/balance against the user-edited lineup and assigned roles |

Similar style does not establish quality, role suitability, or team compatibility.
Replacement recommendations should show these three results alongside minutes,
eligibility, and feature explanations; do not silently combine them into one
opaque score. Changing the lineup affects team fit, not the candidate's underlying
style comparison or selected role definition. Show which weights and assumptions
produced each result.

Team fit is an interpretable compatibility heuristic, not a prediction of tactical
chemistry or future performance. Users assign lineup slots because the inspected
raw match sheets lack tactical slot coordinates. No tracking, contracts, wages,
or current transfer-market information is supplied by this event dataset.

## Data constraints and implementation gates

The inspected player metadata provides only broad labels such as `Midfielder`,
not a reliable central-midfielder designation or the two MVP role labels. Plan a
reviewed central-midfielder inclusion list/rule using football context; document
ambiguity rather than treating every midfielder as central. Role profiles are
application definitions, not source annotations.

Event `positions` describe action locations on a 0–100 scale, not continuous
player tracking. Confirm coordinate orientation before defining spatial metrics.
The minutes function now derives estimates from participation and timing records.
Per-90 rates now use only matched positive-minute samples with explicit warnings
and missing coverage. The full-season audit retained conservative exclusions in
39 matches and found uneven team coverage. Completeness policy, minimum sample
threshold, missing identities and name encoding still need review before rankings.

Direct Figshare metadata/download access and rendered socceraction documentation
were blocked during 0b. A GitHub mirror sample and upstream loader source were
accessible. In 1c the primary item licenses and small metadata checksums were
verified; the original event binary still redirects to a blocked S3 host, and its
whole-archive hash remains unverified. The raw event smoke is mirror-derived.
See [data sources](data-sources.md) for evidence and attribution requirements.
The local loader and mirror smoke do not establish original event-binary identity.
Retain provenance and follow the verified data attribution terms for any publication.
Keep data outside Git and add dependencies only with the milestone that needs them.
