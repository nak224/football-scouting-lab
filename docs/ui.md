# Local scouting interface — Milestone 4a

The optional Streamlit app is a local portfolio demonstration for historical
Bundesliga recruitment analysis. It uses the existing metrics, role, similarity
and recruitment APIs. No additional scores or player-position reviews are added.

## Install and start

Requires Python 3.12+. From the repository root, activate the virtual environment
created in the [README](../README.md), then run:

```sh
python -m pip install -e ".[ui]"
python -m streamlit run streamlit_app.py
```

The checked-in configuration binds to `127.0.0.1` and disables usage telemetry.
Keep this as a local application. Stop it with Ctrl+C. For headless startup,
append `--server.headless true`. No database, API server or deployment is required.

Supply your own extracted files together in an external directory:

```text
/absolute/path/to/wyscout/
├── matches_Germany.json
├── players.json
├── teams.json
└── events_Germany.json
```

Enter that directory in the sidebar and click **Load season**. All four files
are required for the UI; the existing metadata-only CLI remains available.
The app never downloads/extracts datasets. Follow the source/license and
attribution guidance in [data sources](data-sources.md); source data stays outside
Git. A local subset is accepted without implying full-season completeness.
Missing files and invalid consumed JSON fields produce an error before results
are shown, including after replacing a previously loaded dataset.

## Example workflow

1. In **Player explorer**, search `Thiago`, filter a historical team, or choose
   **Reviewed demo only**. Tables initially sort by rated minutes; click column
   headers to sort. Each player/team row retains original IDs, rated-match and
   appearance counts, minutes, coverage and existing passing/defensive metrics.
2. In **Replacement finder**, choose a reviewed, eligible reference such as Weigl
   `(224677, 2447)` and Deep-Lying Playmaker or Ball-Winning Midfielder.
3. Adjust minimum rated minutes (default 600), appearance coverage (60%), shortlist
   length (3), and style priority (0.5). Open **Metric weights** for independent,
   nonnegative relative weights. At least one weight per component must be positive;
   zero disables that feature. Both source scores are required even at priority 0/1.
4. Inspect the separate style and role scores, combined score, weighted points,
   minutes and samples. Choose **Explain candidate** to see raw measurements,
   feature differences, normalized weights and per-feature contributions.
5. Open **Normalization, position reviews and exclusions** to inspect each source
   cohort, style ranges, review evidence and reasons for unavailable scores.
   Thresholds or missing measurements can leave no reference or an empty shortlist;
   the app explains these states rather than substituting zero scores.

Scores and explanations come directly from `rank_replacements`; see
[recruitment](recruitment.md), [roles](roles.md) and [similarity](similarity.md).
No frontend scoring algorithm or normalization is introduced.

## Cache and interpretation limits

`st.cache_data(max_entries=1)` caches derived season metrics and display names,
keyed by the absolute directory and each file's size and modification time.
Raw events are released after calculation and are not retained in the cache.
Streamlit serializes the snapshot and returns independent copies, including nested
mappings. Presentation helpers build fresh rows; the app treats all loaded records
as read-only. Control changes reuse this snapshot and only rerun presentation and
the existing small-cohort ranking. Normal file changes invalidate the entry;
**Load season** forces a refresh even if size/timestamps were preserved. There is
no disk cache or cross-startup persistence.

Only **four** players have existing demonstration position reviews. They are
secondary positional proxies, not exhaustive or verified match-position ground
truth. All other explored players remain unverified and are excluded from role
and replacement ranking. A reference has at most three replacement players before
further exclusions. Transfers stay separate historical team rows, and the backend
excludes every row belonging to the reference's underlying player ID.

Unknown measurements remain blank. Displayed metrics use the rated sample only,
not a mixture with all observed events. Coverage means rated recorded appearances
/ all recorded appearances, not official minute or event completeness. Minutes
are estimates, and conservative timing exclusions can bias rankings. Scores are
cohort-relative, not probabilities, league-wide quality rankings or team fit.

## Actual local smoke — 2026-10-15

Python 3.12.14 / Streamlit 1.66.0 loaded the existing external files at
`/tmp/football-scouting-lab-1c-jpd5e7e6/raw`. This was the previously documented
**raw mirror-derived** sample, not a new original-release verification. No files
were downloaded. The event SHA-256 was rechecked as
`2612a6f8cbd8209acf39d5e3c7d2a43689138b1134d09b36e23a4b0422a781f3`;
[provenance and original event-binary limitations](data-sources.md) are unchanged.

Streamlit AppTest rendered **306 matches, 519,407 events and 485 player/team rows**
without application exceptions. Name search found Thiago; changing priority to
0.75 and the role to Ball-Winning Midfielder also rendered successfully. Instrumented
loading ran **once** across these interactions. The cold loaded render took
**11.146 s** (10.726 s loading/calculation); a cached slider rerun took **0.147 s**.
Peak AppTest process RSS was **1,047.3 MiB** during the cold run; full JSON parsing
still requires substantial memory. These are measurements on this environment,
not performance guarantees.

At default thresholds, Weigl / Dortmund as reference, Deep-Lying Playmaker and
priority 0.5, both normalization cohorts contained four rows. The app displayed:

| Player / historical team | Wyscout player/team IDs | Style | Role | Combined | Rated minutes | Rated / appearances |
| --- | --- | --- | --- | --- | --- | --- |
| Thiago / Bayern | 3345 / 2444 | 49.40 | 100.00 | 74.70 | 841.23 | 12 / 19 |
| Vidal / Bayern | 20475 / 2444 | 41.45 | 66.67 | 54.06 | 1,140.02 | 16 / 22 |
| Keita / Leipzig | 289711 / 2975 | 69.64 | 13.33 | 41.49 | 1,704.88 | 23 / 27 |

The small-cohort warning was visible. The underlying season retains only
267/306 usable match durations, uneven coverage, 37,244 unknown-player events
and 93 events without recorded appearances. No estimator policy was relaxed.

The actual headless Streamlit process started on the loopback interface; its
`/_stcore/health` returned HTTP 200 `ok`, and `/` returned HTTP 200 HTML.
The filesystem sandbox initially prevented binding a socket; the authorized local
startup check succeeded outside that restriction. HTTP checks establish server
startup; AppTest establishes functional rendering and interactions. No manual
browser visual review or deployment is claimed. The test server was stopped.

## Checks

```sh
python -m pip install -e ".[dev,ui]"
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

CI installs the UI extra and runs synthetic presentation and built-in Streamlit
AppTest tests alongside all backend tests. Coverage includes search/filtering,
role/priority/weight/threshold changes, missing scores/files, invalid JSON,
empty results, cache reuse/invalidation/forced reload and independent cached copies.
Without the UI extra, the Streamlit test module skips; backend and pure presentation
tests still run. Test reviews and football records are explicitly fictional.
