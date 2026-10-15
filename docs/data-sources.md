# Wyscout data source and verification

## Selected release

MVP v0.1 uses only the **German Bundesliga 2017/18** portion of the public
Soccer match event dataset collected by Wyscout. Other leagues and tournaments
in the release are outside the MVP. This is historical event data, not tracking
data or access to the commercial Wyscout service.

- [Primary Figshare collection](https://figshare.com/collections/Soccer_match_event_dataset/4415000)
- Dataset citation: Pappalardo, Luca; Massucco, Emanuele (2019): *Soccer match event
  dataset*. Figshare. Collection. <https://doi.org/10.6084/m9.figshare.c.4415000>.
- Paper: Pappalardo, L., Cintia, P., Rossi, A. et al. *A public data set of
  spatio-temporal match events in soccer competitions*. Scientific Data 6, 236
  (2019). <https://doi.org/10.1038/s41597-019-0247-7>.
- [PublicWyscoutLoader reference](https://socceraction.readthedocs.io/en/latest/api/generated/socceraction.data.wyscout.PublicWyscoutLoader.html)
- [Socceraction Wyscout guide](https://socceraction.readthedocs.io/en/latest/documentation/data/wyscout.html)

## Milestone 0b verification — 2026-10-14

Direct Figshare and rendered Read the Docs access failed, so verification used
accessible upstream source and a documented **secondary GitHub mirror**. This
does not establish that the mirror is byte-identical to the current Figshare
release. No third-party dataset, sample, archive, or loader dependency was added
to this repository. Downloaded evidence is temporary and outside the checkout.

| Evidence | Actual outcome |
| --- | --- |
| Figshare collection page and `https://api.figshare.com/v2/collections/4415000` | Proxy tunnel `403 Forbidden`; collection contents/version/license metadata not inspected directly |
| `https://ndownloader.figshare.com/files/15073697` (small teams file referenced upstream) | Proxy tunnel `403 Forbidden`; direct original-file sample failed |
| Rendered PublicWyscoutLoader API reference | Proxy tunnel `403 Forbidden` |
| Official socceraction guide source, loader implementation, and schemas on GitHub | HTTP 200; inspected without installing or executing socceraction |
| Mirror raw `matches.zip`, `players.json`, and `teams.json` | HTTP 200; German match metadata and global player/team schemas inspected |
| Mirror processed match `2516739` | HTTP 200; parsed 1,607 events for Bayern München–Bayer Leverkusen on 2017-08-18 |
| Mirror processed match `2517042` | HTTP 200; inspected dismissal timing against its raw match sheet |

Upstream source revision inspected:
[`93a1242d46c104889205753accaabadb00c45c6d`](https://github.com/ML-KULeuven/socceraction/tree/93a1242d46c104889205753accaabadb00c45c6d).
Relevant files are the
[guide source](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/docs/documentation/data/wyscout.rst),
[loader](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/data/wyscout/loader.py),
and [schemas](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/data/wyscout/schema.py).

Mirror revision inspected:
[`ebc4c54c1093c420a81ce442c69e4186fab33bb4`](https://github.com/koenvo/wyscout-soccer-match-event-dataset/tree/ebc4c54c1093c420a81ce442c69e4186fab33bb4).
Its [README](https://github.com/koenvo/wyscout-soccer-match-event-dataset/blob/ebc4c54c1093c420a81ce442c69e4186fab33bb4/README.md)
identifies the original Figshare files. The inspected files live under `raw_data/`
and `processed/files/`; the processed wrapper contains `events`, `players`, and
`teams`, not a raw season-wide event array or a `match` object. The mirror is
verification evidence, not a replacement source selected for ingestion.

## Files and identifiers

The loader's German index selects **competition ID `426`**, **season ID
`181137`**, season name `2017/2018`. The mirror's `matches_Germany.json` contains
**306 matches**, all with those IDs. Join events by `matchId` to match `wyId`,
players by `playerId` to player `wyId`, and teams by `teamId` to team `wyId`.

| Original filename | Upstream Figshare file ID | Verification |
| --- | --- | --- |
| `competitions.json` | `15073685` | Loader path/download mapping verified; data content not sampled |
| `matches.zip` → `matches_Germany.json` | `14464622` | Filename verified in the mirror ZIP directory; all 306 German match records inspected |
| `events.zip` → `events_Germany.json` | `14464685` | Filename verified in loader index; full archive/German event file not downloaded |
| `players.json` | `15073721` | Raw mirror file inspected: 3,603 records across the release, not all German-season players |
| `teams.json` | `15073697` | Raw mirror file inspected: 142 records across the release, not just Bundesliga teams |

The loader's download links use `https://ndownloader.figshare.com/files/<id>`.
The IDs are verified in upstream source, not against current Figshare metadata.

## Raw fields and participation

The following fields were observed in raw mirror metadata or the German event
sample. Socceraction converts names for its output; keep raw and converted
schemas distinct.

| Entity | Observed raw fields | Meaning and limits |
| --- | --- | --- |
| Match | `wyId`, `competitionId`, `seasonId`, `dateutc`, `gameweek`, `duration`, `teamsData` | `duration` is a match category, not a numeric player-minutes column |
| Team | `wyId`, `name`, `officialName`, `area`, `city`, `type` | Match team membership comes from `teamsData`, not a player's current club |
| Player | `wyId`, `firstName`, `lastName`, `shortName`, `birthDate`, `foot`, `role`, `currentTeamId` | `currentTeamId` must not be assumed to describe the player's club at every historical match |
| Player position | `role.name`, `role.code2`, `role.code3` | Only broad Goalkeeper, Defender, Midfielder, Forward labels observed; midfield codes are `MD`/`MID` |
| Event | `id`, `matchId`, `teamId`, `playerId`, `eventId`, `eventName`, `subEventId`, `subEventName`, `matchPeriod`, `eventSec`, `tags`, `positions` | `id` identifies an event; `eventId` identifies its type. Some sampled events have unknown player ID `0` |
| Event coordinates | `positions` entries with `x`, `y` | Sample values range from 0 to 100; these are action locations, not lineup slots or tracking positions. Orientation still needs explicit validation |
| Match team | `teamsData[<team-id string>]`: `teamId`, `side`, `formation` | Team IDs appear as JSON string keys; use explicit IDs when joining |
| Starting lineup / bench | `formation.lineup`, `formation.bench`; each includes `playerId`, `goals`, `ownGoals`, `yellowCards`, `redCards` | First sampled match has 11 starters and 7 bench players per side; no tactical slot/position fields observed |
| Substitution | `formation.substitutions`: `playerIn`, `playerOut`, `minute` | All 612 German team match sheets have list-valued substitutions. Upstream also handles the string `"null"`; do not confuse it with JSON null |

The sample contains no direct central-midfielder, Deep-Lying Playmaker, or
Ball-Winning Midfielder labels. Establish a reviewed central-midfielder cohort
and explicit application role profiles later. Do not use event `positions` as
proof of a player's assigned tactical position. Some raw names retain escaped
Unicode sequences, which normalization will need to handle.

### Playing time is derived

No ready-made player `minutes_played` field was observed in the raw metadata.
In the inspected implementation, `PublicWyscoutLoader.players(game_id)` joins
lineups, substitutes, player metadata, and match events. Its `_get_minutes_played`
helper derives period duration from the last `eventSec` in each `matchPeriod`,
rounds to minutes, adjusts substitution/dismissal times with `_expand_minute`,
and produces `minutes_played`, `is_starter`, `team_id`, and `player_id`.

For match `2516739`, the last observed event timestamps are approximately
2,734.34 s in `1H` and 2,795.43 s in `2H`. The helper's rounded periods are
46 and 47 minutes, giving a 93-minute estimated full-match duration rather than
an assumed 90 minutes. In match `2517042`, the match sheet's player `15232` has
`redCards: "71"`; the sample has that player's second-yellow-tagged foul in `2H`
at about 1,511.39 s. Such string-valued dismissal fields are timing information,
not simply card counts.

These checks confirm the available inputs and derivation approach; the loader was
not executed and its numerical minutes output was not validated end to end.
Before using per-90 metrics, specify and test interval/stoppage-time conventions,
halftime substitutions, dismissals, missing events, and unused substitutes.
Last-event timing is an estimate, not a supplied official final-whistle timestamp.

### Loader download behavior

`PublicWyscoutLoader` is the public-release loader; commercial `WyscoutLoader`
feeds have a different layout and can require a paid subscription. No paid API
credentials are needed for this selected public release.

In the inspected source, an empty root or `download=True` triggers downloads of
competitions, teams, players, **all matches and all events**, not just Germany.
It defaults to `wyscout_data` in the working directory. Do not instantiate it in
the checkout during this milestone. Future source preparation must use an
external data root and avoid unintentionally downloading the whole event archive.
Socceraction is a documentation reference here, not an installed dependency or a
committed choice of ingestion implementation.

## License and attribution

The pinned mirror README explicitly reports **CC BY 4.0** for the datasets.
That statement was verified; the license metadata of each original Figshare item
could not be independently verified because primary access is blocked. The
scientific paper's license and socceraction's software license are separate from
the dataset license. Treat primary item-level license verification as an ingestion
and publication gate, not as completed legal clearance.

**1c update:** the original Figshare API now returns item-level CC BY 4.0 licenses
for events, matches, players, and teams. The older access failures above are
historical. Original event-binary identity is still a separate, unresolved check;
see the 1c acquisition below.

If the primary release confirms CC BY 4.0, follow its
[license terms](https://creativecommons.org/licenses/by/4.0/): credit the dataset
creators and Wyscout as the data source, link the dataset and license, retain
required notices, and indicate modifications. Do not imply endorsement. Include
the dataset citation above and the accompanying paper reference in published
analysis; preserve any additional attribution specified by the original items.
Recheck terms before importing or publishing data or derived outputs.

## Milestone 1a local metadata smoke — 2026-10-14

Actual raw files cached during 0b were available for this test. No new Figshare
download or primary-release validation was performed. `matches_Germany.json` was
extracted unchanged from the cached mirror `matches.zip`; cached `players.json`
and `teams.json` were copied alongside it into a new directory under `/tmp`,
outside Git. The cached archive and metadata hashes matched the 0b acquisition
manifest before use. Source: the secondary mirror at commit
`ebc4c54c1093c420a81ce442c69e4186fab33bb4`, linked above.

| Local file | Bytes | SHA-256 of inspected file |
| --- | --- | --- |
| `matches_Germany.json` | 1,377,328 | `6f962a20f50b174939c7b24d51169aaee10ae896b05dca89fc33aa81b585c0a9` |
| `players.json` | 1,737,347 | `877a111cb1005b73df5645e9338bd74fb4b496bace2fbc545a72abb3b73efa2e` |
| `teams.json` | 27,404 | `9f7a4a3b3d92c0be33f40613ad6e6eb4316c3b9771ec74c61a22c9b8ece23a4d` |

The actual command was `python -m football_scouting_lab --data-dir <external-dir>`
using the development virtual environment. It exited **0** and printed:

```text
Wyscout Bundesliga 2017/18
Matches: 306
Teams: 18
Referenced players: 537 (includes unused bench)
Players recorded as appearing: 472
```

It also warned on stderr:

```text
warning: player IDs missing from players.json: 302605, 497353
```

The loader produced 11,002 match-team-player facts from the match sheets. The
two missing metadata IDs occur only as unused bench players in this snapshot:
`302605` in match `2516994`, team `2453`, and `497353` in match `2517007`, team
`2481`. Their original references remain intact; no names or metadata records
were fabricated. The full global files contain 3,603 players and 142 teams,
so those file totals must not be reported as German-season participant counts.

This smoke demonstrates local loading, consumed-field validation, and historical
match-sheet derivation on this mirror snapshot. It does not establish equivalence
to the original Figshare release, verify primary item licenses/checksums, process
events, calculate minutes, validate optional metadata fields, or identify central
midfielders. Dataset attribution and the primary-access limitations above still
apply. Tests in Git use only hand-authored, explicitly synthetic fixtures.

## Milestone 1b event contract and smoke limitation — 2026-10-14

The implemented `load_events(data_dir, metadata)` reads a **nonempty JSON array**
from `events_Germany.json`, using the already loaded 1a metadata. The CLI enables
it only with `--events`. Records remain indexed by original event `id`; fields,
values, tag/position array order, and overall source record order are unchanged.
Extra fields are retained without additional interpretation. Duplicate JSON object
keys and duplicate event IDs anywhere in the input are rejected.

| Consumed field | Implemented validation |
| --- | --- |
| `id` | Unique positive integer event identifier; booleans and string IDs are invalid |
| `matchId` | Positive integer referring to a loaded match |
| `teamId` | Positive integer present in team metadata and in that particular match's `teamsData` |
| `playerId` | Nonnegative integer; `0` is explicitly unknown; positive unresolved/unlisted IDs are retained with discrepancies |
| `eventId`, `eventName` | Positive integer type ID and nonempty string label; no fixed type catalogue or inferred label mapping |
| `subEventId`, `subEventName` | Nonnegative integer or empty-string subtype ID, plus string label (which may be empty); no coercion or replacement |
| `matchPeriod` | One of `1H`, `2H`, `E1`, `E2`, `P`, preserved as supplied |
| `eventSec` | Finite nonnegative numeric value, excluding booleans; no upper duration limit, sorting, conversion, or derived minutes |
| `tags` | Array of objects, each with a positive integer `id`; empty arrays and additional object fields are retained |
| `positions` | Array of objects with finite numeric `x`/`y`; empty arrays and any number of points are supported, without coordinate transformation. In 1c, values outside nominal `[0, 100]` are retained with diagnostics after real-source outliers were observed |

All consumed fields are required. Validation checks the supplied file against
loaded metadata; it does not prove release authenticity, complete season coverage,
or that all matches have events. Event subsets are allowed as long as their
match/team references resolve. CLI summaries show matches with events versus
loaded matches, type-ID counts, and period counts.

`SeasonEvents` exposes discrepancies as sets of **event IDs**, so callers can
inspect the original records:

- `unknown_player_event_ids`: source player ID `0`; no player is fabricated.
- `missing_player_metadata_event_ids`: positive player ID absent from `players.json`.
- `unlisted_player_event_ids`: positive player ID absent from that match-team's
  starting lineup and bench, even if globally known.
- `out_of_bounds_position_event_ids` (1c): finite coordinates outside nominal
  `[0, 100]`, retained unchanged rather than clipped or rejected.

The last two categories can overlap, so adding their sizes is not a distinct-event
total. Discrepancies produce CLI stderr warnings and exit 0; records are not
dropped or reassigned. Missing/invalid files, invalid consumed fields, and invalid
match/team references exit 2. Bench membership is not evidence of playing time;
event loading does not change the 1a match-sheet appearance flags or use
`currentTeamId` as affiliation.

**Real-data smoke: not run.** No accessible `events_Germany.json`, event archive,
or prior real-match sample was found in the current workspace or accessible
temporary directories. The 0b/1a temporary evidence directories were no longer
present in this environment. No automatic dataset download was attempted. The
1a metadata smoke above is a historical result and does not validate this event
loader on real data. Only explicitly synthetic event records were exercised;
no actual German-season event count or real discrepancy totals are claimed.
Primary Figshare release/license checks remain pending; the blocked 0b probes
were not re-run during 1b.

To run the missing smoke later, supply the three 1a metadata files plus the
original `events_Germany.json` in an external directory and run the README's
`--events` command. Record the source/version, file hashes, exit status, and actual
summary/warnings. Do not infer full-season success from a sample or synthetic test.

## Milestone 1c raw acquisition and actual findings — 2026-10-14

### Provenance and verification boundaries

The primary collection API returned collection **version 5**. Original item APIs
for [events](https://api.figshare.com/v2/articles/7770599),
[matches](https://api.figshare.com/v2/articles/7770422),
[players](https://api.figshare.com/v2/articles/7765196), and
[teams](https://api.figshare.com/v2/articles/7765310) each reported **CC BY 4.0**.
Events/matches items are version 1; players/teams are version 3. The events item
identifies `events.zip`, file `14464685`, size **77,323,413 bytes**, published MD5
`7c20e8647e7eda58d7838a0c7b1ec6ab`.

Original download access was attempted. The public `ndownloader.figshare.com`
link redirects to `s3-eu-west-1.amazonaws.com/pfigshare-u-files/14464685/events.zip`,
where the proxy returned a tunnel **403 Forbidden**. The original binary was not
downloaded, and its whole-archive MD5 was **not verified**.

Fallback used the documented, pinned secondary mirror at
`ebc4c54c1093c420a81ce442c69e4186fab33bb4`, specifically `raw_data/events.zip`.
HTTP byte ranges were honored with **206**. A 64-KiB central-directory read and
30-byte local header located `events_Germany.json`; bytes
**32158836–44516389** fetched only its **12,357,554 compressed bytes**. Deflate
decompression produced the untouched **152,916,631-byte raw JSON array**, and
its ZIP member CRC-32 **1109742889** matched. SHA-256 of the extracted file:
`2612a6f8cbd8209acf39d5e3c7d2a43689138b1134d09b36e23a4b0422a781f3`.

This is a **raw mirror ZIP member**, not events stripped from a processed match
wrapper. ZIP CRC proves integrity against the mirror's directory, not identity
to the independently published original archive. Matching archive size is also
not proof of identity. No other league's events or complete multi-league event
archive was downloaded. All acquisition files stayed under `/tmp`, outside Git.

The mirror's small `matches.zip` (645,097 bytes), `players.json`, and `teams.json`
were also acquired; only the German matches were extracted. Their published
Figshare file/container MD5 values matched respectively:
`51d80beb17480919f69a53a0152c2d71`, `f28ddf6326281efeda6488b2169f5609`, and
`1381ff9449f21105090729cf0e086b5b`. Extracted metadata SHA-256 values match the
1a table. These metadata checks do not verify the event archive.

### Existing loader smoke and scoped compatibility correction

The initial 1b loader rejected event `225765702` because a position had `y=101`.
Independent inspection found **two finite coordinate-outlier events**, IDs
`225765702` and `225765704`. The 1c correction preserves such values and reports
their event IDs as data-quality diagnostics. It does not decide whether the
outliers are intentional annotations or errors, clip them, or relax nonfinite/
nonnumeric field validation. Regression tests remain explicitly synthetic.

After that correction, loading and auditing the actual raw member succeeded:

| Check | Actual result |
| --- | --- |
| Events / represented matches | **519,407 / 306** |
| `1H` / `2H` event counts | **260,333 / 259,074**; no other period codes observed |
| Unknown player ID `0` events | **37,244**, retained and reported |
| Positive players missing metadata / absent from match-team squad | **0 / 0** |
| Coordinate-outlier events | **2**, retained and reported |
| Unique IDs and match/team references | Existing loader checks passed |
| Timestamp range | Approximately **0.0096–3537.356061 seconds**; finite and nonnegative |
| Loading plus audit wall time / peak RSS | **11.525 s / 1010.9 MiB** on this instance |

The standard-library loader reads the whole German array in memory. The runtime
had a 32-GiB memory limit and ample temporary disk space; this smoke establishes
feasibility here, not a low-memory or streaming guarantee. These are raw-data
validation counts, not player-performance statistics.

### Match-minutes smoke

The function was exercised against the same loaded raw data for three matches.
Values below are rounded only for display; calculations retain fractional minutes.

| Match | Observed halves / estimated duration | Actual estimator finding |
| --- | --- | --- |
| `2516739` | 45.5723 + 46.5905 = **92.1627 min** | 28 appearing players, no unknown minute rows; halftime outgoing `388267` estimated 45.5723 and incoming `146583` 46.5905 min |
| `2517042` | 47.0724 + 45.6943 = **92.7668 min** | 28 appearing players, no unknown minute rows; tagged dismissal for `15232` gave **72.2623 min** |
| `2516740` | First half endpoint **44.9603 min** | Duration and all 28 player-minute rows deliberately `None`, with a completeness warning |

Each already-loaded match estimate took about **0.063–0.065 s** here. This is
not validation against official player-minute totals. Last events can precede
the whistle. Across the source, **42 period endpoints** were below 45 minutes;
this can be a normal small final-event gap, not proof of missing data. The
conservative convention withholds affected match estimates rather than padding
or pretending completeness. Inspect both match and player warnings.

See [playing-time conventions](playing-time.md) for halftime, second-half and
stoppage clocks, dismissal precedence, uncertainty, and unsupported cases. No
season scouting statistics or per-90 measures were generated.

## Milestone 2a taxonomy verification — 2026-10-15

Primary Figshare mapping-item APIs returned HTTP 200:

| Official mapping item (version 1, CC BY 4.0) | File | Published MD5 |
| --- | --- | --- |
| [Event identifiers](https://api.figshare.com/v2/articles/11743836) | `eventid2name.csv`, file `21385245`, 1,001 bytes | `46daf16100ece0c743eedc9adcfea162` |
| [Tag identifiers](https://api.figshare.com/v2/articles/11743818) | `tags2name.csv`, file `21385239`, 1,754 bytes | `e7acb14918d00e40c80a898b1da8fc39` |

Direct `ndownloader.figshare.com/files/21385245` and `/21385239` requests
returned HTTP 403. The official glossary at
`https://dataglossary.wyscout.com/ground_defending_duel/` also returned a proxy
CONNECT 403, so its rendered commercial definition was not inspected.

Accessible copies of both dictionaries came from
[`jakeyk11/football-data-analytics` at `123790b78fab5c5f6e6d76eb31d78e85214797c9`](https://github.com/jakeyk11/football-data-analytics/tree/123790b78fab5c5f6e6d76eb31d78e85214797c9/data_directory/wyscout_data).
These are **mapping-table copies**, separate from the pinned raw event mirror.
Their original LF-form MD5s were respectively
`b60a18e4a0e44bdd6f37ab84bea063a1` and
`10b3c26e41dfe64984133c2b90d7efb4`. Converting only LF to CRLF reproduced
**both exact published Figshare MD5s**. This verifies the dictionary contents
subject to that explicit line-ending change, not a successful original binary
download or verification of any event archive. The files stayed outside Git.

Inspected mappings confirm Pass type `8` and subtypes `80`–`86`, Duel type `1`
with Ground defending duel subtype `12`, Interception tag `1401`, Accurate /
Not accurate tags `1801` / `1802`, and Lost / Neutral / Won tags `701` / `702` /
`703`. The pinned socceraction tag table independently agrees on those tag IDs.
The operational metrics count raw records by these exact semantics; no possession
or spatial inference is added. See [metrics](metrics.md) for definitions,
unknown outcomes, the complete-season minutes audit, methodology comparison,
real smoke results and selection bias. Its estimator remains unchanged.

The mapping articles request attribution to the data paper and collection cited
above, plus Pappalardo et al. (2019), *PlayeRank: Data-driven Performance
Evaluation and Player Ranking in Soccer via a Machine Learning Approach*, ACM
TIST 10(5), Article 59, <https://doi.org/10.1145/3343172>. Retain this attribution
when using or publishing the mapping-derived work; no third-party tables are
redistributed in this repository.

## Remaining access checks

The saved environment draft adds `figshare.com`, `api.figshare.com`,
`ndownloader.figshare.com`, and `socceraction.readthedocs.io`; saving the draft
does not apply these domains to the running environment. Review/save the settings
and publish the environment after review. The collection/item API and metadata
checks succeeded in 1c. Original binary access still requires the observed S3
redirect host to be permitted through environment settings; no policy bypass was
attempted. Recheck actual access and original event-archive identity separately.
No new token requirement is established by that proxy denial.

Keep all third-party files outside Git. The repository's ignored root `data/`
is a safeguard, not a license grant; PublicWyscoutLoader's different default
directory is not covered by that ignore rule. After 2a, local metadata, raw events,
conservative match-level minutes and covered per-90 metrics are implemented.
Milestone 2b adds explicit cohort reviews, eligibility cutoffs and weighted role
templates; [role documentation](roles.md) records the limited secondary evidence
for its four-player positional-proxy demo. This does not verify historical match
positions or alter the football-data provenance above. Milestone 3a adds
independent [style similarity and a basic shortlist](similarity.md) using that
unchanged demo cohort and the same rated measurements. Broader recommendation
workflows, team compatibility and UI remain unimplemented.
