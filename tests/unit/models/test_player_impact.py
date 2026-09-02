import csv
import math
from dataclasses import fields
from pathlib import Path

import pytest

from application.player_impact import (
    IMPACT_COMPONENTS,
    IMPACT_WEIGHTS,
    LAN_IMPACT_VERSION,
    bounded_positive_score,
    calculate_clutch_component,
    calculate_combat_component,
    calculate_multikill_component,
    calculate_opening_component,
    calculate_player_impact,
    calculate_teamplay_component,
    calculate_utility_flash_component,
    impact_tie_break_key,
    tournament_impact_eligibility,
)
from application.statistics_aggregation import aggregate_map
from importers.lan_match_csv import parse_player_map_row
from models.lan_match import PlayedMap
from models.player_impact import ImpactComponentResult, ImpactEvidence
from models.statistics import PlayerRawTotals, PlayerStatistics


def statistics(
    player_id: str = "1",
    *,
    display_name: str = "player",
    aliases: tuple[str, ...] = ("player",),
    teams: tuple[str, ...] = ("team-a",),
    maps_played: int = 1,
    series_played: int = 1,
    **values: int,
) -> PlayerStatistics:
    raw_values = {field.name: 0 for field in fields(PlayerRawTotals)}
    raw_values.update(values)
    return PlayerStatistics(
        player_id,
        display_name,
        aliases,
        teams,
        maps_played,
        series_played,
        PlayerRawTotals(**raw_values),
    )


ARCHETYPES = {
    "FRAGGER": statistics(
        kills=24, deaths=14, damage=2200, assists=3, enemy2ks=3, enemy3ks=1
    ),
    "ENTRY": statistics(
        kills=17, deaths=16, damage=1750, assists=4, entry_count=9, entry_wins=6
    ),
    "SUPPORT": statistics(
        kills=14,
        deaths=15,
        damage=1450,
        assists=12,
        utility_count=14,
        utility_damage=260,
        utility_successes=8,
        flash_count=16,
        flash_successes=11,
        enemies_flashed=20,
        entry_count=2,
        entry_wins=1,
    ),
    "CLUTCH": statistics(
        kills=15,
        deaths=14,
        damage=1550,
        assists=4,
        v1_count=4,
        v1_wins=3,
        v2_count=3,
        v2_wins=2,
    ),
    "BALANCED": statistics(
        kills=18,
        deaths=14,
        damage=1850,
        assists=7,
        enemy2ks=2,
        enemy3ks=1,
        entry_count=5,
        entry_wins=3,
        v1_count=2,
        v1_wins=1,
        utility_count=10,
        utility_damage=150,
        utility_successes=5,
        flash_count=10,
        flash_successes=6,
        enemies_flashed=12,
    ),
    "PASSIVE": statistics(kills=3, deaths=5, damage=350, assists=1),
    "SMALL_SAMPLE_STAR": statistics(
        kills=30,
        deaths=8,
        damage=2800,
        assists=8,
        enemy3ks=3,
        entry_count=7,
        entry_wins=6,
        v1_count=2,
        v1_wins=2,
        utility_count=8,
        utility_damage=180,
        utility_successes=6,
        flash_count=8,
        flash_successes=6,
        enemies_flashed=10,
    ),
    "ZERO_OPPORTUNITY": statistics(kills=10, deaths=10, damage=1000, assists=2),
}


def component(result, component_id: str) -> ImpactComponentResult:
    return next(item for item in result.components if item.component_id == component_id)


def test_weights_are_canonical_validated_and_sum_to_one() -> None:
    assert tuple(IMPACT_WEIGHTS) == tuple(item.component_id for item in IMPACT_COMPONENTS)
    assert sum(IMPACT_WEIGHTS.values()) == pytest.approx(1.0)
    assert IMPACT_WEIGHTS == {
        "combat": 0.40,
        "opening": 0.15,
        "multikill": 0.10,
        "supported_clutch": 0.15,
        "teamplay": 0.10,
        "utility_flash": 0.10,
    }
    with pytest.raises(TypeError):
        IMPACT_WEIGHTS["combat"] = 1.0  # type: ignore[index]


def test_bounded_positive_score_is_smooth_bounded_and_monotonic() -> None:
    values = [bounded_positive_score(value, 10.0) for value in (0, 1, 10, 100, 1_000_000)]
    assert values == sorted(values)
    assert values[0] == 0.0
    assert values[2] == pytest.approx(100 * (1 - math.exp(-1)))
    assert all(0.0 <= value <= 100.0 and math.isfinite(value) for value in values)


def test_component_contributions_reconcile_exactly_to_final_score() -> None:
    result = calculate_player_impact(ARCHETYPES["BALANCED"])
    assert result.model_version == LAN_IMPACT_VERSION == "1.0"
    assert result.score == sum(item.weighted_contribution for item in result.components)
    for item in result.components:
        assert item.weighted_contribution == item.score * item.weight
        assert 0.0 <= item.score <= 100.0
        assert item.evidence


def test_no_component_can_supply_more_than_its_weighted_maximum() -> None:
    extreme = statistics(**{field.name: 10**9 for field in fields(PlayerRawTotals)})
    result = calculate_player_impact(extreme)
    assert result.score <= 100.0
    for item in result.components:
        assert item.weighted_contribution <= item.weight * 100.0
    combat_only = calculate_player_impact(
        statistics(kills=10**9, damage=10**9, deaths=0)
    )
    assert combat_only.score <= 40.0


def test_zero_statistics_and_zero_opportunities_are_finite() -> None:
    result = calculate_player_impact(statistics())
    assert result.score == 0.0
    assert all(item.score == 0.0 for item in result.components)
    assert all(math.isfinite(item.score) for item in result.components)


@pytest.mark.parametrize(
    ("calculator", "base", "improved"),
    [
        (calculate_combat_component, {"damage": 500}, {"damage": 1000}),
        (calculate_combat_component, {"kills": 5}, {"kills": 10}),
        (calculate_opening_component, {"entry_count": 2}, {"entry_count": 2, "entry_wins": 1}),
        (calculate_multikill_component, {"enemy2ks": 1}, {"enemy2ks": 2}),
        (calculate_clutch_component, {"v1_count": 2}, {"v1_count": 2, "v1_wins": 1}),
        (calculate_teamplay_component, {"assists": 2}, {"assists": 4}),
        (
            calculate_utility_flash_component,
            {"utility_count": 2},
            {"utility_count": 2, "utility_damage": 100, "utility_successes": 1},
        ),
    ],
)
def test_components_are_monotonic_for_successful_contribution(
    calculator, base: dict[str, int], improved: dict[str, int]
) -> None:
    assert calculator(statistics(**improved)).score >= calculator(statistics(**base)).score


def test_entry_and_clutch_use_volume_confidence_not_rate_alone() -> None:
    one_entry = calculate_opening_component(statistics(entry_count=1, entry_wins=1))
    repeated_entries = calculate_opening_component(statistics(entry_count=12, entry_wins=8))
    assert repeated_entries.score > one_entry.score
    one_clutch = calculate_clutch_component(statistics(v1_count=1, v1_wins=1))
    repeated_clutches = calculate_clutch_component(statistics(v1_count=7, v1_wins=5))
    assert repeated_clutches.score > one_clutch.score


@pytest.mark.parametrize(
    ("weighted_value", "expected_score"),
    [(7, 75.34030360583935), (12, 90.92820467105875)],
)
def test_frozen_multikill_scale_has_approved_observable_calibration(
    weighted_value: int, expected_score: float
) -> None:
    result = calculate_multikill_component(
        statistics(enemy2ks=weighted_value)
    )
    assert result.score == pytest.approx(expected_score)


def test_synthetic_archetypes_are_finite_bounded_and_broad() -> None:
    results = {name: calculate_player_impact(stats) for name, stats in ARCHETYPES.items()}
    assert all(0.0 <= result.score <= 100.0 for result in results.values())
    assert results["BALANCED"].score > results["PASSIVE"].score
    assert results["FRAGGER"].score > results["PASSIVE"].score
    assert results["SUPPORT"].score > results["FRAGGER"].score
    assert component(results["ENTRY"], "opening").score > component(results["FRAGGER"], "opening").score
    assert component(results["CLUTCH"], "supported_clutch").score > component(
        results["FRAGGER"], "supported_clutch"
    ).score


def test_aliases_and_team_strings_do_not_change_numeric_impact() -> None:
    baseline = statistics(kills=12, damage=1200)
    renamed = statistics(
        display_name="renamed",
        aliases=("old", "renamed"),
        teams=("red", "blue"),
        kills=12,
        damage=1200,
    )
    first = calculate_player_impact(baseline)
    second = calculate_player_impact(renamed)
    assert first.score == second.score
    assert first.components == second.components


def test_same_function_handles_map_series_and_tournament_statistics() -> None:
    map_stats = statistics(kills=10, damage=1000, maps_played=1)
    series_stats = statistics(kills=20, damage=2000, maps_played=2)
    tournament_stats = statistics(kills=50, damage=5000, maps_played=5, series_played=2)
    scores = [
        calculate_player_impact(item).score
        for item in (map_stats, series_stats, tournament_stats)
    ]
    assert scores[0] == pytest.approx(scores[1])
    assert scores[1] == pytest.approx(scores[2])


def test_tournament_eligibility_is_separate_from_impact() -> None:
    small_sample = ARCHETYPES["SMALL_SAMPLE_STAR"]
    impact = calculate_player_impact(small_sample)
    eligibility = tournament_impact_eligibility(small_sample, maximum_maps_played=12)
    assert eligibility.required_maps == 6
    assert not eligibility.eligible
    assert calculate_player_impact(small_sample).score == impact.score
    assert tournament_impact_eligibility(statistics(maps_played=6), 12).eligible


def test_future_tie_break_key_matches_documented_evidence_order() -> None:
    stats = statistics(player_id="765", kills=10, damage=1000, entry_wins=2, v1_wins=1)
    impact = calculate_player_impact(stats)
    assert impact_tie_break_key(impact, stats) == (
        -impact.score,
        -1000.0,
        -1,
        -2,
        -10.0,
        "765",
    )


def test_result_validation_rejects_non_reconciling_component() -> None:
    with pytest.raises(ValueError, match=r"score \* weight"):
        ImpactComponentResult("x", "X", 50.0, 0.5, 99.0, (ImpactEvidence("x", 1),))


def test_real_fixture_is_deterministic_bounded_and_explainable() -> None:
    fixture = Path(__file__).parents[2] / "fixtures" / "match_data_map0_1.csv"
    with fixture.open(encoding="utf-8", newline="") as source:
        rows = tuple(parse_player_map_row(row) for row in csv.DictReader(source))
    played_map = PlayedMap("fixture", rows[0].matchid, rows[0].mapnumber, rows)
    players = aggregate_map(played_map).players
    first = tuple(calculate_player_impact(player) for player in players)
    second = tuple(calculate_player_impact(player) for player in players)
    assert len(first) == 10
    assert first == second
    for result in first:
        assert 0.0 <= result.score <= 100.0 and math.isfinite(result.score)
        assert result.score == sum(item.weighted_contribution for item in result.components)
        assert all(math.isfinite(item.score) for item in result.components)
