"""Request snapshots and modest validation at the public API boundary."""

from dataclasses import FrozenInstanceError

import pytest

from application.balancing_request import BalancingRequest
from optimizer.modes.optimization_mode import OptimizationMode
from tests.unit.test_composition_root import players


def test_request_copies_collections_without_cloning_players_or_nested_metadata():
    source = players()
    player = source[0]
    nested = {"label": "retained"}
    metadata = {"event": "original", "nested": nested}
    request = BalancingRequest(source, 2, OptimizationMode.FAST, metadata=metadata)
    source.clear()
    metadata["event"] = "changed"
    assert isinstance(request.players, tuple)
    assert len(request.players) == 4
    assert request.players[0] is player
    assert request.metadata["event"] == "original"
    assert request.metadata["nested"] is nested
    with pytest.raises(TypeError):
        request.metadata["event"] = "forbidden"
    with pytest.raises(FrozenInstanceError):
        request.number_of_teams = 3
    assert not hasattr(request, "__dict__")


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"players": None}, TypeError),
        ({"players": []}, ValueError),
        ({"number_of_teams": 0}, ValueError),
        ({"number_of_teams": -1}, ValueError),
        ({"number_of_teams": True}, TypeError),
        ({"number_of_teams": 2.5}, TypeError),
        ({"optimization_mode": "fast"}, TypeError),
        ({"optimization_mode": None}, TypeError),
        ({"title": 42}, TypeError),
        ({"metadata": []}, TypeError),
    ],
)
def test_invalid_requests(changes, error):
    arguments = dict(
        players=players(), number_of_teams=2, optimization_mode=OptimizationMode.FAST
    )
    arguments.update(changes)
    with pytest.raises(error):
        BalancingRequest(**arguments)


def test_optional_metadata_and_blank_title_preserve_engine_handling():
    request = BalancingRequest(players(), 2, OptimizationMode.STABLE, title=" ")
    assert request.metadata == {}
    assert request.title == " "
