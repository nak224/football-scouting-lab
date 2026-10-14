"""Conservative regular-time estimates from match sheets and observed event ends."""

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .wyscout import MetadataError, SeasonEvents, SeasonMetadata


@dataclass(frozen=True)
class PlayerMinutes:
    match_id: int
    team_id: int
    player_id: int
    minutes: float | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MatchPlayingTime:
    match_id: int
    period_minutes: dict[str, float | None]
    duration_minutes: float | None
    players: tuple[PlayerMinutes, ...]
    warnings: tuple[str, ...]


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _clock_time(
    value: Any, first_half: float, duration: float, *, substitution: bool = False
) -> tuple[float | None, str | None]:
    minute = _numeric(value)
    if minute is None:
        return None, "missing or invalid nominal-clock minute"
    if substitution and minute in (45, 46):
        return first_half, "minute 45/46 interpreted as halftime; boundary is ambiguous"
    if minute > 45 and minute <= math.ceil(first_half):
        return None, "clock minute overlaps first-half stoppage and second-half play"
    elapsed = minute if minute <= 45 else first_half + minute - 45
    if elapsed > duration:
        return None, "clock minute exceeds observed match duration"
    return elapsed, None


def estimate_playing_time(
    metadata: SeasonMetadata, match_id: int, events: SeasonEvents | None = None
) -> MatchPlayingTime:
    """Estimate one match, excluding unused substitutes and keeping original IDs.

    See docs/data-sources.md for clock, dismissal, completeness, and uncertainty
    conventions. None denotes unavailable/ambiguous minutes, never assumed 90.
    Callers must inspect both match warnings and per-player warnings.
    """
    if type(match_id) is not int or match_id not in metadata.matches:
        raise MetadataError(f"matchId {match_id!r} missing from loaded matches")
    match = metadata.matches[match_id]
    players = [
        row for row in metadata.participation if row.match_id == match_id and row.played
    ]
    match_events = (
        [e for e in events.records.values() if e["matchId"] == match_id]
        if events is not None
        else []
    )
    warnings = [
        "period ends use the last observed event, not an official final whistle"
    ]
    period_minutes: dict[str, float | None] = {"1H": None, "2H": None}
    usable = match.get("duration", "Regular") == "Regular"
    if not usable:
        warnings.append("only regular-time matches are supported")
    if "duration" not in match:
        warnings.append("duration classification missing; regular-time convention used")
    for event in match_events:
        period = event.get("matchPeriod")
        seconds = _numeric(event.get("eventSec"))
        if period not in period_minutes or seconds is None:
            usable = False
            warnings.append("unsupported period or invalid event timestamp")
            continue
        observed = seconds / 60
        period_minutes[period] = max(period_minutes[period] or 0, observed)
    for period, observed in period_minutes.items():
        if observed is None or observed < 45:
            usable = False
            warnings.append(
                f"{period} endpoint missing or below 45 minutes; completeness unknown"
            )
    if not usable:
        return MatchPlayingTime(
            match_id,
            period_minutes,
            None,
            tuple(
                PlayerMinutes(
                    match_id,
                    row.team_id,
                    row.player_id,
                    None,
                    ("period durations unavailable or incomplete",),
                )
                for row in players
            ),
            tuple(dict.fromkeys(warnings)),
        )
    first_half = period_minutes["1H"]
    second_half = period_minutes["2H"]
    assert first_half is not None and second_half is not None
    duration = first_half + second_half
    warnings.append("nominal substitution/card minutes are coarse timing estimates")
    dismissals = defaultdict(set)
    for event in match_events:
        if any(tag["id"] in (1701, 1703) for tag in event["tags"]):
            if event["playerId"] == 0:
                warnings.append("dismissal event has unknown playerId 0")
                continue
            elapsed = event["eventSec"] / 60
            if event["matchPeriod"] == "2H":
                elapsed += first_half
            dismissals[(event["teamId"], event["playerId"])].add(elapsed)
    results = []
    for team in match["teamsData"].values():
        team_id = team["teamId"]
        formation = team["formation"]
        squad = {p["playerId"]: p for p in formation["lineup"] + formation["bench"]}
        team_players = [row for row in players if row.team_id == team_id]
        starts = {row.player_id: (0.0 if row.started else None) for row in team_players}
        ends = {row.player_id: duration for row in team_players}
        notes = defaultdict(list)
        substitutions = formation["substitutions"]
        previous = 0.0
        if substitutions is not None and substitutions != "null":
            for sub in substitutions:
                moment, warning = _clock_time(
                    sub.get("minute"), first_half, duration, substitution=True
                )
                if moment is not None and moment < previous:
                    moment, warning = (
                        None,
                        "substitution times contradict source list order",
                    )
                if warning:
                    for player in (sub["playerIn"], sub["playerOut"]):
                        notes[player].append(warning)
                ends[sub["playerOut"]] = moment
                starts[sub["playerIn"]] = moment
                if moment is not None:
                    previous = moment
        for row in team_players:
            player_id = row.player_id
            start, end = starts[player_id], ends[player_id]
            card = _numeric(squad[player_id].get("redCards"))
            tagged = dismissals.get((team_id, player_id), set())
            dismissal = None
            invalid_card = False
            if len(tagged) > 1:
                invalid_card = True
                notes[player_id].append(
                    "multiple distinct dismissal timestamps; timing ambiguous"
                )
            elif tagged:
                dismissal = next(iter(tagged))
                if card is None or card == 0:
                    notes[player_id].append(
                        "event dismissal conflicts with missing/zero redCards"
                    )
                else:
                    clock = (
                        dismissal
                        if dismissal <= first_half
                        else 45 + dismissal - first_half
                    )
                    if abs(clock - card) > 1:
                        notes[player_id].append(
                            "event dismissal and redCards clocks disagree"
                        )
            elif card is None:
                invalid_card = True
                notes[player_id].append(
                    "dismissal metadata missing/invalid and no tagged timing"
                )
            elif card > 0:
                dismissal, warning = _clock_time(card, first_half, duration)
                notes[player_id].append(
                    "dismissal estimated from nominal redCards clock"
                )
                if warning:
                    invalid_card = True
                    notes[player_id].append(warning)
            if dismissal is not None and start is not None and end is not None:
                if dismissal < start:
                    invalid_card = True
                    notes[player_id].append(
                        "dismissal precedes entry; interval inconsistent"
                    )
                elif dismissal > end:
                    notes[player_id].append(
                        "dismissal after substitution off; off-pitch card ignored"
                    )
                else:
                    end = dismissal
            if invalid_card or start is None or end is None or end < start:
                minutes = None
                notes[player_id].append("playing interval unavailable or inconsistent")
            else:
                minutes = end - start
            results.append(
                PlayerMinutes(
                    match_id,
                    team_id,
                    player_id,
                    minutes,
                    tuple(dict.fromkeys(notes[player_id])),
                )
            )
    return MatchPlayingTime(
        match_id,
        period_minutes,
        duration,
        tuple(results),
        tuple(dict.fromkeys(warnings)),
    )
