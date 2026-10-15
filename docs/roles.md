# Midfielder eligibility and role fit (Milestone 2b)

`football_scouting_lab.roles` consumes the existing `PlayerSeasonMetrics` without
changing its counts or minutes. These are transparent **application templates**,
not source tactical labels, learned predictions, style similarity or team fit.
Milestone 3a's separate [style-similarity API](similarity.md) reuses eligibility
and samples without reading or combining these role scores.
The separate [3b recruitment workflow](recruitment.md) optionally combines the
original role and style scores with user priorities while preserving both results.

## Explicit cohort review

Callers supply `PositionReview` entries keyed by **(original player ID, historical
team ID)**. `included` or `excluded` decisions require evidence and a review note;
absent entries remain `unverified`. The broad Wyscout Midfielder label is never
used to infer central midfield. Reviews do not propagate across transfers, and a
review referring to an absent player/team is rejected rather than silently joined
to a current club. Duplicate metric keys are also rejected.

The opt-in example contains a **four-player demonstration cohort**, manually
reviewed during implementation on 2026-10-15 using independent secondary
positional proxies. It is deliberately limited and not a production-grade,
match-by-match tactical-position annotation or exhaustive central-midfielder list.

| Wyscout player / historical team | Independent FIFA 18 identity | Listed preferred positions | Review decision |
| --- | --- | --- | --- |
| Thiago `3345` / Bayern `2444` | Thiago, FIFA `189509`, age 26, FC Bayern Munich | CDM, CAM, CM | Include in demo based on CM/CDM evidence |
| Arturo Vidal `20475` / Bayern `2444` | A. Vidal, FIFA `181872`, age 30, FC Bayern Munich | CM, CDM | Include in demo based on CM/CDM evidence |
| Julian Weigl `224677` / Dortmund `2447` | J. Weigl, FIFA `222028`, age 21, Borussia Dortmund | CM, CDM | Include in demo based on CM/CDM evidence |
| Naby Keïta `289711` / Leipzig `2975` | N. Keïta, FIFA `220971`, age 22, RB Leipzig | CAM, CDM, CM | Include in demo based on CM/CDM evidence |

Evidence: the `Preferred Positions`, name, age and club fields in
[`4m4n5/fifa18-all-player-statistics`, pinned revision `dfa2c55b08f9c9dd0fb26e5db9585e026bf263a7`](https://github.com/4m4n5/fifa18-all-player-statistics/blob/dfa2c55b08f9c9dd0fb26e5db9585e026bf263a7/Complete/CompleteDataset.csv).
Its README identifies this as EA FIFA 18 data scraped from SoFIFA. Original
Wyscout names, birth dates and **match-derived** team affiliations were inspected
to resolve these four identities manually; FIFA IDs never replace Wyscout IDs.
This is a curated candidate selection, not an automatic name join or a claim
that video-game positions establish real match assignments. No FIFA attributes
enter the metrics, weights or scores. All other players remain unverified.

The original Wikipedia profile API returned HTTP 403. An accessible pinned
[secondary Weigl profile](https://github.com/saketh-04/live-football-commentary-paper-baseline/blob/7afe273f81d3e7396f85e3c12bea71cc2ca1eaa4/data/addinfo_retrieval/Julian_Weigl.txt)
also describes him as a defensive midfielder and records his 2015–2020 Dortmund
spell, but is not primary historical match evidence. No original profile/API
verification is claimed. The FIFA CSV was inspected under `/tmp`, SHA-256
`7e42c889aba88b68c72216198b24537773ddac176f14709f804c5305a9429ee3`.
Its GitHub metadata reports no identified license; no source records, roster or
ratings are redistributed. Retain source attribution and review usage terms
before publishing third-party material. The example stores only four curated
review decisions. Obtain stronger football evidence and scout review before
expanding this demonstration cohort or treating it as validated eligibility.

## Statistical eligibility and missingness

`EligibilityThresholds()` defaults to **600 rated minutes** and **0.60 appearance
coverage**. Both are configurable demonstration cutoffs, not validated scouting
standards. Minimum minutes must be finite/nonnegative; coverage must be finite
and between 0 and 1. Positive known minutes and rated counts are always required,
even with zero thresholds.

Appearance coverage is the number of recorded appearances with positive usable
minutes and supplied events, divided by **all recorded appearances for that
player/team**. It is not a fraction of official season minutes or matches in the
team's schedule. Unknown timings stay unknown. Unused bench listings do not
inflate the denominator; event rows without recorded appearances are counted
separately and retain the existing metrics' warnings. Transfers are separate
samples and can pass different thresholds.

`assess_eligibility` returns every candidate with the review, rated minutes,
appearance/rated-match counts, coverage, unrecorded-event-match count and all
exclusion reasons. Original per-match metrics/warnings remain accessible through
`candidate.player.matches`. `score_role` additionally requires every metric with
positive selected weight to be available and finite. Incomplete rows receive
`score=None`, reasons and no contributions, and are excluded from normalization.
Missing values are never replaced with zero or filled from a different sample.

## Templates and scoring

Only [verified 2a measurements](metrics.md) from the **rated** sample are used:

| Template | Default weights |
| --- | --- |
| `deep_lying_playmaker` | Pass attempts/90 **40%**, completion percentage **30%**, accurate passes/90 **30%** |
| `ball_winning_midfielder` | Interceptions/90 **45%**, successful ground defending duels/90 **40%**, pass attempts/90 **15%** |

The playmaker template approximates passing involvement, completion and
**distribution volume**. Accurate-pass volume is correlated with attempts and
completion, so these weights intentionally emphasize passing and are not
independent evidence. No pass direction, distance, progression, tactical depth
or chance-creation measurement is invented. The ball-winning template measures
the existing interception-tagged events and won defending records, not inferred
ball recoveries or possession-adjusted defensive quality.

Each positively weighted measurement is normalized within that role's complete,
eligible **player/team rows** using empirical midrank percentiles:

`percentile = 100 * (number_lower + (number_equal - 1)/2) / (N - 1)`.

For `N=1`, use a neutral **50**. A constant feature also gives everyone 50;
an empty eligible pool produces no scores. For two distinct values the endpoints
are 0 and 100. Ties receive the same mean rank, using unrounded measurements.
All selected features have the same explicit reference IDs in `RoleRanking`.
Higher values receive higher percentiles for all current features.

Per-metric contribution is `percentile * normalized_weight`; score is the sum
of contributions on a 0–100 scale, subject to floating-point precision. Results
include original measurements, percentile, normalized weight and contribution,
plus thresholds, reference IDs and candidate context. Rank by descending full
score; exact ties use ascending player ID then team ID. Exclusions follow in ID
order. Display rounding does not change scoring.

Custom weight mappings **replace** the chosen template's weights. Use only its
metric keys with finite nonnegative numbers and at least one positive weight;
unknown keys, booleans, negative/nonfinite values and all-zero weights are
rejected. Weights are normalized to sum to one. Omitted/zero metrics are explicitly
disabled, may be unavailable, and supply no contribution; all measurements remain
visible. Changing weights can change the complete reference pool if required
metrics change. Input order and weight-mapping insertion order do not define ranks.

## Local demonstration and custom weights

After the README setup, supply the same four external Wyscout JSON files:

```sh
python examples/midfield_roles.py --data-dir /absolute/path/to/wyscout-metadata
# Optional statistical thresholds:
python examples/midfield_roles.py --data-dir /absolute/path/to/wyscout-metadata \
  --min-rated-minutes 900 --min-appearance-coverage 0.8
```

The example opts into `DEMO_REVIEWS`, reports review availability, event
discrepancies, exclusions and each scored entry's contributions. The package
does not auto-include that list. The existing metadata/event/CSV CLI is unchanged.
With a loaded `metrics` result and explicit caller-supplied `reviews`:

```python
from football_scouting_lab.roles import EligibilityThresholds, score_role

result = score_role(
    metrics.players,
    reviews,
    "deep_lying_playmaker",
    thresholds=EligibilityThresholds(900, 0.8),
    weights={"pass_attempts_per90": 2, "pass_completion_pct": 1},
)
for row in result.candidates:
    print(row.eligibility.player.player_id, row.score, row.reasons, row.contributions)
```

## Actual Bundesliga smoke — 2026-10-15

The local example exited 0 on **306 matches / 519,407 raw mirror-derived events**
reused from 1c/2a. The event SHA-256 was rechecked against
`2612a6f8cbd8209acf39d5e3c7d2a43689138b1134d09b36e23a4b0422a781f3`.
Original-release binary identity remains unverified; see [provenance](data-sources.md).
No Wyscout files were downloaded anew; all third-party source files stayed outside Git.

Default thresholds yielded **4 reference rows for each role**, out of 485
observed player/team rows; the other **481 were position-unverified**. Additional
overlapping exclusions across all rows included 143 below minimum minutes and
18 below minimum appearance coverage. The smoke reported 37,244 unknown-player
events and 93 events without recorded appearances. The conservative estimator
and metrics were unchanged.

| Candidate (original ID / team) | Rated / recorded appearances | Rated minutes | Coverage | Playmaker score | Ball-winning score |
| --- | --- | --- | --- | --- | --- |
| Thiago `3345` / `2444` | 12 / 19 | 841.23 | 63.16% | 100.00 | 28.33 |
| Vidal `20475` / `2444` | 16 / 22 | 1,140.02 | 72.73% | 66.67 | 95.00 |
| Weigl `224677` / `2447` | 24 / 25 | 1,989.78 | 96.00% | 20.00 | 30.00 |
| Keïta `289711` / `2975` | 23 / 27 | 1,704.88 | 85.19% | 13.33 | 46.67 |

For example, Vidal's ball-winning contributions were 45 points from
6.7104 interceptions/90 (100th cohort percentile), 40 from 2.7631 defending
wins/90 (100th), and 10 from 71.3673 passes/90 (66.6667th). These add to 95.
Raw values and full contributions are printed by the example.

These are plausible **relative proxy fits within four selected entries**, not
league rankings, independently validated role truth or probabilities. A 100
means top of this tiny reference on those features, not perfect performance.
The secondary game-position evidence, correlated features, nonrandom missing
minutes, differing opponents and tactical contexts limit interpretation. A
larger reviewed cohort, a different threshold or different weights can change
percentiles and rankings without changing a player's underlying performance.
