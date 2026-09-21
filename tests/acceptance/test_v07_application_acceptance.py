"""Final application-to-report acceptance matrix, with no live bootstrap I/O."""

from dataclasses import replace

import pytest

import main
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.results.base_report_result import BaseReportResult
from application.results.evaluation_result import EvaluationResult
from application.results.global_report_result import GlobalReportResult
from application.results.optimization_result import OptimizationResult
from application.results.report_mode import ReportMode
from configuration.application_config import ApplicationConfig
from configuration.composition_root import create_balancing_composition
from exporters.html_v2.html_exporter import HtmlExporterV2
from optimizer.modes.optimization_mode import OptimizationMode
from tests.acceptance import test_application_behavior_contract as contract
from tests.acceptance.test_balancing_application_api import (
    assert_same_report,
    without_timing,
)
from tests.acceptance.test_engine_acceptance import (
    canonical_membership,
    stable_config,
    synthetic_players,
)
from tests.unit.test_composition_root import players, small_config

characterized_run = contract.composed_run


def acceptance_config():
    config = ApplicationConfig.production_defaults()
    # Existing characterized test budgets; production defaults remain untouched.
    return replace(
        config,
        stable=stable_config(),
        global_search=replace(
            config.global_search,
            maximum_nodes=500,
            maximum_evaluations=50,
            maximum_elapsed_seconds=None,
        ),
    )


@pytest.mark.parametrize(
    "mode,fingerprint",
    [
        (OptimizationMode.FAST, contract.FAST_TEAMS),
        (OptimizationMode.STABLE, contract.STABLE_TEAMS),
        (OptimizationMode.GLOBAL, contract.GLOBAL_TEAMS),
    ],
)
def test_public_flow_preserves_characterized_report(
    characterized_run, mode, fingerprint
):
    source, scoring, objective, expected = characterized_run(mode)
    if mode is OptimizationMode.GLOBAL:
        # Reference: the characterized application owner, with unchanged fingerprints.
        expected = contract.run_characterized_global(
            source, scoring, objective, expected
        )
    actual = BalancingApplication(acceptance_config()).run(
        BalancingRequest(
            source,
            4,
            mode,
            title="Application acceptance",
            metadata={"contract": "SCRUM-37"},
        )
    )
    assert_same_report(actual, expected)
    assert canonical_membership(actual.teams) == contract.expected_membership(
        fingerprint
    )
    assert actual.title == "Application acceptance"
    assert actual.mode is ReportMode.OPTIMIZED
    assert actual.metadata["optimization_mode"] == mode.value
    assert actual.metadata["optimization_deterministic"] is mode.deterministic
    if mode is OptimizationMode.GLOBAL:
        assert isinstance(actual, GlobalReportResult)
        for field in (
            "initial_incumbent_score",
            "nodes_visited",
            "complete_solutions_evaluated",
            "pruned_nodes",
            "capacity_prunes",
            "seed_prunes",
            "bound_prunes",
            "stopped_by_limit",
            "optimality_proven",
            "stop_reason",
        ):
            assert getattr(actual, field) == getattr(expected, field)
        assert actual.stop_reason == "EVALUATION_LIMIT"
        assert (
            actual.metadata["global_optimization"].keys()
            == expected.metadata["global_optimization"].keys()
        )
        assert (
            actual.as_dict()["metadata"]["global_optimization"]
            == actual.metadata["global_optimization"]
        )
        assert "stable_optimization" in actual.metadata
        assert not hasattr(actual, "raw_result")
    else:
        assert isinstance(actual, OptimizationResult)
    if mode is OptimizationMode.STABLE:
        assert actual.metadata["stable_optimization"]["completed_restarts"] == 3
        assert actual.metadata["stable_optimization"]["stop_reason"] == "restart_limit"


@pytest.fixture(scope="module")
def accepted_flows():
    compositions = []

    def compose(config):
        composition = create_balancing_composition(config)
        compositions.append(composition)
        return composition

    application = BalancingApplication(acceptance_config(), composition_factory=compose)
    request = BalancingRequest(
        synthetic_players(), 4, OptimizationMode.FAST, title="Application acceptance"
    )
    results = {}
    for name, mode in (
        ("FAST", OptimizationMode.FAST),
        ("STABLE", OptimizationMode.STABLE),
        ("GLOBAL", OptimizationMode.GLOBAL),
        ("FAST replay", OptimizationMode.FAST),
        ("STABLE replay", OptimizationMode.STABLE),
    ):
        result = application.run(replace(request, optimization_mode=mode))
        results[name] = (result, compositions[-1])
    assigned = synthetic_players()
    for index, player in enumerate(assigned):
        player.team_number = index // 5 + 1
    result = application.run(
        replace(request, players=assigned, optimization_mode=OptimizationMode.GLOBAL)
    )
    results["PREASSIGNED"] = (result, compositions[-1])
    return results


def test_fast_stable_global_fast_isolation_and_stable_replay(accepted_flows):
    assert_same_report(accepted_flows["FAST replay"][0], accepted_flows["FAST"][0])
    assert_same_report(accepted_flows["STABLE replay"][0], accepted_flows["STABLE"][0])
    compositions = [
        accepted_flows[name][1] for name in ("FAST", "STABLE", "GLOBAL", "FAST replay")
    ]
    assert len({id(c.balancer) for c in compositions}) == 4
    assert len({id(c.balancer.optimizer.pipeline) for c in compositions}) == 4
    assert [c.balancer.optimization_mode for c in compositions] == [
        OptimizationMode.FAST,
        OptimizationMode.STABLE,
        OptimizationMode.STABLE,
        OptimizationMode.FAST,
    ]


def test_preassigned_acceptance_ignores_global_optimization(accepted_flows):
    result, _ = accepted_flows["PREASSIGNED"]
    assert isinstance(result, EvaluationResult)
    assert isinstance(result, BaseReportResult)
    assert result.mode is ReportMode.PREASSIGNED
    assert result.evaluation_only and not result.optimized
    expected = synthetic_players()
    expected_groups = tuple(
        tuple(p.steam_id for p in expected[i : i + 5]) for i in range(0, 20, 5)
    )
    assert canonical_membership(result.teams) == expected_groups
    assert result.initial_score == result.final_score
    assert result.improvement == 0 and result.iterations == 0
    assert result.metadata["optimization_mode"] is None
    assert result.metadata["optimization_applied"] is False
    assert "global_optimization" not in result.metadata
    assert "stable_optimization" not in result.metadata


def test_custom_config_reaches_public_result():
    result = BalancingApplication(small_config()).run(
        BalancingRequest(
            players(),
            2,
            OptimizationMode.FAST,
            title="Small configured event",
        )
    )
    assert isinstance(result, BaseReportResult)
    assert result.team_count == 2 and result.player_count == 4
    assert all(len(team.players) == 2 for team in result.teams)
    assert "Seed 2 Separation" in result.restrictions
    assert result.title == "Small configured event"


def assert_html_report(path, result, title):
    assert path.is_file()
    html = path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert '<html lang="es">' in html
    assert f'data-report-mode="{result.mode.value}"' in html
    assert title in html
    assert "section-panels" in html
    assert result.teams[0].players[0].nick in html
    assert "GlobalOptimizationResult(" not in html


@pytest.mark.parametrize("flow", ["FAST", "STABLE", "GLOBAL", "PREASSIGNED"])
def test_html_exporter_accepts_common_public_result(accepted_flows, tmp_path, flow):
    result, composition = accepted_flows[flow]
    exporter = composition.balancer.exporter
    assert isinstance(exporter, HtmlExporterV2)
    before = without_timing(result.as_dict())
    expected_path = tmp_path / flow.lower() / "report.html"
    returned = exporter.export(result, expected_path)
    assert returned == expected_path
    assert_html_report(returned, result, composition.config.event.report_title)
    assert without_timing(result.as_dict()) == before
    assert result.summary()["score"] == result.score


@pytest.mark.parametrize("mode", [OptimizationMode.FAST, OptimizationMode.GLOBAL])
def test_main_bootstrap_exports_application_result_offline(monkeypatch, tmp_path, mode):
    config = small_config()
    destination = tmp_path / "bootstrap.html"
    config = replace(
        config,
        optimization_mode=mode,
        event=replace(config.event, report_title="Bootstrap acceptance"),
        paths=replace(config.paths, output_report=destination),
        faceit=replace(config.faceit, run_import=False),
        debug_players=False,
        debug_final_teams=False,
    )
    monkeypatch.setattr(
        ApplicationConfig, "production_defaults", classmethod(lambda cls: config)
    )
    monkeypatch.setattr(
        main, "resolve_players_file", lambda config: tmp_path / "unused.csv"
    )
    monkeypatch.setattr(main.CssStatsImporter, "load", lambda self, source: players())

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Bootstrap must not call live FACEIT or legacy GLOBAL orchestration"
        )

    monkeypatch.setattr(main, "run_faceit_import", forbidden)
    assert not hasattr(main, "run_global_optimization")
    requests, reports, console_results = [], [], []
    original_export = HtmlExporterV2.export

    class ObservedApplication(BalancingApplication):
        def run(self, request):
            requests.append(request)
            return super().run(request)

    def export(self, result, output):
        reports.append(result)
        return original_export(self, result, output)

    monkeypatch.setattr(main, "BalancingApplication", ObservedApplication)
    monkeypatch.setattr(HtmlExporterV2, "export", export)
    monkeypatch.setattr(main, "print_global_optimization", console_results.append)
    assert main.main() == 0
    assert len(requests) == len(reports) == 1
    assert requests[0].optimization_mode is mode
    assert isinstance(reports[0], BaseReportResult)
    assert_html_report(destination, reports[0], "Bootstrap acceptance")
    if mode is OptimizationMode.GLOBAL:
        assert isinstance(reports[0], GlobalReportResult)
        assert console_results == reports
    else:
        assert console_results == []
