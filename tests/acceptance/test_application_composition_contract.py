"""Production composition at v0.6.0; move these assertions with v0.7 factories."""

from dataclasses import asdict

from configuration import (
    composition_root,
    global_factory,
    objective_factory,
    pipeline_factory,
    scoring_factory,
)
from configuration.application_config import ApplicationConfig
from optimizer.activity.activity_factor_model import ActivityFactorModel
from optimizer.modes.optimization_mode import OptimizationMode
from optimizer.normalization.logistic_normalizer import LogisticNormalizer

config = ApplicationConfig.production_defaults()


def test_production_scoring_composition():
    model = scoring_factory.create_scoring_model(config.scoring)
    expected = [
        ("ELO", "elo", 40.0, 1800.0, -0.003),
        ("KD", "kd", 25.0, 1.0, -8.0),
        ("ADR", "adr", 15.0, 75.0, -0.10),
        ("KPR", "kpr", 10.0, 0.70, -12.0),
        ("Winrate", "winrate", 7.0, 50.0, -0.12),
        ("HS", "hs", 3.0, 45.0, -0.08),
    ]
    assert [
        (
            c.name,
            c.attribute,
            model.get_weight(c.name),
            c.normalizer.midpoint,
            c.normalizer.steepness,
        )
        for c in model.components
    ] == expected
    assert all(isinstance(c.normalizer, LogisticNormalizer) for c in model.components)
    assert all(c.default_score == 0.0 for c in model.components)
    assert model.minimum_available_weight == 40.0
    assert model.default_power == 0.0
    assert isinstance(model.activity_factor_model, ActivityFactorModel)
    assert model.activity_factor_model.DEFAULT_UNKNOWN_LEVEL_STRENGTH == 1.0
    assert model.as_dict()["activity_model"] == {
        "type": "ActivityFactorModel",
        "target_0_7": 10,
        "target_8_30": 20,
        "target_31_90": 30,
        "weight_0_7": 0.5,
        "weight_8_30": 0.3,
        "weight_31_90": 0.2,
        "minimum_factor": 0.75,
        "level_penalty_strength": {
            1: 1.18,
            2: 1.16,
            3: 1.14,
            4: 1.10,
            5: 1.05,
            6: 1.0,
            7: 0.94,
            8: 0.88,
            9: 0.84,
            10: 0.80,
        },
    }


def test_production_objective_composition():
    model = scoring_factory.create_scoring_model(config.scoring)
    objective = objective_factory.create_objective_engine(
        config.objective, model, team_size=config.event.team_size
    )
    assert [(type(r).__name__, r.weight) for r in objective.restrictions] == [
        ("PowerBalanceRestriction", 55.0),
        ("EloBalanceRestriction", 10.0),
        ("EloSpreadRestriction", 5.0),
        ("KdBalanceRestriction", 20.0),
        ("TeamSizeRestriction", 9.0),
        ("SeedSeparationRestriction", 1.0),
    ]
    power, elo, spread, kd, size, seed = objective.restrictions
    assert power.scoring_model is model
    assert (elo.midpoint, elo.steepness) == (120.0, 0.025)
    assert (
        spread.ideal_spread,
        spread.good_spread,
        spread.acceptable_spread,
        spread.poor_spread,
        spread.maximum_spread,
    ) == (100, 150, 200, 300, 400)
    assert kd.max_deviation == 0.35
    assert (size.expected_size, size.penalty_per_position) == (5, 25.0)
    assert (
        seed.seed_level,
        seed.maximum_per_team,
        seed.penalty_per_excess_player,
        seed.maximum_penalty,
    ) == (1, 1, 100, 100)


def test_production_pipeline_composition():
    phases = pipeline_factory.create_pipeline(config.pipeline).phases
    assert [
        (
            p.name,
            type(p.neighborhood).__name__,
            type(p.strategy).__name__,
            p.strategy.minimum_improvement,
            p.max_iterations,
            p.enabled,
            p.stop_when_no_move,
        )
        for p in phases
    ] == [
        (
            "Quick Swap Improvement",
            "SwapNeighborhood",
            "FirstImprovementStrategy",
            0.01,
            100,
            True,
            True,
        ),
        (
            "Final Swap Polish",
            "SwapNeighborhood",
            "ExhaustiveStrategy",
            0.01,
            30,
            True,
            True,
        ),
    ]


def test_production_stable_configuration_and_restart_composition():
    assert asdict(config.stable) == {
        "target_score": 100.0,
        "maximum_restarts": 150,
        "minimum_restarts": 30,
        "convergence_patience": 30,
        "score_tolerance": 1e-6,
        "base_seed": 2026,
        "target_confirmation_restarts": 10,
        "minimum_unique_solutions": 20,
        "maximum_total_evaluations": None,
        "maximum_elapsed_seconds": None,
        "stop_on_perfect_score": False,
        "perfect_score": 100.0,
    }
    balancer = composition_root.create_balancer(
        config, scoring_factory.create_scoring_model(config.scoring)
    )
    stable = balancer.stable_optimizer
    assert stable.config is config.stable
    assert stable.selector.config is config.stable
    restart = stable.restart_factory
    assert (
        restart.separated_seed_level,
        restart.maximum_seeded_players_per_team,
        restart.minimum_swaps,
        restart.maximum_swaps,
        restart.partial_redistribution_ratio,
    ) == (1, 1, 1, 6, 0.50)
    assert (
        config.event.number_of_teams,
        config.event.team_size,
        config.event.expected_player_count,
    ) == (
        4,
        5,
        20,
    )
    assert config.optimization_mode is OptimizationMode.GLOBAL
    # GLOBAL is currently orchestrated outside LanBalancer, after this warm start.
    assert balancer.optimization_mode is OptimizationMode.STABLE


def test_production_application_collaborators():
    scoring = scoring_factory.create_scoring_model(config.scoring)
    objective = objective_factory.create_objective_engine(
        config.objective, scoring, team_size=config.event.team_size
    )
    balancer = composition_root.create_balancer(config, scoring, objective)
    assert type(balancer.importer).__name__ == "CssStatsImporter"
    assert balancer.importer.strict is True
    generator = balancer.generator
    assert type(generator).__name__ == "SnakeDraftGenerator"
    assert generator.scoring_model is scoring
    assert (
        generator.team_name_prefix,
        generator.separated_seed_level,
        generator.maximum_seeded_players_per_team,
    ) == ("Equipo", 1, 1)
    preassigned = balancer.preassigned_generator
    assert (
        preassigned.expected_team_size,
        preassigned.expected_player_count,
        preassigned.team_name_prefix,
        preassigned.require_all_teams,
    ) == (5, 20, "Equipo", True)
    assert balancer.preassigned_evaluator.objective_engine is objective
    assert type(balancer.exporter).__name__ == "HtmlExporterV2"


def test_production_global_configuration_and_bound_composition():
    assert asdict(config.global_search) == {
        "maximum_nodes": 500_000,
        "maximum_evaluations": 100_000,
        "maximum_elapsed_seconds": 60.0,
        "score_tolerance": 1e-6,
        "minimum_improvement": 1e-6,
        "use_incumbent": True,
        "use_symmetry_breaking": True,
        "use_seed_pruning": True,
        "use_capacity_pruning": True,
        "use_power_bound": True,
        "use_elo_bound": False,
        "deterministic": True,
        "require_proof": False,
        "base_seed": 2026,
    }
    objective = objective_factory.create_objective_engine(
        config.objective,
        scoring_factory.create_scoring_model(config.scoring),
        team_size=config.event.team_size,
    )
    optimizer = global_factory.create_global_optimizer(config, objective)
    # These constructor parameters have no public accessors in v0.6. This narrow
    # configuration assertion is intentional; search internals are not snapshotted.
    assert optimizer._config is config.global_search
    assert optimizer._objective_engine is objective
    bound = optimizer._bound_calculator
    assert {
        name: getattr(bound, "_" + name)
        for name in (
            "power_weight",
            "elo_balance_weight",
            "elo_spread_weight",
            "kd_weight",
            "team_size_weight",
            "seed_weight",
            "score_tolerance",
        )
    } == {
        "power_weight": 55.0,
        "elo_balance_weight": 10.0,
        "elo_spread_weight": 5.0,
        "kd_weight": 20.0,
        "team_size_weight": 9.0,
        "seed_weight": 1.0,
        "score_tolerance": 1e-6,
    }
