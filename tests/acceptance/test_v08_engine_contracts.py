"""SCRUM-52: integrated contracts through production application/bootstrap."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from configuration.application_config import ApplicationConfig
from configuration.composition_root import create_balancing_composition
from models.player_identity import logical_player_identity
from optimizer.modes.optimization_mode import OptimizationMode
from tests.acceptance.test_engine_acceptance import stable_config, synthetic_players


def acceptance_config(mode=OptimizationMode.FAST, **global_options):
    config = ApplicationConfig.production_defaults()
    return replace(
        config,
        optimization_mode=mode,
        event=replace(config.event, number_of_teams=2, team_size=2),
        stable=stable_config(),
        global_search=replace(
            config.global_search,
            **dict(
                dict(maximum_nodes=None, maximum_evaluations=None,
                     maximum_elapsed_seconds=None),
                **global_options,
            ),
        ),
        faceit=replace(config.faceit, run_import=False),
        debug_players=False,
        debug_final_teams=False,
    )


def assert_report(result, roster, config):
    composition = create_balancing_composition(config)
    flat = [p for team in result.teams for p in team.players]
    assert len(result.teams) == 2
    assert all(len(t.players) == 2 for t in result.teams)
    assert {id(p) for p in flat} == {id(p) for p in roster}
    assert sorted(map(logical_player_identity, flat)) == sorted(
        map(logical_player_identity, roster)
    )
    assert all(sum(p.seed == 1 for p in t.players) <= 1 for t in result.teams)
    fresh = composition.objective_engine.evaluate(result.teams)
    assert result.final_score == fresh.score
    assert result.penalty == fresh.penalty == 0
    assert result.is_valid and fresh.is_valid
    assert result.restrictions == fresh.restrictions
    assert result.metadata["optimization_mode"] == config.optimization_mode.value
    assert result.as_dict()["metadata"] == result.metadata


@pytest.mark.parametrize("mode", list(OptimizationMode))
def test_application_contracts(mode):
    config = acceptance_config(mode)
    roster = synthetic_players()[:4]
    result = BalancingApplication(config).run(BalancingRequest(roster, 2, mode))
    assert_report(result, roster, config)
    if mode is OptimizationMode.STABLE:
        assert result.metadata["stable_optimization"]["completed_restarts"] >= 1
    if mode is OptimizationMode.GLOBAL:
        assert result.search_exhausted and not result.stopped_by_limit
        assert result.stop_reason == "SEARCH_EXHAUSTED"
        assert result.optimality_proven == result.proof_certificate.optimality_proven
        assert result.complete_solutions_evaluated + result.pruned_nodes <= result.nodes_visited


@pytest.mark.parametrize("mode", list(OptimizationMode))
def test_duplicate_logical_pool_rejected(mode):
    roster = synthetic_players()[:4]
    roster[1].steam_id = roster[0].steam_id
    with pytest.raises(ValueError, match="[Dd]uplicate|duplicad"):
        BalancingApplication(acceptance_config(mode)).run(
            BalancingRequest(roster, 2, mode)
        )


@pytest.mark.parametrize("mode", list(OptimizationMode))
@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf")])
def test_invalid_objective_numbers_cross_application_boundary(mode, value):
    def compose(config):
        composition = create_balancing_composition(config)
        # Corrupt an actual restriction after construction, as a mutable extension can.
        composition.objective_engine.restrictions[0]._weight = value
        return composition

    with pytest.raises(TypeError if isinstance(value, bool) else ValueError):
        BalancingApplication(acceptance_config(mode), composition_factory=compose).run(
            BalancingRequest(synthetic_players()[:4], 2, mode)
        )


def test_global_without_incumbent_proof_and_nullable_serialization():
    config = acceptance_config(OptimizationMode.GLOBAL, use_incumbent=False, require_proof=True)
    roster = synthetic_players()[:4]
    result = BalancingApplication(config).run(
        BalancingRequest(roster, 2, OptimizationMode.GLOBAL)
    )
    assert_report(result, roster, config)
    assert result.initial_score is None and result.improvement is None
    assert "stable_optimization" not in result.metadata
    assert result.optimality_proven and result.proof_certificate.optimality_proven
    assert result.search_exhausted and not result.stopped_by_limit
    assert result.metadata["global_optimization"]["initial_incumbent_score"] is None
    assert json.loads(json.dumps(result.as_dict(), default=str))["initial_score"] is None


def test_documented_migration_example():
    from docs.v08_migration_example import run_example

    result = run_example()
    assert result.initial_score is None and result.improvement is None
    assert result.search_exhausted and result.optimality_proven
    assert result.proof_certificate.optimality_proven


@pytest.mark.parametrize("mode", list(OptimizationMode))
def test_python_main_csv_engine_report_subprocess(tmp_path, mode):
    """Run the literal script; sitecustomize only supplies offline typed config."""
    repo = Path(__file__).resolve().parents[2]
    source = tmp_path / "stats.csv"
    source.write_text(
        "Nick,SteamID,ELO,KD,Seed\n"
        "A,S1,1600,1.0,1\nB,S2,1500,0.9,1\n"
        "C,S3,1400,1.1,\nD,S4,1300,0.8,\n", encoding="utf-8"
    )
    destination = tmp_path / "report.html"
    (tmp_path / "sitecustomize.py").write_text(
        "from dataclasses import replace\n"
        "from pathlib import Path\n"
        "from tests.acceptance.test_v08_engine_contracts import acceptance_config\n"
        "from configuration.application_config import ApplicationConfig\n"
        "from optimizer.modes.optimization_mode import OptimizationMode\n"
        f"config = acceptance_config(OptimizationMode({mode.value!r}))\n"
        f"config = replace(config, paths=replace(config.paths, generated_stats=Path({str(source)!r}), output_report=Path({str(destination)!r})))\n"
        "ApplicationConfig.production_defaults = classmethod(lambda cls: config)\n",
        encoding="utf-8",
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tmp_path), str(repo)]),
               PYTHONIOENCODING="utf-8")
    completed = subprocess.run(
        [sys.executable, str(repo / "main.py")], cwd=repo, env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not completed.stderr
    assert mode.value.upper() in completed.stdout
    html = destination.read_text(encoding="utf-8")
    assert '<!DOCTYPE html>' in html
    assert 'data-report-mode="optimized"' in html
