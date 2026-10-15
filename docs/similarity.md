# Playing-style similarity and shortlist (Milestone 3a)

`compare_styles` in `football_scouting_lab.similarity` compares existing rated
player/team metrics using **weighted numerical distance**. It reuses
`assess_eligibility`, `PositionReview` and `EligibilityThresholds` from the roles
module, but never calls role scoring, consumes role scores or uses role weights.
`replacement_shortlist` ranks those style comparisons without combining other
notions of suitability. Original APIs and the four-player demo cohort are unchanged.

## Measurements, cohort and weights

The four supported measurements are **pass attempts/90**, **pass completion
percentage**, **interceptions/90**, and **successful ground defending duels/90**,
all from the existing [rated sample](metrics.md). Defaults give each 25% weight.
Accurate passes/90 is deliberately omitted: it is derived from passing volume
and completion and would add correlated passing influence. No spatial,
progressive-pass, recovery or new event metric is inferred.

Use explicit **(original player ID, historical team ID)** position reviews.
Unreviewed players stay unverified, including broadly labelled Midfielders.
The [2b eligibility convention](roles.md#statistical-eligibility-and-missingness)
is reused: defaults are 600 positive rated minutes and 60% of recorded appearances
with usable minutes/events. Coverage is an appearance fraction, not a fraction
of official season minutes. Match samples, timing warnings, review notes and
unrecorded-event-match counts remain accessible for reference and candidates.

Custom weight mappings replace the four equal defaults. Omitted or zero weights
explicitly disable a feature. Names must be from the four measurements above;
values must be finite nonnegative numbers, with at least one positive weight.
Booleans, nonnumeric/nonfinite values, unknown features, empty and all-zero
mappings fail with `ValueError`. The returned weights are normalized to sum to
one. No role template constrains or changes these weights.

Only eligible player/team rows with **every positively weighted feature**
available define the normalization cohort, including the reference. Missing,
nonfinite or negative required values exclude the row; a completion percentage
above 100 is also invalid. Nothing is filled with zero, and available features
are not reweighted around a missing one. Disabled missing features remain `None`
in the measurements. Duplicate keys and unmatched review references retain the
existing eligibility API's validation.

## Distance and bounded score

For each active feature, let `low` and `high` be its minimum and maximum over
the same complete eligible player/team rows. Normalize as:

`z = (raw_value - low) / (high - low)`.

Then calculate:

`feature_contribution = normalized_weight * abs(candidate_z - reference_z)`

`distance = sum(feature_contributions)`

`similarity = 100 * (1 - distance)`.

Distance is bounded to [0, 1] against floating-point summation drift; similarity
is on [0, 100]. Both points in every comparison belong to the fitted cohort, so
there is no extrapolation or clipping of source measurements. Signed raw
differences are **candidate minus reference**. Normalized differences and
distance contributions are absolute: a larger contribution reduces similarity.
High or low performance values are not rewarded in themselves; closeness is
what matters. With a fixed cohort/weights, pairwise distances are symmetric.

This linear score is **not a probability**, verified tactical likeness or overall
quality score. A score of 100 means indistinguishable on the chosen measurements
at this precision. Adding/removing cohort rows can change scales and scores even
when the two players' original measurements do not change. Min/max scaling is
simple and preserves relative numerical gaps, but is sensitive to outliers.

Special cases are explicit:

- Constant features normalize to 0.5 for everyone and contribute zero distance,
  with a warning. Their weights stay in the denominator; they are not redistributed.
  Thus fewer varying features can produce larger similarities.
- One- or two-row normalization cohorts carry a tiny-cohort warning. With one
  row only the self-comparison exists. With two, every varying feature spans
  the full range, making distances coarse.
- An all-constant selected profile gives 100 to all complete rows and an explicit
  **uninformative** warning. This does not establish interchangeable players.
- An absent, ineligible or incomplete reference raises `ValueError` with reasons;
  it never produces a misleading empty or zero-scored result. Other excluded
  candidates stay in the result with `score=None`, `distance=None`, no feature
  contributions and explicit reasons.
- A valid reference with no other eligible underlying player yields an empty
  shortlist and a warning. No extra candidates are invented.

## Results and replacement ranking

`SimilarityResult` includes reference eligibility and raw values, thresholds,
normalized weights, feature ranges, exact normalization IDs, warnings and every
candidate comparison (including self and exclusions). Each `PlayerSimilarity`
has reference/candidate IDs, candidate eligibility/sample context, raw values,
distance, score and `FeatureDifference` records containing both raw values,
signed raw difference, both normalized values, absolute normalized difference,
weight and distance contribution. Source timing warnings remain in
`result.reference.player.matches` and `row.candidate.player.matches`.

Results sort by descending full-precision similarity, then ascending player ID
and team ID; exclusions follow in ID order. `replacement_shortlist(result,
limit=None)` returns only scored entries and **excludes the reference's underlying
player ID across every team**, before applying an optional nonnegative integer
limit. Score 0 is a valid comparison and remains eligible. Reference transfer rows
remain visible in comparisons and the normalization cohort, even though they
cannot enter the shortlist. Other transferred players retain separate historical
team rows; no cross-team aggregation or automatic deduplication is added.

These are candidates by measured style alone, with no role-fit blend, availability,
transfer feasibility, team compatibility or lineup assessment. Separate role
results can later be joined by original player/team IDs for display.

## Local example and Python API

After the README setup, use the same four external Wyscout JSON files:

```sh
python examples/player_similarity.py --data-dir /absolute/path/to/wyscout-metadata
```

The example imports the **unchanged** four `DEMO_REVIEWS` from the role example;
there are no new position claims or automatic cohort expansion. Default reference
is Weigl `(224677, 2447)`, limit 3. Options include `--reference-player`,
`--reference-team`, `--limit`, `--min-rated-minutes` and
`--min-appearance-coverage`. It reports sample coverage, exclusions, normalization
ranges, per-feature explanations and elapsed load/metrics/comparison times.
No role score is computed by the demonstration. Example errors exit 2 without
a traceback or a partial shortlist.

For custom weights, given loaded `metrics` and explicit `reviews`:

```python
from football_scouting_lab.similarity import compare_styles, replacement_shortlist

result = compare_styles(
    metrics.players,
    reviews,
    (224677, 2447),
    weights={"pass_attempts_per90": 2, "interceptions_per90": 1},
)
for row in replacement_shortlist(result, limit=3):
    print(row.reference_id, row.candidate_id, row.score, row.differences)
```

## Actual Bundesliga smoke — 2026-10-15

The local example exited 0 using **306 matches / 519,407 raw mirror-derived
events**, reused from earlier milestones outside Git. The event SHA-256 was
rechecked as
`2612a6f8cbd8209acf39d5e3c7d2a43689138b1134d09b36e23a4b0422a781f3`.
No source files were downloaded or committed in 3a; original-release event-binary
identity remains unverified. See [data sources](data-sources.md) for provenance
and [roles](roles.md#explicit-cohort-review) for the secondary positional-proxy
evidence and limitations of the existing cohort.

Default thresholds/weights gave 4 complete eligible normalization rows from 485
observed player/team rows. The remaining 481 were position-unverified; overlapping
exclusions also included 143 below minimum minutes and 18 below appearance
coverage. Unknown-player events (37,244) and events without recorded appearances
(93) remained reported. No coverage rules or estimates were relaxed.

Reference **Weigl `224677` / Dortmund `2447`**: 1,989.78 rated minutes,
24/25 recorded appearances covered (96%). Actual shortlist, rounded for display:

| Candidate / historical team | Similarity | Distance | Rated minutes | Rated / appearances | Coverage |
| --- | --- | --- | --- | --- | --- |
| Keïta `289711` / Leipzig `2975` | **69.6419** | 0.303581 | 1,704.88 | 23 / 27 | 85.19% |
| Thiago `3345` / Bayern `2444` | **49.3999** | 0.506001 | 841.23 | 12 / 19 | 63.16% |
| Vidal `20475` / Bayern `2444` | **41.4496** | 0.585504 | 1,140.02 | 16 / 22 | 72.73% |

Keïta's distance contributions were 0.077385 from interceptions/90,
0.017752 from pass attempts/90, 0.161100 from completion and 0.047343 from
defending wins/90. Completion differed by about −7.0060 percentage points;
its contribution is larger than the passing-volume gap. Contributions sum to
the displayed distance subject to rounding; this is unrelated to either role score.

Measured runtime on this instance: **10.292433 s loading**, **1.986994 s metrics**,
**0.012351 s similarity plus shortlist**, **12.291778 s total**, measured after
argument parsing and before output formatting. The loader still reads the raw
array into memory; this is a single-run observation, not a throughput guarantee.

The four-player cohort is a limited positional-proxy demonstration, not an
exhaustive or verified midfielder census. Small sample selection, correlated
features, missing-minute bias, different teams/opponents and unadjusted possession
context limit interpretation. A stylistically close candidate can have very
different role fit; neither result establishes recruitment suitability.
