"""The application API preserves the existing characterized report contract."""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import main
from application.balancing_application import (
    BalancingApplication,
    GlobalExecutionUnavailableError,
)
from application.balancing_request import BalancingRequest
from application.lan_balancer import LanBalancer
from application.results.base_report_result import BaseReportResult
from application.results.evaluation_result import EvaluationResult
from application.results.report_mode import ReportMode
from configuration.application_config import ApplicationConfig
from configuration.composition_root import create_balancing_composition
from optimizer.modes.optimization_mode import OptimizationMode
from tests.acceptance import test_application_behavior_contract as contract
from tests.acceptance.test_engine_acceptance import (
    canonical_membership,
    stable_config,
    synthetic_players,
)
from tests.unit.test_composition_root import players, small_config

# Reuse SCRUM-37's fixture and fingerprints rather than maintaining new snapshots.
legacy_run = contract.composed_run


def without_timing(value):
    if isinstance(value, dict):
        return {k: without_timing(v) for k, v in value.items() if "elapsed" not in k}
    if isinstance(value, (tuple, list)):
        return [without_timing(v) for v in value]
    return value


def assert_same_report(actual, expected):
    assert isinstance(actual, BaseReportResult)
    assert canonical_membership(actual.teams) == canonical_membership(expected.teams)
    for name in ("initial_score", "final_score", "score", "improvement", "penalty"):
        assert getattr(actual, name) == pytest.approx(getattr(expected, name), abs=1e-6)
    assert actual.mode is expected.mode
    assert actual.optimized == expected.optimized
    assert actual.evaluation_only == expected.evaluation_only
    assert actual.iterations == expected.iterations
    assert actual.total_evaluations == expected.total_evaluations
    assert {k: r.score for k, r in actual.restrictions.items()} == pytest.approx(
        {k: r.score for k, r in expected.restrictions.items()},
        abs=1e-6,
    )
    assert without_timing(actual.metadata) == without_timing(expected.metadata)
    assert without_timing(actual.history.as_dict()) == without_timing(
        expected.history.as_dict()
    )


@pytest.mark.parametrize(
    "mode,fingerprint",
    [
        (OptimizationMode.FAST, contract.FAST_TEAMS),
        (OptimizationMode.STABLE, contract.STABLE_TEAMS),
    ],
)
def test_api_matches_scrum37_reports(legacy_run, mode, fingerprint):
    source_players, _, _, expected = legacy_run(mode)
    config = replace(ApplicationConfig.production_defaults(), stable=stable_config())
    metadata = {"contract": "SCRUM-37"}
    request = BalancingRequest(source_players, 4, mode, metadata=metadata)
    actual = BalancingApplication(config).run(request)
    assert_same_report(actual, expected)
    assert canonical_membership(actual.teams) == contract.expected_membership(
        fingerprint
    )
    assert metadata == {"contract": "SCRUM-37"}
    actual.metadata["caller_change"] = True
    assert "caller_change" not in request.metadata


def test_fast_stable_fast_on_same_application_has_no_cross_run_state():
    config = replace(ApplicationConfig.production_defaults(), stable=stable_config())
    compositions = []

    def compose(config):
        composition = create_balancing_composition(config)
        compositions.append(composition)
        return composition

    application = BalancingApplication(config, composition_factory=compose)
    request = BalancingRequest(synthetic_players(), 4, OptimizationMode.FAST)
    first = application.run(request)
    stable = application.run(
        replace(request, optimization_mode=OptimizationMode.STABLE)
    )
    last = application.run(request)
    assert_same_report(last, first)
    assert stable.metadata["optimization_mode"] == "stable"
    assert stable.metadata["stable_optimization"]["completed_restarts"] == 3
    assert [c.balancer.optimization_mode for c in compositions] == [
        OptimizationMode.FAST,
        OptimizationMode.STABLE,
        OptimizationMode.FAST,
    ]
    assert len({id(c.balancer) for c in compositions}) == 3
    assert len({id(c.balancer.optimizer.pipeline) for c in compositions}) == 3
    assert config.optimization_mode is OptimizationMode.GLOBAL


def test_custom_config_and_request_team_count_reach_composition():
    config = small_config()
    # The request owns the execution team count; the config still owns team size.
    config = replace(config, event=replace(config.event, number_of_teams=3))
    observed = []

    def compose(run_config):
        c = create_balancing_composition(run_config)
        observed.append(c)
        return c

    result = BalancingApplication(config, composition_factory=compose).run(
        BalancingRequest(players(), 2, OptimizationMode.FAST, title="Request title"),
    )
    composition = observed[0]
    assert composition.config.event.number_of_teams == 2
    assert composition.config.event.expected_player_count == 4
    assert config.event.number_of_teams == 3
    assert composition.scoring_model.minimum_available_weight == 10
    assert composition.objective_engine.restrictions[3].max_deviation == 0.6
    assert composition.balancer.optimizer.pipeline.phases[0].max_iterations == 2
    assert len(result.teams) == 2
    assert result.title == "Request title"


def test_global_runner_receives_request_composition_and_stable_warm_start():
    config = small_config()
    request = BalancingRequest(
        players(), 2, OptimizationMode.GLOBAL, metadata={"tag": "input"}
    )
    returned = []

    class Runner:
        def run(self, *, request: BalancingRequest, composition, warm_start):
            assert request is original_request
            assert composition.config.optimization_mode is OptimizationMode.GLOBAL
            assert composition.balancer.optimization_mode is OptimizationMode.STABLE
            assert warm_start.metadata["optimization_mode"] == "stable"
            assert warm_start.metadata["tag"] == "input"
            assert "stable_optimization" in warm_start.metadata
            assert isinstance(warm_start, BaseReportResult)
            result = EvaluationResult(
                teams=warm_start.teams,
                objective_result=warm_start.objective_result,
                title="Delegated result",
                metadata={"runner": True},
            )
            returned.append(result)
            return result

    original_request = request
    result = BalancingApplication(config, global_runner=Runner()).run(request)
    assert result is returned[0]
    assert isinstance(result, BaseReportResult)
    assert request.metadata == {"tag": "input"}


def test_global_without_runner_fails_before_warm_start(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Missing dependency must fail before optimization")

    monkeypatch.setattr(LanBalancer, "run_players", forbidden)
    with pytest.raises(GlobalExecutionUnavailableError, match="injected GlobalRunner"):
        BalancingApplication(small_config()).run(
            BalancingRequest(players(), 2, OptimizationMode.GLOBAL),
        )


def test_global_runner_cannot_return_an_engine_only_result():
    class Runner:
        def run(self, **kwargs):
            return object()

    with pytest.raises(TypeError, match="BaseReportResult"):
        BalancingApplication(small_config(), global_runner=Runner()).run(
            BalancingRequest(players(), 2, OptimizationMode.GLOBAL),
        )


@pytest.mark.parametrize("mode", list(OptimizationMode))
@pytest.mark.parametrize("with_runner", [False, True])
def test_preassigned_is_evaluation_only_for_every_mode(mode, with_runner):
    assigned = players()
    for i, player in enumerate(assigned):
        player.team_number = 1 + i // 2

    class ForbiddenRunner:
        def run(self, **kwargs):
            raise AssertionError("PREASSIGNED must not execute GLOBAL")

    result = BalancingApplication(
        small_config(),
        global_runner=ForbiddenRunner() if with_runner else None,
    ).run(BalancingRequest(assigned, 2, mode, metadata={"source": "request"}))
    assert isinstance(result, BaseReportResult)
    assert result.mode is ReportMode.PREASSIGNED
    assert result.evaluation_only and not result.optimized
    assert canonical_membership(result.teams) == (
        ("CUSTOM-0", "CUSTOM-1"),
        ("CUSTOM-2", "CUSTOM-3"),
    )
    assert result.initial_score == result.final_score
    assert result.metadata["optimization_mode"] is None
    assert result.metadata["optimization_applied"] is False
    assert result.metadata["preassigned"] is True
    assert result.metadata["source"] == "request"


def test_legacy_global_adapter_uses_request_config_and_public_result():
    runner = main.LegacyGlobalRunner()
    result = BalancingApplication(small_config(), global_runner=runner).run(
        BalancingRequest(players(), 2, OptimizationMode.GLOBAL, title="Custom GLOBAL"),
    )
    assert isinstance(result, BaseReportResult)
    assert result.title == "Custom GLOBAL"
    assert result.metadata["optimization_mode"] == "global"
    assert result.metadata["global_optimization"]["stop_reason"] == "NODE_LIMIT"
    assert runner.last_search_result.stop_reason == "NODE_LIMIT"
    assert result is not runner.last_search_result


@pytest.mark.parametrize("mode", list(OptimizationMode))
def test_entrypoint_uses_application_once_and_exports_public_result(
    monkeypatch, tmp_path, mode
):
    config = small_config()
    monkeypatch.setattr(main, "APPLICATION_CONFIG", config)
    for name, value in {
        "NUMBER_OF_TEAMS": 2,
        "TEAM_SIZE": 2,
        "EXPECTED_PLAYER_COUNT": 4,
        "OPTIMIZATION_MODE": mode,
        "STABLE_OPTIMIZATION_CONFIG": config.stable,
        "GLOBAL_OPTIMIZATION_CONFIG": config.global_search,
        "REPORT_TITLE": "Entrypoint report",
        "DEBUG_PLAYERS": False,
        "DEBUG_FINAL_TEAMS": False,
    }.items():
        monkeypatch.setattr(main, name, value)
    monkeypatch.setattr(main, "resolve_players_file", lambda: tmp_path / "unused.csv")
    monkeypatch.setattr(main.CssStatsImporter, "load", lambda self, source: players())
    compositions, requests, reports, searches = [], [], [], []

    def compose(config):
        composition = create_balancing_composition(config)
        compositions.append(composition)
        return composition

    class TrackedApplication(BalancingApplication):
        def run(self, request):
            requests.append(request)
            return super().run(request)

    def export(self, *, result, output):
        reports.append(result)
        return tmp_path / "report.html"

    monkeypatch.setattr(main.composition_root, "create_balancing_composition", compose)
    monkeypatch.setattr(main, "BalancingApplication", TrackedApplication)
    monkeypatch.setattr(LanBalancer, "export", export)
    monkeypatch.setattr(main, "print_global_optimization", searches.append)
    assert main.main() == 0
    assert len(compositions) == len(requests) == len(reports) == 1
    assert requests[0].optimization_mode is mode
    assert isinstance(reports[0], BaseReportResult)
    assert reports[0].metadata["optimization_mode"] == mode.value
    assert reports[0].title == "Entrypoint report"
    assert len(searches) == (1 if mode is OptimizationMode.GLOBAL else 0)


def test_application_import_and_execution_do_not_import_main():
    script = """
import importlib.abc
import sys
from dataclasses import replace
class BlockMain(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "main":
            raise AssertionError("Application must not import main")
sys.meta_path.insert(0, BlockMain())
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.results.base_report_result import BaseReportResult
from configuration.application_config import ApplicationConfig
from models.player import Player
from optimizer.modes.optimization_mode import OptimizationMode
config = ApplicationConfig.production_defaults()
config = replace(config, event=replace(config.event, team_size=2))
players = [Player(nick=f"P{i}", steam_id=f"P{i}", elo=1500+i*100, kd=1.0) for i in range(4)]
result = BalancingApplication(config).run(BalancingRequest(players, 2, OptimizationMode.FAST))
assert isinstance(result, BaseReportResult)
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
