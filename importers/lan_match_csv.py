"""Strict schema validation for a single LAN player-map CSV row."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from models.lan_match import PlayerMapStatistics

IDENTITY_COLUMNS = ("matchid", "steamid64", "team", "name")
NUMERIC_COLUMNS = (
    "mapnumber",
    "kills",
    "deaths",
    "damage",
    "assists",
    "enemy5ks",
    "enemy4ks",
    "enemy3ks",
    "enemy2ks",
    "utility_count",
    "utility_damage",
    "utility_successes",
    "utility_enemies",
    "flash_count",
    "flash_successes",
    "health_points_removed_total",
    "health_points_dealt_total",
    "shots_fired_total",
    "shots_on_target_total",
    "v1_count",
    "v1_wins",
    "v2_count",
    "v2_wins",
    "entry_count",
    "entry_wins",
    "equipment_value",
    "money_saved",
    "kill_reward",
    "live_time",
    "head_shot_kills",
    "cash_earned",
    "enemies_flashed",
)
SUPPORTED_COLUMNS = (
    "matchid",
    "mapnumber",
    "steamid64",
    "team",
    "name",
    *NUMERIC_COLUMNS[1:],
)
REQUIRED_COLUMNS = frozenset(SUPPORTED_COLUMNS)


class LanMatchCsvError(ValueError):
    """Raised when the input cannot satisfy the LAN CSV contract."""


def validate_columns(columns: Sequence[str | None]) -> None:
    actual = set(columns)
    missing = REQUIRED_COLUMNS - actual
    unknown = actual - REQUIRED_COLUMNS
    if missing:
        raise LanMatchCsvError(f"missing required columns: {', '.join(sorted(missing))}")
    if unknown:
        rendered = ", ".join("<unnamed>" if item is None else item for item in sorted(unknown, key=str))
        raise LanMatchCsvError(f"unknown columns are not supported: {rendered}")
    if len(columns) != len(actual):
        raise LanMatchCsvError("duplicate columns are not supported")


def parse_player_map_row(row: Mapping[str, str | None]) -> PlayerMapStatistics:
    """Parse one strict row; blank or malformed required values are errors."""
    validate_columns(tuple(row.keys()))
    values: dict[str, str | int] = {}
    for column in IDENTITY_COLUMNS:
        raw = row[column]
        if raw is None or not raw.strip():
            raise LanMatchCsvError(f"{column} is required and cannot be blank")
        values[column] = raw.strip()
    for column in NUMERIC_COLUMNS:
        raw = row[column]
        if raw is None or not raw.strip():
            raise LanMatchCsvError(f"{column} is required and cannot be blank")
        try:
            value = int(raw)
        except ValueError as error:
            raise LanMatchCsvError(f"{column} must be a non-negative integer") from error
        if value < 0:
            raise LanMatchCsvError(f"{column} must be a non-negative integer")
        values[column] = value
    return PlayerMapStatistics(**values)
