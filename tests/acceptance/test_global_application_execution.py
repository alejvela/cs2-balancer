"""Production GLOBAL through the public API, using SCRUM-37 fingerprints."""

import subprocess
import sys
from pathlib import Path

import pytest

from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.results.base_report_result import BaseReportResult
from application.results.global_report_result import GlobalReportResult
from optimizer.modes.optimization_mode import OptimizationMode
from tests.acceptance import test_application_behavior_contract as contract
from tests.acceptance.test_balancing_application_api import without_timing
from tests.acceptance.test_engine_acceptance import canonical_membership

characterized_run = contract.composed_run


@pytest.mark.parametrize(
    "node_budget,fingerprint,stop_reason",
    [
        (1, contract.STABLE_TEAMS, "NODE_LIMIT"),
        (500, contract.GLOBAL_TEAMS, "EVALUATION_LIMIT"),
    ],
)
def test_default_global_matches_characterized_execution(
    characterized_run,
    node_budget,
    fingerprint,
    stop_reason,
):
    players, scoring, objective, warm_start = characterized_run(OptimizationMode.GLOBAL)
    config = contract.contract_config(maximum_nodes=node_budget)
    expected = contract.run_characterized_global(
        players, scoring, objective, warm_start, maximum_nodes=node_budget
    )
    # No runner injection: this must perform real GLOBAL search.
    actual = BalancingApplication(config).run(
        BalancingRequest(
            players,
            4,
            OptimizationMode.GLOBAL,
            title=expected.title,
            metadata={"contract": "SCRUM-37"},
        )
    )
    assert isinstance(actual, GlobalReportResult)
    assert isinstance(actual, BaseReportResult)
    assert canonical_membership(actual.teams) == contract.expected_membership(
        fingerprint
    )
    assert canonical_membership(actual.teams) == canonical_membership(expected.teams)
    for field in ("score", "initial_score", "final_score", "improvement", "penalty"):
        assert getattr(actual, field) == pytest.approx(
            getattr(expected, field), abs=1e-6
        )
    assert {k: r.score for k, r in actual.restrictions.items()} == pytest.approx(
        {k: r.score for k, r in expected.restrictions.items()},
        abs=1e-6,
    )
    for field in (
        "nodes_visited",
        "complete_solutions_evaluated",
        "pruned_nodes",
        "capacity_prunes",
        "seed_prunes",
        "bound_prunes",
        "stopped_by_limit",
        "optimality_proven",
        "stop_reason",
        "initial_incumbent_score",
    ):
        assert getattr(actual, field) == getattr(expected, field)
    assert actual.global_stop_reason == stop_reason
    assert actual.initial_score == warm_start.final_score
    assert actual.iterations == 0
    assert actual.history == ()
    assert actual.total_evaluations == expected.complete_solutions_evaluated
    assert without_timing(actual.metadata) == without_timing(expected.metadata)
    assert without_timing(actual.metadata["stable_optimization"]) == without_timing(
        warm_start.metadata["stable_optimization"],
    )
    assert (
        actual.as_dict()["metadata"]["global_optimization"]
        == actual.metadata["global_optimization"]
    )
    assert warm_start.metadata["optimization_mode"] == "stable"
    assert actual.title == expected.title
    assert not hasattr(actual, "raw_result")
    if node_budget == 1:
        assert actual.improvement == 0
    else:
        assert actual.improvement > 0


def test_default_global_import_and_execution_are_independent_of_main():
    script = """
import importlib.abc
import sys
from dataclasses import replace
class BlockMain(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "main":
            raise AssertionError("GLOBAL execution must not import main")
sys.meta_path.insert(0, BlockMain())
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.results.global_report_result import GlobalReportResult
from configuration.application_config import ApplicationConfig
from models.player import Player
from optimizer.modes.optimization_mode import OptimizationMode
config = ApplicationConfig.production_defaults()
config = replace(config,
    event=replace(config.event, number_of_teams=2, team_size=2),
    stable=replace(config.stable, maximum_restarts=1, minimum_restarts=1,
        convergence_patience=1, target_confirmation_restarts=1, minimum_unique_solutions=0),
    global_search=replace(config.global_search, maximum_nodes=1, maximum_elapsed_seconds=None))
players = [Player(nick=f"P{i}", steam_id=f"P{i}", elo=1500+i*100, kd=1.0) for i in range(4)]
result = BalancingApplication(config).run(BalancingRequest(players, 2, OptimizationMode.GLOBAL))
assert isinstance(result, GlobalReportResult)
assert result.stop_reason == "NODE_LIMIT"
assert result.metadata["optimization_mode"] == "global"
assert "stable_optimization" in result.metadata
assert "main" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
