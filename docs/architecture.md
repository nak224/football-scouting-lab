# Architecture

## Implemented in Milestone 0a

The project currently contains one small Python package under
`src/football_scouting_lab/`, an import smoke test under `tests/`, and development
tooling configured in `pyproject.toml`. GitHub Actions installs the package and
runs Ruff and pytest. There are no application services or data pipelines.

## Planned components

Every component below is **planned, not implemented**.

| Component | Intended responsibility | Status |
| --- | --- | --- |
| Ingestion | Read permitted source data and retain source identifiers and provenance | Planned |
| Normalized football data | Represent competitions, matches, players, lineups, and events consistently, with explicit units and coordinate conventions | Planned |
| Analytics | Calculate documented performance metrics with minutes, context, and sample sizes | Planned |
| Player matching | Compare players using explicit features and explain each similarity or recommendation | Planned |
| Semantic retrieval | Search scouting observations by meaning while retaining links to the underlying evidence | Planned |
| API | Expose validated scouting and comparison workflows | Planned |
| UI | Present player profiles, comparisons, explanations, and search results | Planned |

The intended data flow is ingestion → normalized football data → analytics →
player matching. Semantic retrieval will operate on scouting observations and
their provenance. A future API and UI will present these capabilities.

## Design approach

Keep one Python package until a concrete requirement justifies splitting it.
Add modules, schemas, and interfaces alongside actual use cases rather than
creating empty component packages or generic plugin systems now.

Data terms must be reviewed before ingestion. Future metrics and matching should
retain enough provenance and context to make their results inspectable. Database,
web framework, embedding, and model choices are deferred to the milestones that
need them. Deployment is outside the current scope.
