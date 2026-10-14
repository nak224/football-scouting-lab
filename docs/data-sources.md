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

## Remaining access checks

The saved environment draft adds `figshare.com`, `api.figshare.com`,
`ndownloader.figshare.com`, and `socceraction.readthedocs.io`; saving the draft
does not apply these domains to the running environment. Review/save the settings
and publish the environment after review. Then retry the collection API and small
teams download, inspect each selected item's license/version/filename/checksum,
and inspect any download redirect host before requesting an additional domain.
No token requirement has been established by these proxy denials.

Keep all third-party files outside Git. The repository's ignored root `data/`
is a safeguard, not a license grant; the loader's different default directory is
not covered by that ignore rule. Ingestion, metrics, matching, and UI remain
unimplemented after 0b.
