"""Factories honor explicit configuration and own fresh engine instances."""

from dataclasses import replace

import pytest

from configuration.application_config import (
    ObjectiveConfig,
    PhaseConfig,
    PipelineConfig,
    ScoringComponentConfig,
    ScoringConfig,
)
from configuration.objective_factory import create_objective_engine
from configuration.pipeline_factory import create_pipeline
from configuration.scoring_factory import create_scoring_model
from optimizer.activity.activity_factor_model import ActivityFactorModel
from optimizer.neighborhoods.swap_neighborhood import SwapNeighborhood
from optimizer.normalization.logistic_normalizer import LogisticNormalizer
from optimizer.strategies.exhaustive_strategy import ExhaustiveStrategy
from optimizer.strategies.first_improvement_strategy import FirstImprovementStrategy


def test_scoring_factory_defaults_and_instance_isolation():
    config = ScoringConfig()
    first, second = create_scoring_model(config), create_scoring_model(config)
    assert first is not second
    assert isinstance(first.activity_factor_model, ActivityFactorModel)
    assert first.activity_factor_model is not second.activity_factor_model
    assert first.as_dict()["activity_model"] == second.as_dict()["activity_model"]
    assert [c.name for c in first.components] == [
        "ELO",
        "KD",
        "ADR",
        "KPR",
        "Winrate",
        "HS",
    ]
    for declared, a, b in zip(
        config.components, first.components, second.components, strict=True
    ):
        assert a is not b
        assert a.normalizer is not b.normalizer
        assert isinstance(a.normalizer, LogisticNormalizer)
        assert (
            a.attribute,
            a.default_score,
            a.normalizer.midpoint,
            a.normalizer.steepness,
        ) == (
            declared.attribute,
            declared.default_score,
            declared.midpoint,
            declared.steepness,
        )
        assert first.get_weight(a.name) == declared.weight
    assert (first.minimum_available_weight, first.default_power) == (40, 0)


def test_custom_scoring_config_controls_every_component_parameter():
    config = ScoringConfig(
        components=(ScoringComponentConfig("Custom ELO", "elo", 23, 1500, -0.005, 12),),
        minimum_available_weight=5,
        default_power=17,
    )
    scoring = create_scoring_model(config)
    assert len(scoring.components) == 1
    component = scoring.components[0]
    assert (component.name, component.attribute, component.default_score) == (
        "Custom ELO",
        "elo",
        12,
    )
    assert (component.normalizer.midpoint, component.normalizer.steepness) == (
        1500,
        -0.005,
    )
    assert scoring.get_weight("Custom ELO") == 23
    assert (scoring.minimum_available_weight, scoring.default_power) == (5, 17)
    assert create_scoring_model(ScoringConfig()).get_weight("ELO") == 40


def test_custom_objective_config_controls_all_restriction_parameters():
    config = ObjectiveConfig(
        power_weight=41,
        elo_balance_weight=12,
        elo_spread_weight=6,
        kd_weight=22,
        team_size_weight=8,
        seed_weight=2,
        elo_midpoint=110,
        elo_steepness=0.03,
        ideal_spread=90,
        good_spread=140,
        acceptable_spread=190,
        poor_spread=290,
        maximum_spread=390,
        kd_max_deviation=0.5,
        penalty_per_position=15,
        seed_level=2,
        maximum_per_team=2,
        penalty_per_excess_player=40,
        maximum_penalty=80,
    )
    scoring = create_scoring_model(ScoringConfig())
    objective = create_objective_engine(config, scoring, team_size=3)
    assert [type(r).__name__ for r in objective.restrictions] == [
        "PowerBalanceRestriction",
        "EloBalanceRestriction",
        "EloSpreadRestriction",
        "KdBalanceRestriction",
        "TeamSizeRestriction",
        "SeedSeparationRestriction",
    ]
    assert [r.weight for r in objective.restrictions] == [41, 12, 6, 22, 8, 2]
    power, elo, spread, kd, size, seed = objective.restrictions
    assert power.scoring_model is scoring
    assert (elo.midpoint, elo.steepness) == (110, 0.03)
    assert (
        spread.ideal_spread,
        spread.good_spread,
        spread.acceptable_spread,
        spread.poor_spread,
        spread.maximum_spread,
    ) == (90, 140, 190, 290, 390)
    assert kd.max_deviation == 0.5
    assert (size.expected_size, size.penalty_per_position) == (3, 15)
    assert (
        seed.seed_level,
        seed.maximum_per_team,
        seed.penalty_per_excess_player,
        seed.maximum_penalty,
    ) == (2, 2, 40, 80)
    other = create_objective_engine(config, scoring, team_size=3)
    assert other is not objective
    assert all(
        a is not b
        for a, b in zip(objective.restrictions, other.restrictions, strict=True)
    )


def test_pipeline_instances_are_isolated_from_each_other_and_config():
    config = PipelineConfig()
    first, second = create_pipeline(config), create_pipeline(config)
    assert first is not second
    assert [type(p.strategy) for p in first.phases] == [
        FirstImprovementStrategy,
        ExhaustiveStrategy,
    ]
    for declared, a, b in zip(config.phases, first.phases, second.phases, strict=True):
        assert a is not b
        assert a.strategy is not b.strategy
        assert a.neighborhood is not b.neighborhood
        assert isinstance(a.neighborhood, SwapNeighborhood)
        assert (
            a.name,
            a.max_iterations,
            a.enabled,
            a.stop_when_no_move,
            a.strategy.minimum_improvement,
        ) == (
            declared.name,
            declared.max_iterations,
            declared.enabled,
            declared.stop_when_no_move,
            declared.minimum_improvement,
        )
    first.phases[0].enabled = False
    first.phases[0].max_iterations = 1
    assert second.phases[0].enabled is True
    assert second.phases[0].max_iterations == config.phases[0].max_iterations == 100


@pytest.mark.parametrize(
    "strategy,expected",
    [
        ("exhaustive", ExhaustiveStrategy),
        ("first_improvement", FirstImprovementStrategy),
    ],
)
def test_custom_pipeline_config(strategy, expected):
    phase = PhaseConfig(
        "Custom phase",
        strategy,
        2,
        minimum_improvement=0.5,
        enabled=False,
        stop_when_no_move=False,
    )
    pipeline = create_pipeline(PipelineConfig(phases=(phase,)))
    assert len(pipeline.phases) == 1
    built = pipeline.phases[0]
    assert isinstance(built.strategy, expected)
    assert (
        built.name,
        built.max_iterations,
        built.strategy.minimum_improvement,
        built.enabled,
        built.stop_when_no_move,
    ) == ("Custom phase", 2, 0.5, False, False)
    assert replace(phase, enabled=True).enabled
