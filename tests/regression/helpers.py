from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from models.player import Player
from models.team import Team
from scrapers.player_record import ActivityRecord

FIXTURES_DIRECTORY = Path(__file__).resolve().parents[1] / "fixtures"
PLAYERS_FIXTURE = FIXTURES_DIRECTORY / "lan_2026_players.json"
BASELINE_FIXTURE = FIXTURES_DIRECTORY / "lan_2026_baseline.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fixture_file:
        value = json.load(fixture_file)

    if not isinstance(value, dict):
        raise TypeError(f"Fixture {path.name} must contain a JSON object.")
    return value


def load_lan_2026_fixture() -> dict[str, Any]:
    fixture = _load_json(PLAYERS_FIXTURE)
    if fixture.get("fixture_version") != 1:
        raise ValueError("Unsupported LAN 2026 fixture version.")
    return fixture


def load_lan_2026_players() -> list[Player]:
    fixture = load_lan_2026_fixture()
    records = fixture.get("players")
    if not isinstance(records, list) or len(records) != 20:
        raise ValueError("LAN 2026 fixture must contain exactly 20 players.")

    nicks = [record.get("nick") for record in records]
    steam_ids = [record.get("steam_id") for record in records]
    if any(not isinstance(nick, str) or not nick.strip() for nick in nicks):
        raise ValueError("Every LAN 2026 player must have a nickname.")
    if len({nick.casefold() for nick in nicks}) != len(nicks):
        raise ValueError("LAN 2026 fixture contains duplicate nicknames.")
    if any(not isinstance(value, str) or not value.strip() for value in steam_ids):
        raise ValueError("Every LAN 2026 player must have a Steam ID.")
    if len(set(steam_ids)) != len(steam_ids):
        raise ValueError("LAN 2026 fixture contains duplicate Steam IDs.")
    if sum(record.get("seed") == 1 for record in records) != 4:
        raise ValueError("LAN 2026 fixture must contain exactly four seed-1 players.")

    players = []
    for record in records:
        activity = record.get("activity")
        if not isinstance(activity, Mapping):
            raise TypeError("Every LAN 2026 player must contain activity data.")
        players.append(
            Player(
                nick=record["nick"],
                steam_id=record["steam_id"],
                elo=record["elo"],
                level=record["level"],
                kd=record["kd"],
                adr=record["adr"],
                kpr=record["kpr"],
                hs=record["hs"],
                winrate=record["winrate"],
                seed=record["seed"],
                activity=ActivityRecord(**activity),
            )
        )

    if any(player.team_number is not None for player in players):
        raise ValueError("LAN 2026 regression players cannot be preassigned.")
    return players


def load_lan_2026_baseline() -> dict[str, Any]:
    baseline = _load_json(BASELINE_FIXTURE)
    if baseline.get("baseline_version") != 1:
        raise ValueError("Unsupported LAN 2026 baseline version.")
    if baseline.get("fixture_version") != 1:
        raise ValueError("Baseline and player fixture versions do not match.")
    return baseline


def canonical_team_membership(
    teams: Sequence[Team],
) -> tuple[tuple[str, ...], ...]:
    memberships = []
    for team in teams:
        identities = []
        for player in team.players:
            if not player.steam_id:
                raise ValueError("Canonical team membership requires Steam IDs.")
            identities.append(player.steam_id)
        memberships.append(tuple(sorted(identities)))
    return tuple(sorted(memberships))
