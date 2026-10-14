"""Load local Bundesliga 2017/18 metadata and optional unmodified event records."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COMPETITION_ID = 426
SEASON_ID = 181137


class MetadataError(ValueError):
    """A required Wyscout file or a consumed field is invalid."""


@dataclass(frozen=True)
class PlayerParticipation:
    """Match-sheet facts; a bench listing alone does not establish an appearance."""

    match_id: int
    team_id: int
    player_id: int
    started: bool
    on_bench: bool
    substituted_in: bool
    substituted_out: bool

    @property
    def played(self) -> bool:
        return self.started or self.substituted_in


@dataclass
class SeasonMetadata:
    """Original records indexed by wyId, plus historical match-sheet participation."""

    matches: dict[int, dict[str, Any]]
    players: dict[int, dict[str, Any]]
    teams: dict[int, dict[str, Any]]
    participation: tuple[PlayerParticipation, ...]

    @property
    def referenced_team_ids(self) -> frozenset[int]:
        return frozenset(row.team_id for row in self.participation)

    @property
    def referenced_player_ids(self) -> frozenset[int]:
        return frozenset(row.player_id for row in self.participation)

    @property
    def missing_player_ids(self) -> frozenset[int]:
        return self.referenced_player_ids - self.players.keys()


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MetadataError(f"{context}: expected a JSON object")
    return value


def _array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise MetadataError(f"{context}: expected a JSON array")
    return value


def _identifier(value: Any, context: str) -> int:
    if type(value) is not int or value <= 0:
        raise MetadataError(f"{context}: expected a positive integer ID")
    return value


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    record = {}
    for key, value in pairs:
        if key in record:
            raise MetadataError(f"duplicate JSON key {key!r}")
        record[key] = value
    return record


def _read_records(path: Path, id_field: str = "wyId") -> dict[int, dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as stream:
            records = json.load(stream, object_pairs_hook=_unique_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, MetadataError) as error:
        raise MetadataError(f"{path}: cannot read JSON: {error}") from error

    records = _array(records, str(path))
    if not records:
        raise MetadataError(f"{path}: expected a nonempty record array")
    indexed = {}
    for number, value in enumerate(records):
        context = f"{path.name}[{number}]"
        record = _object(value, context)
        record_id = _identifier(record.get(id_field), f"{context}.{id_field}")
        if record_id in indexed:
            raise MetadataError(f"{context}: duplicate {id_field} {record_id}")
        indexed[record_id] = record
    return indexed


def _squad(value: Any, context: str) -> set[int]:
    squad = set()
    for number, row in enumerate(_array(value, context)):
        item_context = f"{context}[{number}]"
        row = _object(row, item_context)
        player_id = _identifier(row.get("playerId"), f"{item_context}.playerId")
        if player_id in squad:
            raise MetadataError(f"{context}: duplicate playerId {player_id}")
        squad.add(player_id)
    return squad


def _match_participation(
    match: dict[str, Any], teams: dict[int, dict[str, Any]]
) -> list[PlayerParticipation]:
    context = f"matches_Germany.json match {match['wyId']}"
    for field, expected in (("competitionId", COMPETITION_ID), ("seasonId", SEASON_ID)):
        actual = _identifier(match.get(field), f"{context}.{field}")
        if actual != expected:
            raise MetadataError(f"{context}.{field}: expected {expected}, got {actual}")

    teams_data = _object(match.get("teamsData"), f"{context}.teamsData")
    if len(teams_data) != 2:
        raise MetadataError(f"{context}.teamsData: expected exactly two teams")
    participation = []
    sides = set()
    match_players = set()
    for key, value in teams_data.items():
        team_context = f"{context}.teamsData[{key}]"
        team = _object(value, team_context)
        team_id = _identifier(team.get("teamId"), f"{team_context}.teamId")
        if key != str(team_id):
            raise MetadataError(f"{team_context}: key must match teamId {team_id}")
        if team_id not in teams:
            raise MetadataError(
                f"{team_context}: teamId {team_id} missing from teams.json"
            )
        side = team.get("side")
        if side not in ("home", "away") or side in sides:
            raise MetadataError(
                f"{team_context}.side: expected one home and one away team"
            )
        sides.add(side)

        formation = _object(team.get("formation"), f"{team_context}.formation")
        starters = _squad(formation.get("lineup"), f"{team_context}.formation.lineup")
        bench = _squad(formation.get("bench"), f"{team_context}.formation.bench")
        if not starters:
            raise MetadataError(f"{team_context}: lineup must not be empty")
        if starters & bench:
            raise MetadataError(f"{team_context}: lineup and bench must be disjoint")
        squad = starters | bench
        if squad & match_players:
            raise MetadataError(f"{context}: a player is listed for both teams")
        match_players.update(squad)

        if "substitutions" not in formation:
            raise MetadataError(f"{team_context}.formation: missing substitutions")
        substitutions = formation["substitutions"]
        if substitutions is None or substitutions == "null":
            substitutions = []
        substitutions = _array(substitutions, f"{team_context}.formation.substitutions")
        active = set(starters)
        incoming, outgoing = set(), set()
        for number, value in enumerate(substitutions):
            sub_context = f"{team_context}.formation.substitutions[{number}]"
            substitution = _object(value, sub_context)
            player_in = _identifier(
                substitution.get("playerIn"), f"{sub_context}.playerIn"
            )
            player_out = _identifier(
                substitution.get("playerOut"), f"{sub_context}.playerOut"
            )
            if player_in not in bench or player_in in incoming:
                raise MetadataError(
                    f"{sub_context}: playerIn must be an unused bench ID"
                )
            if player_out not in active:
                raise MetadataError(
                    f"{sub_context}: playerOut must be an active player ID"
                )
            active.remove(player_out)
            active.add(player_in)
            incoming.add(player_in)
            outgoing.add(player_out)

        participation.extend(
            PlayerParticipation(
                match_id=match["wyId"],
                team_id=team_id,
                player_id=player_id,
                started=player_id in starters,
                on_bench=player_id in bench,
                substituted_in=player_id in incoming,
                substituted_out=player_id in outgoing,
            )
            for player_id in sorted(squad)
        )
    return participation


def load_season(data_dir: str | Path) -> SeasonMetadata:
    """Load three local files, preserving IDs and reporting missing player metadata.

    Structural inconsistencies and unresolved teams raise MetadataError. Positive
    match-sheet player IDs absent from players.json remain in participation and
    are exposed by missing_player_ids. Unconsumed raw fields are retained without
    further validation; no currentTeamId, events, or minutes are used.
    """
    root = Path(data_dir)
    matches = _read_records(root / "matches_Germany.json")
    players = _read_records(root / "players.json")
    teams = _read_records(root / "teams.json")
    participation = tuple(
        row for match in matches.values() for row in _match_participation(match, teams)
    )
    return SeasonMetadata(matches, players, teams, participation)


@dataclass
class SeasonEvents:
    """Original events and nonfatal player discrepancies, identified by event ID.

    Missing-metadata and unlisted-player categories can overlap. Player ID 0 is
    an explicit unknown and belongs only to unknown_player_event_ids.
    """

    records: dict[int, dict[str, Any]]
    unknown_player_event_ids: frozenset[int]
    missing_player_metadata_event_ids: frozenset[int]
    unlisted_player_event_ids: frozenset[int]

    @property
    def match_ids(self) -> frozenset[int]:
        return frozenset(event["matchId"] for event in self.records.values())


def _number(value: Any, context: str) -> int | float:
    if type(value) not in (int, float) or (
        type(value) is float and not math.isfinite(value)
    ):
        raise MetadataError(f"{context}: expected a finite number")
    return value


def _validate_event_fields(event: dict[str, Any], context: str) -> None:
    _identifier(event.get("eventId"), f"{context}.eventId")
    name = event.get("eventName")
    if not isinstance(name, str) or not name.strip():
        raise MetadataError(f"{context}.eventName: expected a nonempty string")
    subtype = event.get("subEventId")
    if subtype != "" and (type(subtype) is not int or subtype < 0):
        raise MetadataError(
            f"{context}.subEventId: expected a nonnegative integer or ''"
        )
    if not isinstance(event.get("subEventName"), str):
        raise MetadataError(f"{context}.subEventName: expected a string")
    if event.get("matchPeriod") not in ("1H", "2H", "E1", "E2", "P"):
        raise MetadataError(f"{context}.matchPeriod: expected 1H, 2H, E1, E2, or P")
    if _number(event.get("eventSec"), f"{context}.eventSec") < 0:
        raise MetadataError(f"{context}.eventSec: expected nonnegative seconds")

    for number, value in enumerate(_array(event.get("tags"), f"{context}.tags")):
        tag_context = f"{context}.tags[{number}]"
        tag = _object(value, tag_context)
        _identifier(tag.get("id"), f"{tag_context}.id")
    for number, value in enumerate(
        _array(event.get("positions"), f"{context}.positions")
    ):
        point_context = f"{context}.positions[{number}]"
        point = _object(value, point_context)
        for axis in ("x", "y"):
            coordinate = _number(point.get(axis), f"{point_context}.{axis}")
            if not 0 <= coordinate <= 100:
                raise MetadataError(
                    f"{point_context}.{axis}: expected a value in [0, 100]"
                )


def load_events(data_dir: str | Path, metadata: SeasonMetadata) -> SeasonEvents:
    """Validate local events against loaded metadata without changing source values.

    Invalid consumed fields and match/team references raise MetadataError.
    Unknown, unresolved, or unlisted players are retained with explicit event-ID
    discrepancy sets. No event ordering, clock conversion, or minutes are derived.
    """
    events = _read_records(Path(data_dir) / "events_Germany.json", id_field="id")
    squad_members = {
        (row.match_id, row.team_id, row.player_id) for row in metadata.participation
    }
    unknown, missing, unlisted = set(), set(), set()
    for event_id, event in events.items():
        context = f"events_Germany.json event {event_id}"
        _validate_event_fields(event, context)
        match_id = _identifier(event.get("matchId"), f"{context}.matchId")
        team_id = _identifier(event.get("teamId"), f"{context}.teamId")
        if match_id not in metadata.matches:
            raise MetadataError(
                f"{context}: matchId {match_id} missing from loaded matches"
            )
        if team_id not in metadata.teams:
            raise MetadataError(f"{context}: teamId {team_id} missing from teams.json")
        if str(team_id) not in metadata.matches[match_id]["teamsData"]:
            raise MetadataError(
                f"{context}: teamId {team_id} is not in match {match_id}"
            )
        player_id = event.get("playerId")
        if type(player_id) is not int or player_id < 0:
            raise MetadataError(
                f"{context}.playerId: expected a nonnegative integer ID"
            )
        if player_id == 0:
            unknown.add(event_id)
        else:
            if player_id not in metadata.players:
                missing.add(event_id)
            if (match_id, team_id, player_id) not in squad_members:
                unlisted.add(event_id)
    return SeasonEvents(
        events, frozenset(unknown), frozenset(missing), frozenset(unlisted)
    )
