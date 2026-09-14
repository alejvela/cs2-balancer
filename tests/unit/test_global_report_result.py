"""Public GLOBAL report metrics and unchanged BaseReportResult serialization."""

import pytest

import main
from application.results.base_report_result import BaseReportResult
from application.results.global_report_result import GlobalReportResult
from application.results.report_mode import ReportMode
from configuration.composition_root import create_balancing_composition
from optimizer.global_search.global_optimization_result import GlobalOptimizationResult
from tests.unit.test_composition_root import players, small_config


@pytest.mark.parametrize(
    "stop_reason,proven,limited",
    [
        ("NODE_LIMIT", False, True),
        ("SEARCH_EXHAUSTED", True, False),
    ],
)
@pytest.mark.parametrize("metadata", [None, {"caller": "copied"}])
def test_global_report_contract_and_serialization(
    stop_reason, proven, limited, metadata, capsys
):
    metadata = dict(metadata) if metadata is not None else None
    composition = create_balancing_composition(small_config())
    teams = composition.balancer.generator.generate(players(), 2)
    objective = composition.objective_engine.evaluate(teams)
    raw = GlobalOptimizationResult(
        teams=teams,
        score=objective.score,
        initial_incumbent_score=objective.score - 2,
        nodes_visited=23,
        complete_solutions_evaluated=7,
        pruned_nodes=11,
        capacity_prunes=2,
        seed_prunes=3,
        bound_prunes=6,
        elapsed_seconds=1.25,
        optimality_proven=proven,
        stopped_by_limit=limited,
        stop_reason=stop_reason,
    )
    result = GlobalReportResult(
        teams,
        objective,
        raw.initial_incumbent_score,
        raw,
        title="GLOBAL report",
        metadata=metadata,
    )
    assert isinstance(result, BaseReportResult)
    assert main.GlobalReportResult is GlobalReportResult  # Legacy import alias.
    assert result.mode is ReportMode.OPTIMIZED
    assert result.optimized is True and result.evaluation_only is False
    assert (
        result.initial_score
        == result.initial_incumbent_score
        == raw.initial_incumbent_score
    )
    assert result.score == result.final_score == objective.score
    assert result.improvement == 2
    assert result.iterations == 0 and result.history == ()
    assert result.total_evaluations == result.complete_solutions_evaluated == 7
    assert result.elapsed == result.elapsed_seconds == 1.25
    assert result.elapsed_ms == 1250
    assert result.optimization_engine == "GLOBAL"
    assert result.nodes_visited == 23
    assert result.pruned_nodes == 11
    assert (result.capacity_prunes, result.seed_prunes, result.bound_prunes) == (
        2,
        3,
        6,
    )
    assert result.optimality_proven is proven
    assert result.stopped_by_limit is limited
    assert result.global_stop_reason == result.stop_reason == stop_reason
    assert result.search_exhausted is (stop_reason == "SEARCH_EXHAUSTED")
    assert not hasattr(result, "raw_result")
    assert GlobalReportResult.as_dict is BaseReportResult.as_dict
    serialized = result.as_dict()
    assert serialized["mode"] == "optimized"
    assert serialized["total_evaluations"] == 7
    assert serialized["elapsed_ms"] == 1250
    assert serialized["metadata"] == (metadata or {})
    assert "raw_result" not in serialized
    if metadata is not None:
        metadata["outside"] = True
        assert "outside" not in result.metadata
    main.print_global_optimization(result)
    output = capsys.readouterr().out
    assert "OPTIMIZACIÓN GLOBAL" in output
    assert stop_reason in output
    assert "23" in output
