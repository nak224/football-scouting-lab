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
| `positions` | Array of objects with finite numeric `x`/`y` in `[0, 100]`; empty arrays and any number of points are supported, without coordinate transformation |

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

## Remaining access checks

The saved environment draft adds `figshare.com`, `api.figshare.com`,
`ndownloader.figshare.com`, and `socceraction.readthedocs.io`; saving the draft
does not apply these domains to the running environment. Review/save the settings
and publish the environment after review. Then retry the collection API and small
teams download, inspect each selected item's license/version/filename/checksum,
and inspect any download redirect host before requesting an additional domain.
No token requirement has been established by these proxy denials.

Keep all third-party files outside Git. The repository's ignored root `data/`
is a safeguard, not a license grant; PublicWyscoutLoader's different default
directory is not covered by that ignore rule. After 1b, local match/player/team
metadata, match-sheet participation, and optional raw event loading/validation are
implemented. Minutes, metrics, matching, and UI remain unimplemented.
