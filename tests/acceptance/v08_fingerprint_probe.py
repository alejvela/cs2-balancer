"""Run with an explicit checkout path, including an extracted v0.7.0 archive.

python tests/acceptance/v08_fingerprint_probe.py CHECKOUT OUTPUT.json
This reads the checkout; it never rewrites a baseline fixture.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path


def snapshot():
    from application.balancing_application import BalancingApplication
    from application.balancing_request import BalancingRequest
    from configuration.application_config import ApplicationConfig
    from configuration.scoring_factory import create_scoring_model
    from optimizer.modes.optimization_mode import OptimizationMode
    from tests.acceptance.test_application_behavior_contract import contract_config
    from tests.acceptance.test_engine_acceptance import (
        canonical_membership,
        synthetic_players,
    )

    config = ApplicationConfig.production_defaults()
    scoring = create_scoring_model(config.scoring)
    data = {
        "production_config": asdict(config),
        "powers": [scoring.power(p) for p in synthetic_players()],
        "modes": {},
    }
    for mode in OptimizationMode:
        result = BalancingApplication(contract_config(mode)).run(
            BalancingRequest(synthetic_players(), 4, mode)
        )
        row = {
            "teams": canonical_membership(result.teams),
            "initial_score": result.initial_score,
            "final_score": result.final_score,
            "penalty": result.penalty,
            "components": {
                name: {key: getattr(r, key) for key in ("score", "weight", "penalty")}
                for name, r in result.restrictions.items()
            },
            "evaluations": result.total_evaluations,
        }
        if mode is OptimizationMode.GLOBAL:
            row.update({key: getattr(result, key) for key in (
                "nodes_visited", "complete_solutions_evaluated", "pruned_nodes",
                "capacity_prunes", "seed_prunes", "bound_prunes", "stop_reason",
                "optimality_proven",
            )})
        data["modes"][mode.value] = row
    return data


if __name__ == "__main__":
    sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
    Path(sys.argv[2]).write_text(
        json.dumps(snapshot(), indent=2, default=str, sort_keys=True) + "\n",
        encoding="utf-8",
    )
