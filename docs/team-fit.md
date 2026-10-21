# Hypothetical midfield compatibility — Milestone 4b1

`team_fit.compare_midfield` compares the statistical profiles represented by a
user-selected **4-3-3 midfield trio** before and after one replacement. It uses
existing `PlayerSeasonMetrics`, preserving original player/team and match IDs.
Slots are arbitrary ordered indices **0, 1, 2**, not observed tactical positions.
This is a descriptive complementarity heuristic, not a model of team chemistry,
synergy, match results or tactical suitability. It never enters `rank_replacements`
or modifies individual style/role scores. The [4b2 simulator tab](ui.md#midfield-simulator-workflow-4b2)
now calls this same API. `prepare_player_profile()` exposes the existing completeness
validation so the UI can report exclusions before fixing its comparison cohort.

## Fixed comparison cohort and completeness

The caller explicitly supplies one fixed collection of player/team metric rows.
It must include all baseline rows and the candidate; when comparing several
candidates, include them **all before making any comparison** and reuse that same
cohort. Each feature's min/max is calculated once per call over this collection
and shared by both lineups. Neither lineup defines its own scale. Original and
replaced players remain in the fixed cohort after replacement. Changing cohort
membership or source measurements changes the reference scale and can change
results; compare outputs only when those inputs are the same.

All cohort rows must have positive finite rated minutes, rated counts, at least
one rated recorded appearance and all four complete, finite measurements:

| Group | Feature | Existing definition |
| --- | --- | --- |
| Passing | Pass attempts/90 | Rated Pass family count / rated minutes × 90 |
| Passing | Pass completion % | 100 × rated accurate passes / rated pass attempts |
| Defending | Interceptions/90 | Rated interception-tagged events / rated minutes × 90 |
| Defending | Successful ground defending duels/90 | Rated ground defending duel records with Won outcome / rated minutes × 90 |

These reuse the [verified metrics](metrics.md); no recovery, spatial or new event
metric is introduced. Unknown outcomes and missing timing remain unknown. An
incomplete row, even an unselected cohort member, raises `ValueError` naming
its ID and missing measurements; nothing is imputed or silently dropped from the
fixed reference. All four features remain required/displayed even at zero weight.

The function does not infer positions or impose scouting thresholds. The caller
must review/select its cohort and ensure comparable league/season samples. The
local example explicitly uses only the four existing [demo reviews](roles.md),
checks the existing default **600 rated minutes / 60% appearance coverage** and
fails with reasons if any fixed member is absent or ineligible. No review is
expanded. The generic function exposes sample counts/coverage and warns about
partial coverage, allowing explicit caller policy rather than a hidden cutoff.

## Formula and interpretation

For feature `f`, let `lo_f`, `hi_f` be the min/max over the **fixed cohort**.
Normalize an individual measurement with:

`z(player, f) = (x(player, f) - lo_f) / (hi_f - lo_f)`.

For a constant feature, use the explicit neutral convention `z = 0.5` for
every player, warn that it carries no discrimination, and return zero coverage
change. This placeholder does not mean median performance or known quality.

For a trio `L`, feature coverage is:

`C(L, f) = max(z(player, f) for player in L)`.

This answers **how strongly is this feature represented by at least one selected
individual?** It is bounded in [0, 1]; it is not a team event rate or projected
trio output. Also return the three raw values in slot order, their equal-player
arithmetic mean before/after, and the mean change. The mean of individual
completion percentages is **not pooled team pass completion**. Neither means nor
coverage combine minutes or event denominators across players/clubs.

Weights default to 0.25 each. Custom mappings replace those defaults and must
contain only the four feature keys, finite nonnegative numbers and at least one
positive value. They are normalized to sum to one (omitted/zero keys contribute
zero). Weights affect the summary contributions, not scales, raw measurements or
cohort membership:

`feature_change_f = C(after, f) - C(before, f)`

`weighted_change_f = 100 * normalized_weight_f * feature_change_f`

`weighted_coverage_change = sum(weighted_change_f)`.

The convenience summary is a **signed index change in [-100, 100]**,
not a team-fit rating or a probability. Positive means increased representation
under the selected priorities, not better football. Keep individual gains/losses
visible because opposing changes can cancel. One player can cover several
features; the max rule ignores depth behind the strongest player. Raw trio means
help expose changes hidden by unchanged maxima, but do not model interactions.
Passing and defending features are correlated and unadjusted for possession,
opponents or tactical context. No claim of independent evidence is made.

## Inputs, identities and returned context

`compare_midfield(cohort, baseline_lineup, replacement_slot, candidate_id, weights=None)`
uses `(player_id, historical_team_id)` tuples. Weights are a keyword argument.
The baseline must contain exactly three distinct **underlying player IDs**. A
candidate cannot be any baseline player, including the outgoing player or a row
from another historical club. Invalid slots, absent rows and duplicate exact
cohort keys fail explicitly. A valid comparison needs at least four distinct
players; smaller pools fail instead of inventing candidates or scales. The minimal
four-player pool carries a tiny-cohort warning.

Transfer rows can coexist explicitly in the fixed cohort, with a warning and
separate statistics/sample sizes. Only one row per underlying player may enter
a lineup. No current club is consulted, and no transfer statistics are merged.
Cohort rows sort by player ID then team ID; slot and feature order are preserved,
so input iterable/weight insertion order cannot change the result. Inputs and
source score objects are never mutated.

`MidfieldComparison` retains baseline, replaced and candidate IDs, replacement
slot, updated IDs, before/after `PlayerProfile` tuples, the complete sorted
comparison cohort, feature ranges, normalized weights, `FeatureChange` rows,
signed summary, warnings and limitations. Each profile retains its original
`PlayerSeasonMetrics`, rated/recorded appearances, appearance coverage and
unrecorded-event-match count. Match IDs, counts, minutes, and all source warnings
remain accessible through `profile.player.matches`. Appearance coverage is not
proof of complete events or official season-minute coverage.

## Local example

After the [README setup](../README.md), supply the same four external JSON files:

```sh
python examples/midfield_lineup.py --data-dir /absolute/path/to/wyscout-metadata
```

The explicitly hypothetical baseline is **Thiago / Bayern `(3345, 2444)`,
Weigl / Dortmund `(224677, 2447)`, Keita / Leipzig `(289711, 2975)`**. Candidate
**Vidal / Bayern `(20475, 2444)`** replaces slot 2 by default. They are selected
from different historical clubs: this is **not an actual starting XI**, and they
are not assumed to have played together. `--replacement-slot 0` or `1` changes
which member is removed while retaining the same four-player comparison cohort.
The CLI prints both profiles, feature contributions, samples, warnings and runtime.

Given previously loaded `metrics`, an equivalent Python call with custom weights:

```python
from football_scouting_lab.demo_cohort import DEMO_REVIEWS
from football_scouting_lab.team_fit import compare_midfield

# Review eligibility first; the example enforces the existing default cutoffs.
fixed_cohort = [p for p in metrics.players if (p.player_id, p.team_id) in DEMO_REVIEWS]
result = compare_midfield(
    fixed_cohort,
    ((3345, 2444), (224677, 2447), (289711, 2975)),
    replacement_slot=2,
    candidate_id=(20475, 2444),
    weights={
        "pass_attempts_per90": 1,
        "pass_completion_pct": 1,
        "interceptions_per90": 2,
        "successful_defensive_duels_per90": 2,
    },
)
for feature in result.features:
    print(
        feature.metric,
        feature.before_mean,
        feature.after_mean,
        feature.coverage_change,
        feature.weighted_change,
    )
```

## Actual verification — 2026-10-16

**No new real-data smoke result is claimed.** The earlier external directory
`/tmp/football-scouting-lab-1c-jpd5e7e6/raw` is absent in this session. The local
example was actually attempted there and exited 2 because `matches_Germany.json`
was missing. Searches of accessible `/workspace` and `/tmp` paths found only the
explicitly synthetic fixture copies. No football files were downloaded, bundled
or reconstructed from published summaries. Earlier real-data results belong to
[prior milestones](metrics.md); original-release/mirror provenance limitations in
[data sources](data-sources.md) remain unchanged.

Synthetic checks cover formulas, fixed scales across replacements, weights,
constant/tiny pools, identity/slot validation, missing data, transfers, samples,
source warnings and deterministic output without mutation. The local example is
also exercised end to end on synthetic JSON with test-only fictional reviews.
A hand-calculated fixture replacing player 1 with player 4 changes normalized
coverage by `(+1/3, -1/3, +1/3, +1/3)` in feature order; equal weights yield
**+16.6667 index points**, whereas completion-only weighting yields **−33.3333**.
These numbers are explicitly fictional, not Bundesliga findings.
