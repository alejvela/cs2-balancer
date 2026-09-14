"""Production values and safe reuse of application configuration."""

from dataclasses import FrozenInstanceError, asdict, fields, replace
from pathlib import Path

import pytest

import main
from configuration.application_config import (
    ApplicationConfig,
    EventConfig,
    FaceitConfig,
    ObjectiveConfig,
    PhaseConfig,
    PipelineConfig,
    RestartConfig,
    ScoringComponentConfig,
    ScoringConfig,
)
from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.modes.optimization_mode import OptimizationMode
from optimizer.modes.stable_optimization_config import StableOptimizationConfig


def test_production_event_paths_and_faceit():
    config = ApplicationConfig.production_defaults()
    assert asdict(config.event) == {
        "number_of_teams": 4,
        "team_size": 5,
        "name": "LAN CS2",
        "report_title": "LAN CS2 — Análisis de equipos",
        "team_name_prefix": "Equipo",
        "preassigned_title": "Evaluación de equipos predeterminados",
        "require_all_teams": True,
        "importer_strict": True,
    }
    assert config.event.expected_player_count == 20
    assert asdict(config.paths) == {
        "source_players": Path("data/players.csv"),
        "generated_stats": Path("data/players_stats.csv"),
        "faceit_errors": Path("data/faceit_errors.csv"),
        "output_report": Path("output/lan_report.html"),
    }
    assert asdict(config.faceit) == {
        "run_import": True,
        "preferred_game_id": "cs2",
        "fallback_game_ids": ("csgo",),
        "recent_matches": 30,
        "strict": False,
        "delay_seconds": 0.25,
        "timeout_seconds": 20.0,
        "retries": 3,
        "retry_delay_seconds": 1.0,
    }
    assert config.optimization_mode is OptimizationMode.GLOBAL
    assert (config.debug_players, config.debug_final_teams) == (False, True)


def test_scoring_defaults_are_declarative():
    config = ScoringConfig()
    assert [
        (c.name, c.attribute, c.weight, c.midpoint, c.steepness, c.default_score)
        for c in config.components
    ] == [
        ("ELO", "elo", 40, 1800, -0.003, 0),
        ("KD", "kd", 25, 1, -8, 0),
        ("ADR", "adr", 15, 75, -0.10, 0),
        ("KPR", "kpr", 10, 0.70, -12, 0),
        ("Winrate", "winrate", 7, 50, -0.12, 0),
        ("HS", "hs", 3, 45, -0.08, 0),
    ]
    assert (config.minimum_available_weight, config.default_power) == (40, 0)
    assert config.activity_factor == "engine_defaults"


def test_objective_and_restart_defaults():
    assert asdict(ObjectiveConfig()) == {
        "power_weight": 55,
        "elo_balance_weight": 10,
        "elo_spread_weight": 5,
        "kd_weight": 20,
        "team_size_weight": 9,
        "seed_weight": 1,
        "elo_midpoint": 120,
        "elo_steepness": 0.025,
        "ideal_spread": 100,
        "good_spread": 150,
        "acceptable_spread": 200,
        "poor_spread": 300,
        "maximum_spread": 400,
        "kd_max_deviation": 0.35,
        "penalty_per_position": 25,
        "seed_level": 1,
        "maximum_per_team": 1,
        "penalty_per_excess_player": 100,
        "maximum_penalty": 100,
    }
    assert asdict(RestartConfig()) == {
        "separated_seed_level": 1,
        "maximum_seeded_players_per_team": 1,
        "minimum_swaps": 1,
        "maximum_swaps": 6,
        "partial_redistribution_ratio": 0.50,
    }


def test_pipeline_defaults():
    assert [asdict(p) for p in PipelineConfig().phases] == [
        dict(
            name=name,
            strategy=strategy,
            max_iterations=iterations,
            neighborhood="swap",
            minimum_improvement=0.01,
            enabled=True,
            stop_when_no_move=True,
        )
        for name, strategy, iterations in (
            ("Quick Swap Improvement", "first_improvement", 100),
            ("Final Swap Polish", "exhaustive", 30),
        )
    ]


def test_engine_configs_are_reused_and_aliases_preserve_identity():
    config = main.APPLICATION_CONFIG
    assert isinstance(config.stable, StableOptimizationConfig)
    assert isinstance(config.global_search, GlobalOptimizationConfig)
    assert main.STABLE_OPTIMIZATION_CONFIG is config.stable
    assert main.GLOBAL_OPTIMIZATION_CONFIG is config.global_search
    assert ApplicationConfig.production_defaults() == config
    # Full engine values are independently frozen by SCRUM-37 acceptance tests.


def test_every_nested_value_object_is_frozen_and_slotted():
    config = ApplicationConfig.production_defaults()
    objects = [
        config,
        config.event,
        config.paths,
        config.faceit,
        config.scoring,
        *config.scoring.components,
        config.objective,
        config.pipeline,
        *config.pipeline.phases,
        config.restart,
        config.stable,
        config.global_search,
    ]
    for obj in objects:
        assert not hasattr(obj, "__dict__")
        name = fields(obj)[0].name
        with pytest.raises(FrozenInstanceError):
            setattr(obj, name, getattr(obj, name))


def test_defaults_and_composition_do_not_share_mutable_state():
    first = ApplicationConfig.production_defaults()
    second = ApplicationConfig.production_defaults()
    assert first == second
    assert first.scoring is not second.scoring
    assert first.scoring.components is not second.scoring.components
    assert first.pipeline.phases is not second.pipeline.phases
    assert first.stable is not second.stable
    assert first.global_search is not second.global_search
    pipeline1, pipeline2 = main.create_pipeline(), main.create_pipeline()
    assert pipeline1.phases[0].strategy is not pipeline2.phases[0].strategy
    assert pipeline1.phases[0].neighborhood is not pipeline2.phases[0].neighborhood
    assert (
        main.create_scoring_model().activity_factor_model
        is not main.create_scoring_model().activity_factor_model
    )
    assert main.APPLICATION_CONFIG == first


def test_sequences_are_copied_to_tuples():
    games = ["csgo"]
    components = list(ScoringConfig().components)
    phases = list(PipelineConfig().phases)
    faceit = FaceitConfig(fallback_game_ids=games)
    scoring = ScoringConfig(components=components)
    pipeline = PipelineConfig(phases=phases)
    games.clear()
    components.clear()
    phases.clear()
    assert faceit.fallback_game_ids == ("csgo",)
    assert isinstance(scoring.components, tuple) and len(scoring.components) == 6
    assert isinstance(pipeline.phases, tuple) and len(pipeline.phases) == 2


def test_expected_player_count_is_derived_after_replace():
    event = EventConfig()
    changed = replace(event, number_of_teams=3, team_size=2)
    assert changed.expected_player_count == 6
    assert event.expected_player_count == 20


@pytest.mark.parametrize("field", ["number_of_teams", "team_size"])
@pytest.mark.parametrize("value", [0, -1])
def test_invalid_event_dimensions(field, value):
    with pytest.raises(ValueError):
        EventConfig(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "recent_matches",
        "retries",
        "delay_seconds",
        "timeout_seconds",
        "retry_delay_seconds",
    ],
)
def test_negative_faceit_limits(field):
    with pytest.raises(ValueError):
        FaceitConfig(**{field: -1})


@pytest.mark.parametrize(
    "field",
    [
        "power_weight",
        "elo_balance_weight",
        "elo_spread_weight",
        "kd_weight",
        "team_size_weight",
        "seed_weight",
    ],
)
def test_negative_objective_weights(field):
    with pytest.raises(ValueError):
        ObjectiveConfig(**{field: -1})


def test_invalid_scoring_configuration():
    with pytest.raises(ValueError, match="weight"):
        ScoringComponentConfig("ELO", "elo", -1, 1800, -0.003)
    component = ScoringConfig().components[0]
    with pytest.raises(ValueError, match="unique"):
        ScoringConfig(components=(component, component))
    with pytest.raises(ValueError, match="activity"):
        ScoringConfig(activity_factor="unknown")


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_iterations": 0},
        {"strategy": "unknown"},
        {"neighborhood": "unknown"},
    ],
)
def test_invalid_phase(overrides):
    with pytest.raises(ValueError):
        replace(PipelineConfig().phases[0], **overrides)


def test_invalid_pipeline():
    with pytest.raises(ValueError, match="empty"):
        PipelineConfig(phases=())
    phase = PipelineConfig().phases[0]
    with pytest.raises(ValueError, match="unique"):
        PipelineConfig(phases=(phase, phase))


@pytest.mark.parametrize(
    "overrides",
    [
        {"minimum_swaps": -1},
        {"maximum_swaps": -1},
        {"minimum_swaps": 7},
        {"partial_redistribution_ratio": -0.1},
        {"partial_redistribution_ratio": 1.1},
    ],
)
def test_invalid_restart(overrides):
    with pytest.raises(ValueError):
        RestartConfig(**overrides)


def test_compatibility_boundaries_are_not_hardened():
    assert FaceitConfig(retries=0, delay_seconds=0).retries == 0
    assert (
        RestartConfig(
            minimum_swaps=0, maximum_swaps=0, partial_redistribution_ratio=0
        ).minimum_swaps
        == 0
    )
    assert (
        RestartConfig(partial_redistribution_ratio=1).partial_redistribution_ratio == 1
    )
    assert ObjectiveConfig(power_weight=0).power_weight == 0
    assert ScoringComponentConfig("x", "elo", 0, 0, 0).weight == 0
    assert PhaseConfig("disabled", "exhaustive", 1, enabled=False).enabled is False
    config = ApplicationConfig(
        global_search=GlobalOptimizationConfig(
            maximum_nodes=None,
            maximum_evaluations=None,
            maximum_elapsed_seconds=None,
        )
    )
    assert config.global_search.unlimited
