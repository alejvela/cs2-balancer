"""Executable no-incumbent proof migration example; no network or file writes."""

from dataclasses import replace

from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from configuration.application_config import ApplicationConfig
from models.player import Player
from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.modes.optimization_mode import OptimizationMode


def run_example():
    config = ApplicationConfig.production_defaults()
    config = replace(
        config,
        event=replace(config.event, number_of_teams=2, team_size=2),
        global_search=replace(GlobalOptimizationConfig.proof(), use_incumbent=False),
    )
    players = [
        Player(nick=f"P{i}", steam_id=f"S{i}", elo=1300 + 100 * i, kd=1.0)
        for i in range(4)
    ]
    return BalancingApplication(config).run(
        BalancingRequest(players, 2, OptimizationMode.GLOBAL)
    )


if __name__ == "__main__":
    result = run_example()
    assert result.initial_score is None and result.improvement is None
    assert result.search_exhausted and result.optimality_proven
    print(result.final_score, result.stop_reason)
