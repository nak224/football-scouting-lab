# Architecture

## Implemented through Milestone 0b

The project currently contains one small Python package under
`src/football_scouting_lab/`, an import smoke test under `tests/`, and development
tooling configured in `pyproject.toml`. GitHub Actions installs the package and
runs Ruff and pytest. Milestone 0b aligns the MVP scope and documents an external
Wyscout sample audit. There are no application services, ingestion pipelines,
metrics, matching, or UI. Third-party samples remain outside the checkout.

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

## Planned components and data flow

Every component below is **planned, not implemented**.

| Component | Intended responsibility | Status |
| --- | --- | --- |
| Source access and normalization | After release/license verification, read the German season, retain original IDs and provenance, join match/event/player/team records, and validate lineups and minutes | Planned |
| Cohort and analytics | Establish reviewed central-midfielder eligibility, a minutes threshold, documented event-derived metrics, units, and normalization within the eligible cohort | Planned |
| Role profiles and weights | Define explicit Deep-Lying Playmaker and Ball-Winning Midfielder profiles; let scouts customize metric weights and see the effects | Planned |
| Player comparison and replacements | Return separate style-similarity, role-fit, and team-fit results with feature contributions and eligibility filters | Planned |
| Lineup compatibility | Let scouts choose a historical team baseline, edit lineup membership and assigned roles, and inspect candidate profile balance in the selected slot | Planned |
| Local UI and scouting search | Explore players, filter the eligible cohort, adjust weights and lineup context, and inspect comparison/replacement explanations | Planned |

The intended flow is verified local source files → normalized records and
participation intervals → eligible player metrics → separate comparison/fit
results → local exploration and search. Scouting search is structured filtering
and ranking. Semantic retrieval and an API are outside this MVP.

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
Playing time must be derived from participation and timing records; sample sizes,
substitutions, dismissals, stoppage-time conventions, missing/unknown player IDs,
and name encoding need validation before per-90 calculations or rankings.

Direct Figshare metadata/download access and rendered socceraction documentation
were blocked during 0b. A GitHub mirror sample and upstream loader source were
accessible, but the primary release license and file checksums still need checking.
See [data sources](data-sources.md) for evidence and attribution requirements.
Resolve these gates before ingestion. Keep data outside Git and add dependencies
only with the implementation milestone that needs them.
