from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.team import Team


@pytest.fixture
def team_factory():
    def _factory(team_id: int, players: list | None = None):
        team = MagicMock(spec=Team)
        team.id = team_id
        team.players = list(players) if players is not None else [object()]
        return team

    return _factory
