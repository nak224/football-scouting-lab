# Local scouting interface

The optional Streamlit app is a local portfolio demonstration for historical
Bundesliga recruitment analysis. It uses the existing metrics, role, similarity,
recruitment and midfield-comparison APIs. No scoring algorithm or player-position
review of real players is added by the UI. The separate fictional fixture assigns
four invented midfielders solely to exercise the same workflows.
The redesigned Player explorer displays original broad source roles independently
of those recruitment decisions; its percentile profiles use existing rated metrics.

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

## Try the FICTIONAL demo

Select **Load FICTIONAL demo** in the sidebar. No downloaded data, additional
configuration is needed after installing the `ui` extra (Streamlit and Plotly).
One prominent **FICTIONAL DEMO** banner
states that players, clubs, matches, events and results are invented; names and
clubs also carry the FICTIONAL prefix. These are **not real Bundesliga statistics**.

The deterministic generator in `fictional_data.py` writes **14 miniature match
sheets and 1,848 raw-format events** into a temporary directory. The existing
metadata/event loaders, minute estimator and metrics functions run unchanged;
role fit, similarity, recruitment ranking and midfield comparison use those
computed measurements. No calculated score is hardcoded in the frontend. Temporary
files are removed after loading; only derived data is cached, with copy-on-read.
Fixture season/competition codes satisfy the existing loader's format contract;
they do not establish a real competition or season. These are toy match sheets,
not a realistic football simulation.

All four invented players have distinct IDs separate from the real reviewed
cohort and explicit fictional eligibility assignments, not FIFA evidence or
inferred positions. The real four-player review list is unchanged. Generated
players now carry an explicit fictional `role.name: Midfielder`; real-data roles
are never inferred from this assignment or from review files. Generated
match records carry a versioned fictional marker: manually loading those files
still shows the fictional banner. Mixing marked/unmarked matches, unsupported
versions, explicit nulls or inconsistent marker values is rejected before events
are loaded; none of these silently becomes real data.
The generator refuses to overwrite existing dataset files.

Suggested tour:

1. Search **Casey** in Player explorer; inspect passing/defending metrics, rated
   minutes and coverage. Search an absent name to see the empty state.
2. In Replacement finder, choose either role, change metric weights and the style
   priority, and inspect the shortlist and feature explanations. Missing/invalid
   configurations stay explicit rather than becoming zero scores.
3. In Midfield simulator, the default is **Avery / Harbor, Casey / Ridge and
   Drew / Forest**, with **Blair / Harbor** replacing slot 2. Change the slot or
   move Blair into the baseline; the remaining player becomes the candidate.
   Inspect before/after coverage, raw means, weights and source samples.
4. Try all-zero profile weights or excessive minimum minutes to see guarded
   states. Select **Load FICTIONAL demo** again to reset analysis controls.

All results in this mode are fictional. Switching between demo and local files
resets analysis controls and keeps each source's eligibility assignments separate.
Routine four-player sample notes use captions instead of repeated warning banners;
missing data, invalid controls and meaningful backend warnings remain visible.

## Optional local Wyscout files

Open **Use local Wyscout files** in the sidebar. Supply your own extracted files
together in an external directory:

```text
/absolute/path/to/wyscout/
├── matches_Germany.json
├── players.json
├── teams.json
└── events_Germany.json
```

Enter that directory and click **Load season**. All four files are required for
this local-data mode; the existing metadata-only CLI remains available.
The app never downloads/extracts datasets. Follow the source/license and
attribution guidance in [data sources](data-sources.md); source data stays outside
Git. A local subset is accepted without implying full-season completeness.
Missing files and invalid consumed JSON fields produce an error before results
are shown, including after replacing a previously loaded dataset.

## External manual reviews (5b)

In the local-file form, optionally supply **Optional local review JSON file**, then
click **Load season**. This **replaces**, rather than merges with, the default four
reviews. Blank restores those defaults; an empty JSON array `[]` deliberately
leaves no eligible players. This input applies only to real-data mode; the
**Load FICTIONAL demo** button ignores it. Manually loading marked fictional files
with a review path fails instead of attaching real-data decisions to them.

Minimal **fictional schema example**, not real position evidence and not a review
for the built-in fictional demo:

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

All five fields are required, with no extra fields. IDs must be positive JSON
integers (not strings, decimals or booleans). `status` is exactly `included` or
`excluded`; both require nonblank evidence and a review note. Evidence may be a
document/URL/reference string: the app records it without fetching or independently
verifying its football claims. Omitted pairs stay unverified; broad source position
labels and metrics never generate reviews. Keep your review files outside Git.

Each player/team pair must exist in loaded historical match sheets (lineup, bench
or substitutions) with a known team. Missing global player metadata is a separate
discrepancy, not proof that a match-sheet affiliation is invalid. It appears as
**Missing from players.json** in the review table, with an ID-only name fallback.
Merely having both IDs in the metadata, or a matching `currentTeamId`, is
insufficient. Different teams for
a transferred player need independent decisions. Duplicate pairs/JSON keys,
unknown affiliations, missing files and invalid schemas fail with contextual
errors and hide stale results. An unused bench player's review is valid but does
not fabricate an appearance/metric sample and cannot make that player scoreable.
This remains true when that bench player's global metadata is absent. A player
with a genuine metric sample still needs explicit review, positive rated minutes,
coverage and complete measurements under the unchanged eligibility rules.

The source summary shows included/excluded decisions, reviewed player IDs and
unverified metric rows. **Cohort reviews and evidence** shows every supplied
decision, note, evidence, player-metadata status and metric-sample availability,
including exclusions.
Recruitment reviews do not restrict Player explorer or its comparison population.
Minimum minutes/coverage and measurement completeness still control recruitment
scoring eligibility. Replacement
and simulator exclusions explain why reviewed players cannot be scored.

Review files are reread on each interaction, so edits at the same path (including
evidence revisions) take effect without changing file timestamps or recalculating
season events. A changed path or blank field takes effect on **Load season**.
The cached snapshot is never modified: ranking uses the existing analytics and
eligibility APIs unchanged. Stale references are repaired, and simulator lineup
selections reset when review content changes. All complete eligible reviewed rows
form its fixed comparison cohort; it is never narrowed to the selected lineup.

## Example workflow

1. In **Player explorer**, search `Casey` in fictional mode or `Thiago` in local
   Wyscout mode, filter a historical club and broad source position, then select
   a row for the profile. Click table headers to sort. **Player list** returns
   to your filters; transfer rows retain separate team identities.
2. In **Replacement finder**, choose an eligible reference such as fictional
   Casey or local-data Weigl `(224677, 2447)` and Deep-Lying Playmaker or Ball-Winning Midfielder.
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
Recruitment scoring and normalization remain in those existing APIs.

## Player discovery and profiles

The four filters are **Player name**, **League**, **Historical team** and
**Position**. The league selector is fixed to **Bundesliga 2017/18**, the only
supported source. Filters combine; empty results have a simple message. The list
initially sorts by rated minutes and shows seven compact columns. Select a row
using Streamlit's native single-row selection to open a two-column profile.
Audit IDs remain internal; no recruitment-review label or massive statistics
table appears in discovery. Recruitment evidence stays in Replacement finder.

Positions come only from the original `players.json` **`role.name`** values:
Goalkeeper, Defender, Midfielder or Forward. Absent, malformed, unrecognized or
missing-player metadata stays **Unknown**. These are broad metadata labels, not
historical match-specific tactical positions or verified central-midfielder
eligibility. No CM/CDM/AM label is inferred from events, reviews or current clubs.
Historical teams still come from match sheets, never `currentTeamId`.

Profiles show the selected historical team and season, rated minutes/appearances,
the existing per-90 passing/defending statistics, pass completion, and comparison
percentiles. **Player list** restores filters without reopening a stale selection.
Data-source/file changes clear stale profiles and filters; review-file changes
affect recruitment while leaving discovery/profile measurements unchanged.
Navigation, filters and comparison controls reuse the cached season snapshot;
they do not reprocess season events. The cached payload also retains broad roles.

### Comparison and radar conventions

- **Same position** uses the same recognized broad source role. An Unknown
  position does not establish a comparable position group; use **All players**.
- **All players** includes broad-role and Unknown rows from this same source and
  season. Both modes require **at least 600 valid positive rated minutes**, rated
  counts and a rated recorded appearance for population membership. The threshold
  is a documented default, explained by a short tooltip rather than another control.
- Historical player/team rows remain separate; a transferred player can contribute
  more than one row. Include the selected row when it qualifies. A selected player
  below 600 minutes can still show available raw values and comparisons against
  qualified peers, with a sample note, but does not enter that population.
- Each feature independently excludes missing/nonfinite measurements. Its **Peers**
  count is shown; **at least two** are required for a percentile. Tiny groups are
  unstable. Nothing fills unknown measurements or percentiles with zero.

For a raw value `x`, the empirical midrank percentile is
`100 × (count(peer < x) + 0.5 × count(peer == x)) / available peers`.
Tied values share a percentile; a constant cohort matching `x` yields **50**.
For peers `[10, 20, 30, 40]`, `20` is at **37.5**. Values outside the peer range
can reach 0 or 100. This normalization is independent of tactical role scoring,
style similarity and recruitment rankings; none of those algorithms changes.

The Plotly radar uses a fixed **0–100** axis for up to four verified features:
pass attempts/90, pass completion %, interceptions/90 and successful ground
defending duels/90. Raw values appear beside it. At least **three** usable
percentiles are needed; otherwise a concise unavailable state replaces the chart.
Zero is a real measurement/percentile when supported by data, not a placeholder.
The radar describes a **relative statistical profile, not overall player quality**.
Minutes, sample coverage, opponent/possession context and missing outcomes retain
the [existing limitations](metrics.md). The four-player demo is deliberately small.

### Redesign verification — 2026-10-26

Synthetic tests cover combined filters, original role metadata/Unknown positions,
transfer identity, native row-selection events, filtered back navigation,
comparison modes, per-feature missingness, tiny/constant/tied groups, radar data,
source isolation and cached calculation reuse. Existing recruitment and simulator
tests remain intact. Desktop Chromium renders were visually inspected; see genuine
[discovery](screenshots/explorer-list.png) and [profile](screenshots/explorer-profile.png)
captures. All pictured players, clubs and results are fictional. Real local
Wyscout data was unavailable for a new smoke; no source data was downloaded.
Ruff lint/format and the full suite passed on Python **3.12.14 and 3.13.5**:
**509 passed per version, no failures or skips**. Chromium **154.0.8037.57** at
1440 px desktop width verified native sorted-row selection, comparison switching,
filtered back navigation and both other tabs without JavaScript page errors.

## Midfield simulator workflow (4b2)

Open the third tab, **Midfield simulator**, after loading the same local files.
It reuses the cached `ScoutingData` and calls `compare_midfield()` directly.

1. In local Wyscout mode, the documented default trio is **Thiago / Bayern, Weigl / Dortmund and
   Keita / Leipzig**. **Vidal / Bayern** replaces **slot 2**. Names and original
   player/team IDs are shown. This is a **hypothetical 4-3-3 midfield**, not an
   observed historical XI; players from different clubs are not assumed to have
   played together. Fictional-mode defaults are listed above. No tactical positions
   are inferred.
2. Choose three distinct reviewed players, a replacement slot 0/1/2 and a
   candidate outside the baseline. With four eligible demo players, the candidate
   is the remaining player. Moving the candidate into a baseline slot updates
   the available replacement. Duplicate/stale selections are repaired with a note.
3. Adjust the four **Midfield profile weights**. They are relative, nonnegative
   weights normalized by the backend. All-zero weights show a configuration
   warning. Read the BEFORE/AFTER lineups, removed/added labels and feature table:
   coverage before/after, change, raw trio means and weighted contribution.
4. **Signed weighted coverage change** describes statistical representation;
   it is not a performance prediction, chemistry measure or team-fit rating.
   Coverage is the strongest individual normalized feature, and the signed
   summary sums `100 × normalized weight × coverage change`. Raw means average
   individuals; average completion is not pooled team pass completion. See
   [the unchanged backend formula and limits](team-fit.md).
5. Inspect **Simulator normalization, samples and warnings** for the fixed cohort
   IDs, feature ranges, normalized weights, rated minutes, appearance coverage and
   original source warnings. Constant features carry explicit warnings.

The simulator reuses `EligibilityThresholds` and defaults of **600 rated minutes /
60% appearance coverage**, with its own controls. Before constructing the fixed
cohort, it excludes unreviewed, ineligible or incomplete rows using the existing
eligibility and backend profile checks. **Simulator eligibility and exclusions**
reports reviewed entries absent from local data and unavailable measurements.
Fewer than four distinct complete eligible players leaves a clear unavailable
state; no names or metrics are fabricated. All four features are required even
at zero weight.

For a given data snapshot and threshold configuration, the entire eligible,
complete reviewed cohort supplies the scales for **both** lineups. Lineup,
replacement-slot, candidate and weight changes never narrow that cohort or
reprocess season events. Changing thresholds can change eligibility and scales,
so inspect the reference context again. Changing source files resets player
selections and uses the updated cache entry; invalid/missing files hide results.
The original Player explorer and Replacement finder settings/behavior are unchanged,
and simulator coverage never enters a recruitment score.

## Cache and interpretation limits

`st.cache_data(max_entries=1)` caches derived season metrics and display names,
keyed by the absolute directory and each file's size and modification time.
Raw events are released after calculation and are not retained in the cache.
Streamlit serializes the snapshot and returns independent copies, including nested
mappings. Presentation helpers build fresh rows; the app treats all loaded records
as read-only. Control changes reuse this snapshot and only rerun presentation and
the existing small-cohort ranking/comparison APIs. Normal file changes invalidate
the entry. **Load season** applies review configuration while reusing unchanged
source metrics. Check **Force source reload** before submitting to recalculate
even if source size/timestamps were preserved. There is
no disk cache or cross-startup persistence. The fictional generator has a separate
version-keyed cache; lineup/weight changes reuse its calculated season metrics.

Without a custom review file, only **four** players have existing demonstration position
reviews. They are
secondary positional proxies, not exhaustive or verified match-position ground
truth. All other explored players remain unverified and are excluded from role
and replacement ranking. That default demonstration has at most three replacement
players per reference before further exclusions. External reviews can supply a
different cohort; they do not establish independent football validation or change
formulas. Transfers stay separate historical team rows, and the backend
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

## 4b2 verification — 2026-10-16

No real local Wyscout files were available. The earlier external `/tmp` sample
is absent, and searches of accessible project/local paths found only synthetic
fixtures. The 4a real-data smoke above remains a historical result; it does not
establish real-data verification of the simulator. No source data was downloaded
or reconstructed from earlier outputs.

Synthetic AppTest checks and a separate UI smoke rendered all three tabs with
**14 fictional matches / 161 fictional events**, whose player IDs intentionally
match the documented defaults. The fictional default coverage change was
**+25.00 index points**; no Bundesliga value is implied. They verified
the default trio/swap, changed slots and candidates, duplicate-selection repair,
weight effects, fixed feature ranges across swaps, cohort exclusions, constant
features, empty/invalid states and source-change resets. Instrumentation confirmed
**one season metric calculation** across lineup, slot, weight and threshold changes.
The original UI and backend tests remain intact. These tests establish functional
rendering/interactions; no manual browser visual review is claimed.

## Milestone 5a verification — 2026-10-21

The complete fictional workflow passed built-in Streamlit AppTest checks: load,
name search, role/weight changes, replacement shortlist and feature explanations,
lineup/candidate swaps, invalid/empty states, recovery and source switching.
Instrumentation recorded **one season metric calculation** across ordinary widget
changes. Changing raw fictional pass outcomes changes calculated metrics, proving
the results come from source records. Generation is deterministic, the real
review list is unchanged, and existing files are protected from overwrite.

The documented headless launch started successfully on the loopback interface.
`/_stcore/health` returned HTTP 200 `ok`, and `/` returned HTTP 200 HTML. The smoke
server was stopped. AppTest covers functional rendering/interactions; no manual
browser visual review or screenshots are claimed.

**Real Bundesliga simulator smoke remains unverified in 5a.** Accessible local
searches found only synthetic fixtures; the earlier external `/tmp` sample was
absent. No football data was downloaded or reconstructed from old audit outputs.
The earlier real-data results in this guide belong to their dated milestones.

## Milestone 5b verification — 2026-10-21

Synthetic tests cover valid custom cohorts, excluded/unverified pairs, invalid
schemas/IDs/evidence, duplicate records/JSON keys, unknown historical references,
transfers and unused bench entries without metric samples. Streamlit AppTest
exercises review revisions at the same path, new paths, restored defaults, changed
reference/candidate pools, evidence display, empty/invalid states, recovery and
fictional/local source switching. Instrumentation confirms one season metric
calculation across review changes and ordinary widget changes; custom reviews
never mutate the cached default or fictional assignments. Unsupported/inconsistent
fictional marker versions fail before event processing.

Validation: Ruff lint and formatting checks passed; **472 tests passed**, including
the built-in Streamlit AppTest interactions. No scoring formulas or dependencies
were changed.

**Real-data validation remains unavailable in 5b.** Searches of accessible
`/workspace` and `/tmp` paths, excluding generated test/cache directories, found
only the checked-in synthetic fixtures; one system directory was unreadable.
No legitimate local Bundesliga source files were available for this smoke.
No data was downloaded, real player review invented, or real-data success claimed.

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
empty results, cache reuse/invalidation/forced reload, independent cached copies
and the simulator scenarios above.
Without the UI extra, the Streamlit test modules skip; backend and pure presentation
tests still run. Test reviews and football records are explicitly fictional.

## Milestone 5c final review — 2026-10-21

The complete suite passes with **476 tests, no failures or skips**, separately on
Python 3.12.14 and 3.13.5; Ruff lint and format checks also pass. A clean README
installation started successfully and the actual Chromium workflow/visual review
covered all three tabs, local-format synthetic files, custom reviews, source
switching and guarded states. Genuine screenshots retain the fictional banner.
The shortlist puts sample minutes/coverage beside the scores; horizontal scrolling
retains further audit columns. No formulas or eligibility policy changed.
The actual browser review found a stale search display after source resets;
explicit widget updates now synchronize the native controls with Python state.
Regression tests verify the reset updates sent to the frontend.

**No new real-data smoke was possible.** See the
[release-readiness checklist](release-readiness.md) for exact versions, browser
evidence, the historical-pair correction, blocked checks and modeling/source limits.
