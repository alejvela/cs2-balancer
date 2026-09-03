import csv
from dataclasses import replace
from pathlib import Path

import pytest

import application.player_rankings as ranking_service
from application.player_impact import LAN_IMPACT_VERSION, calculate_player_impact
from application.player_rankings import rank_map, rank_series, rank_tournament
from application.statistics_aggregation import (
    aggregate_map,
    aggregate_series,
    aggregate_tournament,
)
from importers.lan_match_csv import parse_player_map_row
from models.lan_match import BestOf, PlayedMap, PlayedSeries
from models.player_impact import ImpactComponentResult, PlayerImpactResult
from models.player_ranking import PlayerRanking, RankingScope
from tests.unit.models.test_statistics import (
    import_result,
    imported_series,
    performance,
    played_map,
)


def fake_impact(player_id: str, score: float) -> PlayerImpactResult:
    component = ImpactComponentResult("test", "Test", score, 1.0, score, ())
    return PlayerImpactResult(player_id, player_id, LAN_IMPACT_VERSION, score, (component,))


def test_real_map_ranking_has_ten_unique_deterministic_entries() -> None:
    fixture = Path(__file__).parents[2] / "fixtures" / "match_data_map0_1.csv"
    with fixture.open(encoding="utf-8", newline="") as source:
        rows = tuple(parse_player_map_row(row) for row in csv.DictReader(source))
    forward_map = PlayedMap("series", rows[0].matchid, rows[0].mapnumber, rows)
    reverse_map = PlayedMap("series", rows[0].matchid, rows[0].mapnumber, tuple(reversed(rows)))

    forward = rank_map(forward_map)
    reverse = rank_map(reverse_map)

    assert len(forward.entries) == 10
    assert len({item.player_id for item in forward.entries}) == 10
    assert forward == reverse
    assert [item.rank for item in forward.entries] == list(range(1, 11))
    assert all(item.tournament_eligibility is None for item in forward.entries)
    aggregated = {item.player_id: item for item in aggregate_map(forward_map).players}
    assert all(
        item.impact == calculate_player_impact(aggregated[item.player_id])
        for item in forward.entries
    )


@pytest.mark.parametrize(
    ("first_values", "second_values", "expected_first"),
    [
        ({}, {}, "1"),
        ({"damage": 2}, {"damage": 1}, "1"),
        ({"v1_wins": 2}, {"v1_wins": 1}, "1"),
        ({"entry_wins": 2}, {"entry_wins": 1}, "1"),
        ({"kills": 2}, {"kills": 1}, "1"),
    ],
)
def test_successive_tie_break_dimensions(
    monkeypatch: pytest.MonkeyPatch,
    first_values: dict[str, int],
    second_values: dict[str, int],
    expected_first: str,
) -> None:
    source = played_map(
        "series",
        0,
        performance("2", **second_values),
        performance("1", **first_values),
    )
    monkeypatch.setattr(
        ranking_service,
        "calculate_player_impact",
        lambda stats: fake_impact(stats.player_id, 50.0),
    )
    result = rank_map(source)
    assert result.entries[0].player_id == expected_first


def test_impact_score_is_first_tie_break_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    source = played_map("series", 0, performance("1"), performance("2"))
    monkeypatch.setattr(
        ranking_service,
        "calculate_player_impact",
        lambda stats: fake_impact(stats.player_id, 60.0 if stats.player_id == "2" else 50.0),
    )
    assert rank_map(source).entries[0].player_id == "2"


def test_bo1_series_matches_its_map_aggregate_ranking() -> None:
    source_map = played_map(
        "series", 0, performance("1", kills=5), performance("2", kills=10)
    )
    map_result = rank_map(source_map)
    series_result = rank_series(PlayedSeries("series", BestOf.BO1, (source_map,)))
    assert [item.player_id for item in series_result.entries] == [
        item.player_id for item in map_result.entries
    ]
    assert [item.impact for item in series_result.entries] == [
        item.impact for item in map_result.entries
    ]


def test_bo3_aggregates_before_impact_instead_of_averaging_map_impacts() -> None:
    maps = (
        played_map("series", 0, performance(kills=30, deaths=5, damage=3000)),
        played_map("series", 1, performance(kills=0, deaths=20, damage=0)),
        played_map("series", 2, performance(kills=10, deaths=10, damage=1000)),
    )
    result = rank_series(PlayedSeries("series", BestOf.BO3, maps))
    aggregate_impact = calculate_player_impact(aggregate_series(PlayedSeries("series", BestOf.BO3, maps)).players[0])
    average_map_impact = sum(
        calculate_player_impact(aggregate_map(item).players[0]).score for item in maps
    ) / len(maps)
    assert result.entries[0].impact == aggregate_impact
    assert result.entries[0].impact.score != pytest.approx(average_map_impact)


@pytest.mark.parametrize("map_count", [2, 5])
def test_complete_and_incomplete_bo5_rank_deterministically(map_count: int) -> None:
    maps = tuple(
        played_map(
            "series",
            number,
            performance("2", kills=number + 1),
            performance("1", assists=number + 1),
        )
        for number in range(map_count)
    )
    source = PlayedSeries("series", BestOf.BO5, maps)
    assert rank_series(source) == rank_series(PlayedSeries("series", BestOf.BO5, tuple(reversed(maps))))
    assert len(rank_series(source).entries) == 2


def test_unknown_best_of_and_nickname_changes_produce_one_canonical_player() -> None:
    maps = (
        played_map("series", 0, performance("1", name="Snkr", kills=5)),
        played_map("series", 1, performance("1", name="SNKR2", kills=5)),
        played_map("series", 2, performance("1", name="Snkr", kills=5)),
    )
    result = rank_series(imported_series("series", maps, None))
    assert len(result.entries) == 1
    assert result.entries[0].player_id == "1"
    assert result.entries[0].display_name == "Snkr"
    assert result.entries[0].observed_aliases == ("Snkr", "SNKR2")


def test_tournament_keeps_every_player_and_exposes_separate_eligibility() -> None:
    maps = tuple(
        played_map(
            "series-a",
            number,
            performance("regular", kills=10, deaths=10, damage=1000),
            *(
                (performance("star", kills=30, deaths=2, damage=3000),)
                if number == 0
                else ()
            ),
        )
        for number in range(4)
    )
    result = rank_tournament(import_result(*maps), tournament_id="lan-2026")
    assert {item.player_id for item in result.entries} == {"regular", "star"}
    by_id = {item.player_id: item for item in result.entries}
    assert (by_id["regular"].maps_played, by_id["regular"].series_played) == (4, 1)
    assert (by_id["star"].maps_played, by_id["star"].series_played) == (1, 1)
    assert by_id["star"].rank == 1
    assert not by_id["star"].tournament_eligibility.eligible
    assert by_id["star"].tournament_eligibility.required_maps == 2
    assert by_id["regular"].tournament_eligibility.eligible
    tournament_players = {item.player_id: item for item in aggregate_tournament(import_result(*maps)).players}
    assert all(
        entry.impact == calculate_player_impact(tournament_players[entry.player_id])
        for entry in result.entries
    )


def test_empty_tournament_ranking_is_valid_and_deterministic() -> None:
    result = rank_tournament(import_result(), tournament_id="empty")
    assert result == PlayerRanking(RankingScope.TOURNAMENT, "empty", (), LAN_IMPACT_VERSION)


def test_ranking_result_invariants_reject_external_inconsistency() -> None:
    source = rank_map(played_map("series", 0, performance("1"), performance("2")))
    first, second = source.entries
    with pytest.raises(ValueError, match="contiguous ordinal"):
        PlayerRanking(source.scope, source.context_id, (replace(first, rank=2),), source.model_version)
    with pytest.raises(ValueError, match="unique"):
        PlayerRanking(
            source.scope,
            source.context_id,
            (first, replace(first, rank=2)),
            source.model_version,
        )
    with pytest.raises(ValueError, match="player ids must match"):
        replace(first, player_id="other")
    with pytest.raises(ValueError, match="eligibility is only valid"):
        replace(first, tournament_eligibility=rank_tournament(import_result(), tournament_id="x").entries)
    with pytest.raises(ValueError, match="canonical comparison order"):
        PlayerRanking(
            source.scope,
            source.context_id,
            (replace(second, rank=1), replace(first, rank=2)),
            source.model_version,
        )


def test_tournament_entry_requires_eligibility_and_matching_version() -> None:
    tournament = rank_tournament(
        import_result(played_map("series", 0, performance("1"))),
        tournament_id="lan",
    )
    with pytest.raises(ValueError, match="require eligibility"):
        replace(tournament.entries[0], tournament_eligibility=None)
    with pytest.raises(ValueError, match="model versions must match"):
        replace(tournament, model_version="other")
