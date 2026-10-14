# Match-level playing-time estimates (Milestone 1c)

`estimate_playing_time(metadata, match_id, events=None)` returns a
`MatchPlayingTime` with observed `period_minutes`, estimated `duration_minutes`,
`PlayerMinutes` rows, and warnings. Each row preserves match/team/player IDs and
has `minutes: float | None` plus its own warnings. Only starters and substitutes
recorded as entering are included; unused bench players are excluded. No season
statistics, per-90 metrics, or role scores are calculated.

## Period duration and completeness

For a regular-time match, each half's endpoint is the maximum supplied
`eventSec` in that `matchPeriod`, divided by 60. Their sum includes observed
stoppage time, excludes the halftime break, and is **an approximation**, not an
official final whistle. Fractional values are retained without rounding.

Both `1H` and `2H` must be present and end at or after 45 observed minutes.
Missing periods, invalid timestamps, unsupported extra-time/shootout periods,
or an endpoint before 45 make match duration and all appearing-player minutes
`None`, with warnings. Observed period values are still returned for inspection.
An endpoint just before 45 may reflect a normal gap before the whistle rather
than a truncated file; this deliberately conservative rule cannot distinguish
them. It never pads a period to 45 or silently assumes a 90-minute match.

Only regular-time matches are supported. A missing match `duration`
classification uses that convention with a warning; a known different category
is unsupported. Passing no events also returns unknown duration/minutes.

## Substitution convention

Match-sheet minutes are nominal-clock labels, not measured elapsed durations:

- Before minute 45, use the supplied nominal minute from kickoff.
- Labels **45 and 46** are interpreted as the observed halftime boundary and
  explicitly warned as ambiguous. The raw sheet cannot reliably distinguish a
  late first-half change from a halftime change with those labels.
- Later second-half labels map to `observed_first_half + (minute - 45)`.
  Thus a minute-60 change after a 47-minute first half occurs at elapsed minute
  62, and minute 92 includes second-half stoppage time.
- A later label that also fits first-half stoppage time (up to the ceiling of
  the observed first-half endpoint) has no unambiguous period; affected player
  minutes are `None`. Do not guess which half it belongs to.

Finite nonnegative numeric labels and numeric strings are supported. Missing,
invalid, out-of-duration, or decreasing substitution times leave affected entry
or exit points unknown. Strings such as `45+2` lack supported phase information
and are not guessed. Integer labels remain coarse estimates even when a value
can be calculated. The function neither sorts substitutions nor clamps intervals.

## Dismissal convention

Prefer a unique event timestamp tagged `1701` (red card) or `1703` (second
yellow), mapped through its explicit period. These codes are documented in the
[pinned upstream Wyscout source](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/spadl/wyscout.py).
Repeated identical times are deduplicated; distinct dismissal times for the same
match/team/player are ambiguous and give that player `None` minutes.

Without a tagged event, the public release's `redCards` sheet field is interpreted
as a nominal dismissal clock: zero means none; a positive numeric/string value
is mapped with the same half/stoppage logic, with a fallback warning. This
convention is specific to the inspected public-release sheets, **not a generic
card-count field**. Missing/invalid card metadata without tagged timing makes the
player's minutes unknown. A dismissal in overlapping first-half stoppage cannot
be located from a nominal label alone.

A tagged dismissal conflicting with a missing/zero field or a clock differing by
more than one minute is used with a warning; event timing takes precedence.
The one-minute tolerance reflects the coarse sheet labels, not proven accuracy.
A dismissal before entry is inconsistent and gives `None`; a card after a known
substitution off is flagged as off-pitch and does not shorten the completed
playing interval. Unknown dismissal actors are reported at match level.

## Reading results

Compute `exit - entry` only when both endpoints are usable and nondecreasing.
Inspect **both match warnings and each player's warnings** before using any
numeric value. `None` is not zero minutes and must not be converted to zero for
later analytics. No raw records or metadata appearance flags are changed.

See [data sources](data-sources.md) for the actual raw-mirror smoke, provenance,
checksum boundaries, coordinate outliers, and observed incomplete endpoints.
