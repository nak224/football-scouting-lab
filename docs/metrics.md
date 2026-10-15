# Event metrics and coverage (Milestone 2a)

`calculate_metrics(metadata, events)` in `football_scouting_lab.metrics` returns
season rows grouped by **original player ID and historical team ID**. It retains
each player-match's counts, estimated minutes, recorded-appearance flag, event
sample size, and warnings, plus every match's playing-time result. Transfers
remain separate team rows. This metrics function applies to all observed players,
without role scores or rankings. Milestone 2b's separate [role API](roles.md)
applies explicit cohort reviews, eligibility thresholds and explained role fits.

## Verified definitions

Definitions use raw Wyscout records, not socceraction's transformed SPADL actions.
The original release's event/tag dictionaries and source verification are linked
in [data sources](data-sources.md#milestone-2a-taxonomy-verification--2026-10-15).

| Metric | Exact rule |
| --- | --- |
| Pass attempts | `eventId == 8` (Pass); documented subtypes 80–86 include Cross, Hand pass, Head pass, High pass, Launch, Simple pass, Smart pass. The family ID determines inclusion, including blank subtypes. Free Kick family `3` is excluded, including corners, free-kick passes, goal kicks and throw-ins. |
| Accurate passes | A Pass with accuracy outcome **only** `1801` (Accurate); `1802` means Not accurate. |
| Pass completion percentage | `100 * accurate_passes / pass_attempts` on the selected sample. Unknown when there are no passes or any missing/conflicting accuracy outcomes. |
| Interceptions | Raw events tagged `1401` (Interception), counted once per event, including passes or touches carrying that tag. This is a tagged-event count, not an inferred possession recovery or deduplicated SPADL action count. |
| Successful defensive duels | `eventId == 1`, `subEventId == 12` (Ground defending duel), with outcome **only** `703` (Won). `701` (Lost) and `702` (Neutral) are not wins. Air, attacking and loose-ball duels are excluded. Accuracy tags do not determine duel success. |

The defensive metric is deliberately named for **won ground defending records**;
it does not claim equivalence to a current commercial aggregate, all tackles,
all defensive actions, or ball recoveries. An interception-tagged defending duel
may contribute to both counts; the metrics are not mutually exclusive.

Repeated identical tags count once. Missing or contradictory outcome-family tags
increment `passes_with_unknown_outcome` or
`defensive_duels_with_unknown_outcome`; they never become failures. The confirmed
success count remains inspectable, but the affected accurate-pass/defensive-win
per-90 rate is withheld if that rated sample has unresolved outcomes. Pass-attempt
and interception rates remain independent of those outcome tags.

## Samples and denominators

- `observed` counts include all supplied, positive-player-ID events, even when
  timing is unknown. They are **observed-sample totals**, not guaranteed complete
  season totals. `observed.pass_completion_pct` uses that same sample.
- `rated` counts and `rated_minutes` include **exactly the same player-match
  rows** with known, positive estimated minutes and supplied match events.
  Per-90 is `90 * sum(counts) / sum(minutes)`, never an average of match rates.
  `rated.pass_completion_pct` uses only rated attempts and accurate passes.
- Unknown minutes are `None`, never zero; no eligible sample gives `rated=None`
  and `rated_minutes=None`, with unknown rates. An actual zero-minute estimate
  is retained at match level and excluded from rates. Entirely missing match
  events yield `counts=None`, not zero. A player with no recorded actions in a
  supplied match can have zero counts and positive minutes.
- Unknown actor `playerId == 0` events are counted/reported separately and never
  assigned to a player. Positive actors without a recorded appearance (including
  unused bench listings) retain observed counts and warnings, with unknown
  minutes and no rates from those rows. Missing player metadata is reported;
  a valid original ID and recorded appearance are not discarded for that reason.
- Match/player warnings remain available. Numeric estimates with warnings, such
  as the documented halftime convention, remain eligible; numeric does not mean
  official or exact. See [playing time](playing-time.md). No estimator rule was
  relaxed in 2a, and this metrics function imposes no minimum scouting sample
  threshold. The separate 2b eligibility layer has configurable cutoffs.

The CLI's `--metrics-csv /external/new-output.csv` implies `--events`. It prints
duration/appearance coverage, excluded match reasons and event discrepancies.
CSV includes both count samples, both completion percentages, per-90 rates,
`rated_minutes`, match-ID lists/counts for observed/rated/unknown/zero/missing
event samples, recorded appearances, player-event counts, and warnings. Empty
cells mean unavailable, not zero. Output must be a **new file** in an existing
directory; existing files, including raw source files, are never overwritten.
Use the Python result for individual match timing and warning details.

Supplying some events, even with late endpoints in both halves, does not prove
the middle of a match is complete. There is no automatic season-completeness
certification or correction for unassigned events. These limitations apply to
every count and rate; do not rank players without reviewing their sample sizes.

## Complete-season audit and smoke — 2026-10-15

Reused the **raw mirror-derived German member from 1c**, outside Git; SHA-256
was rechecked as
`2612a6f8cbd8209acf39d5e3c7d2a43689138b1134d09b36e23a4b0422a781f3`.
The pinned mirror revision, extraction and original-binary verification limits
are recorded in [data sources](data-sources.md#milestone-1c-raw-acquisition-and-actual-findings--2026-10-14).
No new football-data download or original event-archive verification occurred.

| Coverage | Actual result |
| --- | --- |
| Loaded matches / events | 306 / 519,407; events represented all 306 matches |
| Matches with usable durations | **267 / 306 (87.25%)** |
| Excluded matches | **39**: 31 with first-half endpoints below 45, 11 with second-half endpoints below 45; 3 overlap |
| Appearing player-match rows | **8,501**, with **7,395 positive** minute estimates (86.99%), **1,106 unknown**, no zero estimates |
| Unknown appearance timing | 1,084 rows in excluded matches; 22 additional rows: 10 beyond observed duration, 10 overlapping first-half stoppage, 2 contradicting substitution list order |
| Sum of eligible estimated player-minutes | **553,887.2847**; this is a partial observed sum, not a percentage of known official season minutes |
| CSV output | **485 player/team rows**, 473 distinct actors, 477 rows with rated minutes; 472 players had recorded appearances |
| Unknown actors | **37,244 events** excluded from player counts, including 4 passes; positive event actors missing global metadata: 0 |
| Events without recorded appearances | **93**, across 8 player/team/match rows; all actors were listed in their squad, but not recorded as appearing |
| Outcome gaps | 0 ambiguous passes; **88 defending duels without outcomes**, all with unknown actor ID 0; no rated player row had an unresolved duel outcome in this sample |

CSV unknown-minute row counts total 1,114 because they also include the 8
non-appearance rows; the 1,106 above counts **recorded appearances only**. Two
players missing global metadata were unused bench entries and supplied no events.
None of these discrepancies is silently reconciled or assigned minutes.

Full positive-actor observed totals were independently checked against the raw
records: **261,458 passes, 214,975 accurate passes, 27,700 interceptions, 39,426
ground defending duels and 8,868 wins**. The matched positive-minute sample had
**226,159 passes, 185,510 accurate passes, 24,194 interceptions, 34,701 defending
duels and 7,784 wins**. Unknown-actor events explain differences from whole-file
counts; excluded timing rows explain differences between observed and rated counts.

Representative **rated samples**, rounded only for this table:

| Player ID / team ID | Rated / observed matches | Estimated minutes | Accurate / attempted passes | Completion | Passes/90 | Interceptions/90 | Defending wins/90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Thiago `3345` / Bayern `2444` | 12 / 19 | 841.2298 | 764 / 829 | 92.1592% | 88.6916 | 3.7445 | 1.9258 |
| Weigl `224677` / Dortmund `2447` | 24 / 25 | 1,989.7769 | 988 / 1,119 | 88.2931% | 50.6137 | 5.2468 | 1.7640 |
| Gómez `14731` / Stuttgart `2445` | 14 / 16 | 1,258.5097 | 181 / 261 | 69.3487% | 18.6649 | 1.6448 | 0.5006 |
| Gómez `14731` / Wolfsburg `2451` | 11 / 12 | 893.8535 | 110 / 152 | 72.3684% | 15.3045 | 2.4165 | 0.6041 |

Gómez demonstrates historical-team separation, not midfielder eligibility.
Loading/checksum verification took 11.458 s; metric calculation 2.277 s; the
smoke including independent count checks took 15.128 s, peak RSS **1,011.9 MiB**
on this instance. The actual CLI separately exited 0 and wrote 485 CSV rows.
The standard-library loader still reads the raw array in memory.

### Comparison with published socceraction methodology

Compared three matches using the exact pinned upstream `_get_minutes_played`
and `_expand_minute` function bodies, extracted locally from its published source.
A minimal `DataFrame` adapter returned their output records; the complete
socceraction package was **not installed or integration-tested**. See the
[loader](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/data/wyscout/loader.py#L782)
and [minute expansion helper](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/data/base.py#L100).

| Match / player | This estimator (minutes) | Published helper (minutes) | Reason |
| --- | --- | --- | --- |
| `2516739` / outgoing `388267` | 45.5723 | 47 | Our warned halftime boundary; upstream rounds periods and expands nominal minute 46 |
| `2516739` / incoming `146583` | 46.5905 | 46 | Same convention difference |
| `2517042` / dismissed `15232` | 72.2623 | 73 | Our explicit tagged timestamp; upstream nominal redCards clock and rounded periods |
| `2516740` / starter `11095` | Unknown | 92 | First half ends at 44.9603; upstream rounds it to 45; we retain the conservative exclusion |

These differences explain methodology, not agreement with official totals.
Neither last-event method establishes a final whistle. Upstream source alone
does not justify relaxing the conservative rule; that decision remains for review.

### Coverage bias requiring review

Of 42 sub-45 period endpoints, 38 were within 30 seconds of 45; gaps ranged from
0.002746 to 123.686301 seconds. Many may be ordinary gaps before the whistle,
but the raw records cannot establish that. Retaining exclusions avoids silently
padding time while discarding substantial, potentially valid observations.

Exclusions are uneven: Bayern has **23/34** usable matches, Freiburg and Hertha
27/34, Dortmund/Wolfsburg/Mönchengladbach 32/34. Substitution ambiguity further
changes individual samples. Player/team comparisons may therefore reflect
opponents, match selection, game state and substitute usage as well as performance.
Do not interpret per-90 normalization as a correction for this missingness or as
a season-wide ranking. Review the completeness policy and cohort/sample threshold
before role scoring; no correction or extrapolation was implemented here.
