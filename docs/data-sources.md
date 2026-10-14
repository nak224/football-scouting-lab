# Prospective data sources

## StatsBomb Open Data — planned

StatsBomb Open Data is a prospective source for football competitions, matches,
lineups, and event data. Coverage is limited to the competitions and matches
provided by the source; it should not be assumed to cover all players or leagues.

Official references:

- [StatsBomb Open Data repository](https://github.com/statsbomb/open-data)
- [StatsBomb user agreement (LICENSE.pdf)](https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf)
- [Repository usage and attribution guidance](https://github.com/statsbomb/open-data#terms--conditions)

Before importing data, review the current user agreement and confirm that the
intended use is permitted. Before publishing or redistributing data, derived
analysis, visualizations, or insights, check the applicable usage, redistribution,
and attribution requirements again. Public availability is not blanket permission
to reuse or redistribute the data.

The official README currently asks published, shared, or distributed research,
analysis, and insights to identify StatsBomb as the data source and use its logo.
Consult the current agreement and guidance for the exact requirements rather than
treating this summary as a replacement for them. Record the reviewed terms,
source revision, and required attribution when ingestion is implemented.

## Milestone 0a status

No football data is fetched, imported, or committed. There is no ingestion code or
football-data dependency. The root `data/` directory is ignored as a precaution
for future local datasets; that ignore rule does not grant data usage rights.
