"""Explicit external position decisions, scoped to historical player/team pairs."""

import json
from pathlib import Path

from .roles import PositionReview

FIELDS = {"player_id", "team_id", "status", "evidence", "note"}


def _unique_keys(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError(f"duplicate JSON key {key!r}")
        record[key] = value
    return record


def load_position_reviews(
    path: str | Path, historical_pairs: frozenset[tuple[int, int]]
) -> dict[tuple[int, int], PositionReview]:
    """Load a replacement review set; an empty array intentionally includes nobody.

    Evidence is recorded, not fetched or independently verified. Historical pairs
    must come from match sheets, including unused bench entries, never currentTeamId.
    """
    path = Path(path).expanduser()
    try:
        records = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError(f"{path}: cannot read review JSON: {error}") from error
    if not isinstance(records, list):
        raise ValueError(f"{path}: expected a JSON array of review decisions")
    reviews = {}
    for number, record in enumerate(records):
        context = f"{path}[{number}]"
        if not isinstance(record, dict) or record.keys() != FIELDS:
            raise ValueError(
                f"{context}: expected exactly these fields: {', '.join(sorted(FIELDS))}"
            )
        key = (record["player_id"], record["team_id"])
        if any(type(value) is not int or value <= 0 for value in key):
            raise ValueError(
                f"{context}: player_id and team_id must be positive integer IDs"
            )
        if key in reviews:
            raise ValueError(f"{context}: duplicate player/team decision {key}")
        if key not in historical_pairs:
            raise ValueError(
                f"{context}: unknown historical player/team reference {key}"
            )
        if record["status"] not in ("included", "excluded"):
            raise ValueError(f"{context}: status must be 'included' or 'excluded'")
        try:
            reviews[key] = PositionReview(
                record["status"], record["evidence"], record["note"]
            )
        except ValueError as error:
            raise ValueError(f"{context}: {error}") from error
    return reviews
