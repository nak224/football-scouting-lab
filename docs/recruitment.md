# Combined replacement ranking (Milestone 3b)

`rank_replacements` in `football_scouting_lab.recruitment` calls existing
`compare_styles()` and `score_role()` once each on the same player/team metrics,
explicit position reviews and eligibility thresholds. It joins their original
results by **(player ID, historical team ID)** without changing either algorithm,
normalization or source score. The four-player positional-proxy demo cohort is
unchanged; no broad Midfielder label is interpreted as central midfield.

## Priorities and completeness

Choose the reference player/team, `deep_lying_playmaker` or
`ball_winning_midfielder`, independent `style_weights` and `role_weights`,
`EligibilityThresholds`, an optional shortlist `limit`, and `style_priority`:

`combined_score = style_priority * style_similarity + (1 - style_priority) * role_fit`

The default priority is **0.5**. Values must be finite numbers in **[0, 1]**;
booleans, strings and out-of-range/nonfinite values fail with `ValueError`.
At 1, complete candidates rank by style alone; at 0, by selected role fit alone.
The two weighted terms are returned as `style_contribution` and
`role_contribution`. No source score is overwritten, hidden or rescaled.

**Both source scores are required at every priority, including 0 and 1.** An
unavailable score stays `None`; the combined score is `None` and the candidate
is excluded, even if that component's priority is zero. The available component's
weighted contribution remains inspectable; its missing counterpart stays `None`.
Source exclusion reasons are retained and prefixed with `style:` / `role:`.
Unknown values never become zero, and the available priority is never increased
to compensate. Both metric-weight configurations are validated at every priority
by their existing source functions, with their existing omitted/zero-weight rules.

The reference must pass the style API's eligibility and selected-feature checks,
even at priority 0; otherwise its existing `ValueError` propagates. It supplies
the style target, so its own selected **role** score need not be available.
Candidate role fit is assessed against the caller's chosen template, not the
reference's role score. A role pool with no complete replacements produces an
empty combined shortlist and explicit warnings, not fabricated scores.

## Separate source contexts and deterministic output

`RecruitmentRanking.style` is the original `SimilarityResult`, and `.role` is
the original `RoleRanking`. Inspect separately:

- `result.style.normalization_ids`, `.feature_ranges`, `.weights` and `.warnings`;
- `result.role.reference_ids`, `.weights`, `.role` and candidate contributions.

Style uses min/max-normalized numerical distance; role fit uses cohort-relative
midrank percentiles. Their eligible/complete normalization pools can differ when
their positively weighted measurements differ. **Neither pool is refitted to the
intersection of combined candidates.** A candidate excluded from the combined
ranking may still have participated in one source's normalization. These contexts
remain visible because the two scores are descriptive scales, not calibrated
probabilities. Their linear blend expresses user priorities, not validated
recruitment quality, transfer feasibility or team compatibility.

Each `ReplacementCandidate` retains the original `.style` and `.role` rows,
their per-feature explanations, both weighted contributions, `.combined_score`
and `.reasons`. `.candidate_id` preserves player/team identity. Rated minutes,
appearance counts, coverage, review evidence and match-level warnings remain at
`row.style.candidate` / `row.role.eligibility`; reference context is at
`result.style.reference`. `result.reference_id` identifies the original reference.
No source object or player metrics are mutated.

`result.candidates` includes every row, including exclusions. All historical team
rows for the reference's **underlying player ID** are excluded from replacement
ranking with a self-replacement reason; their source scores remain visible.
Other transferred players retain separate team rows and can appear more than
once. No statistics are silently combined and no club is chosen automatically.

Complete non-self candidates sort by descending full-precision combined score,
then ascending player ID and team ID. Exclusions follow in ID order. The optional
nonnegative integer `limit` applies **after** combination, sorting and self-exclusion;
`None` returns all complete replacements and 0 requests an empty shortlist while
retaining diagnostics. `result.shortlist` contains the selected rows. Empty or
underfilled pools are reported through `result.warnings` and are never padded.
Known zero scores remain valid. Tiny/constant-cohort conventions and warnings
from [roles](roles.md) and [similarity](similarity.md) remain unchanged.

## Local demo and custom weights

After the README setup, supply the same four external Wyscout JSON files:

```sh
python examples/replacement_ranking.py --data-dir /absolute/path/to/wyscout-metadata
python examples/replacement_ranking.py --data-dir /absolute/path/to/wyscout-metadata \
  --role ball_winning_midfielder --style-priority 0.25
```

Defaults: reference Weigl `(224677, 2447)`, Deep-Lying Playmaker, priority 0.5,
600 rated minutes / 60% appearance coverage, limit 3. Additional options select
the reference, thresholds and limit. The example imports the same four
`DEMO_REVIEWS`, prints both source scores/explanations and cohorts/weights,
combined contributions, samples, exclusions and runtime. Existing APIs and
demonstrations retain their behavior. Given existing `metrics` and explicit `reviews`:

```python
from football_scouting_lab.recruitment import rank_replacements

result = rank_replacements(
    metrics.players,
    reviews,
    (224677, 2447),
    "deep_lying_playmaker",
    style_priority=0.75,
    style_weights={"pass_attempts_per90": 2, "interceptions_per90": 1},
    role_weights={"pass_attempts_per90": 1, "pass_completion_pct": 1},
    limit=3,
)
for row in result.shortlist:
    print(row.candidate_id, row.style.score, row.role.score, row.combined_score)
```

## Actual Bundesliga smoke — 2026-10-15

The default demo exited 0 on the existing **306 matches / 519,407 raw
mirror-derived events**, kept outside Git. Event SHA-256 was rechecked:
`2612a6f8cbd8209acf39d5e3c7d2a43689138b1134d09b36e23a4b0422a781f3`.
No source downloads, new position reviews or data-source verification occurred.
Original event-archive identity remains unverified; see [data provenance](data-sources.md)
and the [limited cohort evidence](roles.md#explicit-cohort-review).

For **Weigl `224677` / Dortmund `2447`** (1,989.78 rated minutes, 24/25 recorded
appearances covered, 96%), both default source cohorts contained the same four
reviewed entries. All four received both source scores; Weigl was excluded as
self, and 481 other observed player/team rows were position-unverified. The
unchanged sources reported 37,244 unknown-player events and 93 events without
recorded appearances. Deep-Lying Playmaker at priority **0.5** produced:

| Candidate / historical team | Style | Role fit | Combined | Rated minutes | Rated / appearances | Coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Thiago `3345` / Bayern `2444` | 49.3999 | 100.0000 | **74.6999** | 841.23 | 12 / 19 | 63.16% |
| Vidal `20475` / Bayern `2444` | 41.4496 | 66.6667 | **54.0581** | 1,140.02 | 16 / 22 | 72.73% |
| Keïta `289711` / Leipzig `2975` | 69.6419 | 13.3333 | **41.4876** | 1,704.88 | 23 / 27 | 85.19% |

For Thiago, approximately 24.6999 style points plus 50.0000 role points gave
74.6999. Values are rounded only for display; ranking uses original precision.
This differs from the style-only order, while leaving those source scores intact.
Measured single-run runtime: **9.694689 s loading**, **1.833903 s metrics**,
**0.015543 s combined ranking**, **11.544135 s total**, after argument parsing
and before output formatting. The loader's existing whole-array memory use is unchanged.

These are preference-driven rankings within four selected positional-proxy
entries, not league-wide recommendations. Small/selected cohorts, correlated
passing features, unequal missing-minute coverage, tactical context and unadjusted
possession remain limitations. A high combined score does not establish an
actual recruitment recommendation; stronger cohort evidence and calibration
are still needed before interpretation beyond this demonstration.

## Local interface (4a)

The [Streamlit app](ui.md) calls `rank_replacements` directly with the existing
four reviews, separate component weights and eligibility thresholds. It shows
source scores, weighted points, feature explanations, both normalization cohorts
and exclusion reasons. The Python API and CLI examples retain their behavior.
