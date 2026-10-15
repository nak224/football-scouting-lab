"""Observed season counts and per-90 rates with matched minute denominators."""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from typing import Any

from .playing_time import MatchPlayingTime, estimate_playing_time
from .wyscout import SeasonEvents, SeasonMetadata


@dataclass(frozen=True)
class MetricCounts:
    """Raw-record definitions and missing-outcome policy: docs/metrics.md."""

    pass_attempts: int = 0
    accurate_passes: int = 0
    interceptions: int = 0
    defensive_duel_attempts: int = 0
    successful_defensive_duels: int = 0
    passes_with_unknown_outcome: int = 0
    defensive_duels_with_unknown_outcome: int = 0

    @property
    def pass_completion_pct(self) -> float | None:
        if not self.pass_attempts or self.passes_with_unknown_outcome:
            return None
        return 100 * self.accurate_passes / self.pass_attempts

    def per90(self, minutes: float | None) -> dict[str, float | None]:
        values = {
            "pass_attempts": self.pass_attempts,
            "accurate_passes": self.accurate_passes,
            "interceptions": self.interceptions,
            "successful_defensive_duels": self.successful_defensive_duels,
        }
        usable = (
            type(minutes) in (int, float) and math.isfinite(minutes) and minutes > 0
        )
        return {
            name: (
                90 * value / minutes
                if usable
                and not (name == "accurate_passes" and self.passes_with_unknown_outcome)
                and not (
                    name == "successful_defensive_duels"
                    and self.defensive_duels_with_unknown_outcome
                )
                else None
            )
            for name, value in values.items()
        }


@dataclass(frozen=True)
class PlayerMatchMetrics:
    match_id: int
    team_id: int
    player_id: int
    appearance_recorded: bool
    minutes: float | None
    event_count: int
    counts: MetricCounts | None  # None when the entire match lacks events
    warnings: tuple[str, ...]

    @property
    def rate_eligible(self) -> bool:
        return self.counts is not None and self.minutes is not None and self.minutes > 0


@dataclass(frozen=True)
class PlayerSeasonMetrics:
    player_id: int
    team_id: int
    matches: tuple[PlayerMatchMetrics, ...]
    observed: MetricCounts | None
    rated: MetricCounts | None
    rated_minutes: float | None

    @property
    def per90(self) -> dict[str, float | None]:
        return (self.rated or MetricCounts()).per90(self.rated_minutes)


@dataclass(frozen=True)
class SeasonMetrics:
    matches: tuple[MatchPlayingTime, ...]
    players: tuple[PlayerSeasonMetrics, ...]
    event_count: int
    unknown_player_event_ids: frozenset[int]
    missing_player_metadata_event_ids: frozenset[int]
    non_appearance_event_ids: frozenset[int]
    ambiguous_pass_event_ids: frozenset[int]
    ambiguous_defensive_duel_event_ids: frozenset[int]


def _outcome(tags: set[int], family: set[int]) -> int | None:
    outcomes = tags & family
    return next(iter(outcomes)) if len(outcomes) == 1 else None


def _count(records: list[dict[str, Any]]) -> MetricCounts:
    counts = Counter()
    for event in records:
        tags = {tag["id"] for tag in event["tags"]}
        if event["eventId"] == 8:
            outcome = _outcome(tags, {1801, 1802})
            counts["pass_attempts"] += 1
            counts["accurate_passes"] += outcome == 1801
            counts["passes_with_unknown_outcome"] += outcome is None
        counts["interceptions"] += 1401 in tags
        if event["eventId"] == 1 and event["subEventId"] == 12:
            outcome = _outcome(tags, {701, 702, 703})
            counts["defensive_duel_attempts"] += 1
            counts["successful_defensive_duels"] += outcome == 703
            counts["defensive_duels_with_unknown_outcome"] += outcome is None
    return MetricCounts(**counts)


def _sum_counts(rows: list[MetricCounts]) -> MetricCounts | None:
    if not rows:
        return None
    return MetricCounts(
        **{
            field.name: sum(getattr(row, field.name) for row in rows)
            for field in fields(MetricCounts)
        }
    )


def calculate_metrics(metadata: SeasonMetadata, events: SeasonEvents) -> SeasonMetrics:
    """Aggregate loaded events by original player and historical match-sheet team.

    Retain all observed counts separately from counts on positive-minute matches.
    No event download, minute imputation, cohort selection, or estimator relaxation.
    Event coverage is observed, not certified complete by period endpoints.
    """
    by_match = defaultdict(dict)
    ambiguous_passes, ambiguous_duels = set(), set()
    for event in events.records.values():
        by_match[event["matchId"]][event["id"]] = event
        tags = {tag["id"] for tag in event["tags"]}
        if event["eventId"] == 8 and _outcome(tags, {1801, 1802}) is None:
            ambiguous_passes.add(event["id"])
        if (
            event["eventId"] == 1
            and event["subEventId"] == 12
            and _outcome(tags, {701, 702, 703}) is None
        ):
            ambiguous_duels.add(event["id"])
    match_results = []
    player_matches = defaultdict(list)
    non_appearance = set()
    for match_id in sorted(metadata.matches):
        records = by_match[match_id]
        subset = SeasonEvents(records, frozenset(), frozenset(), frozenset())
        timing = estimate_playing_time(metadata, match_id, subset)
        match_results.append(timing)
        minutes = {(p.team_id, p.player_id): p for p in timing.players}
        by_player = defaultdict(list)
        for event in records.values():
            if event["playerId"] != 0:
                key = (event["teamId"], event["playerId"])
                by_player[key].append(event)
                if key not in minutes:
                    non_appearance.add(event["id"])
        for team_id, player_id in sorted(minutes.keys() | by_player.keys()):
            minute_row = minutes.get((team_id, player_id))
            player_events = by_player[(team_id, player_id)]
            notes = (
                minute_row.warnings
                if minute_row is not None
                else ("event player has no recorded appearance; minutes unknown",)
            )
            if player_id not in metadata.players:
                notes += ("player ID missing from players.json",)
            row = PlayerMatchMetrics(
                match_id,
                team_id,
                player_id,
                minute_row is not None,
                minute_row.minutes if minute_row else None,
                len(player_events),
                _count(player_events) if records else None,
                timing.warnings + notes,
            )
            player_matches[(player_id, team_id)].append(row)
    players = []
    for (player_id, team_id), rows in sorted(player_matches.items()):
        eligible = [row for row in rows if row.rate_eligible]
        players.append(
            PlayerSeasonMetrics(
                player_id,
                team_id,
                tuple(rows),
                _sum_counts([row.counts for row in rows if row.counts is not None]),
                _sum_counts([row.counts for row in eligible]),
                sum(row.minutes for row in eligible) if eligible else None,
            )
        )
    return SeasonMetrics(
        tuple(match_results),
        tuple(players),
        len(events.records),
        events.unknown_player_event_ids,
        events.missing_player_metadata_event_ids,
        frozenset(non_appearance),
        frozenset(ambiguous_passes),
        frozenset(ambiguous_duels),
    )
