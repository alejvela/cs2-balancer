import csv
import math
from dataclasses import fields
from pathlib import Path

import pytest

from application.statistics_aggregation import (
    aggregate_map,
    aggregate_series,
    aggregate_tournament,
)
from importers.lan_match_csv import parse_player_map_row
from models.lan_match import BestOf, PlayedMap, PlayedSeries, PlayerMapStatistics
from models.statistics import RAW_ADDITIVE_FIELDS, PlayerRawTotals
from models.tournament_import import (
    ImportedFile,
    ImportedSeries,
    TournamentImportResult,
)


def performance(
    player_id: str = "2",
    *,
    name: str = "player",
    team: str = "team-a",
    matchid: str = "match-0",
    mapnumber: int = 0,
    **overrides: int,
) -> PlayerMapStatistics:
    values = {field: 0 for field in RAW_ADDITIVE_FIELDS}
    values.update(overrides)
    return PlayerMapStatistics(
        matchid=matchid,
        mapnumber=mapnumber,
        steamid64=player_id,
        team=team,
        name=name,
        **values,
    )


def played_map(
    series_id: str,
    mapnumber: int,
    *performances: PlayerMapStatistics,
) -> PlayedMap:
    records = tuple(
        performance(
            item.player_id,
            name=item.name,
            team=item.team,
            matchid=f"{series_id}-{mapnumber}",
            mapnumber=mapnumber,
            **{field: getattr(item, field) for field in RAW_ADDITIVE_FIELDS},
        )
        for item in performances
    )
    return PlayedMap(
        series_id,
        f"{series_id}-{mapnumber}",
        mapnumber,
        records,
        Path(series_id) / f"map-{mapnumber}.csv",
    )


def imported_series(
    series_id: str,
    maps: tuple[PlayedMap, ...],
    best_of: BestOf | None,
) -> ImportedSeries:
    return ImportedSeries(series_id, Path(series_id), maps, best_of)


def import_result(*maps: PlayedMap) -> TournamentImportResult:
    series_ids = sorted({item.series_id for item in maps})
    grouped = tuple(
        imported_series(
            series_id,
            tuple(item for item in maps if item.series_id == series_id),
            None,
        )
        for series_id in series_ids
    )
    return TournamentImportResult(
        root=Path("tournament"),
        discovered_series_folders=tuple(Path(item) for item in series_ids),
        discovered_csv_count=len(maps),
        imported_files=tuple(
            ImportedFile(item.source or Path("map.csv"), str(index), item)
            for index, item in enumerate(maps)
        ),
        skipped_duplicates=(),
        invalid_files=(),
        series_issues=(),
        imported_series=grouped,
        series=(),
    )


def test_one_player_one_map_exposes_raw_and_derived_statistics() -> None:
    source = performance(
        kills=10,
        deaths=4,
        damage=900,
        assists=3,
        head_shot_kills=4,
        shots_fired_total=20,
        shots_on_target_total=8,
        entry_count=4,
        entry_wins=3,
        v1_count=2,
        v1_wins=1,
        v2_count=1,
        v2_wins=1,
        flash_count=5,
        flash_successes=2,
        enemies_flashed=7,
        utility_count=4,
        utility_successes=3,
        utility_damage=100,
        enemy2ks=2,
        enemy3ks=1,
    )
    result = aggregate_map(played_map("series", 0, source))
    player = result.players[0]
    assert (player.maps_played, player.series_played) == (1, 1)
    assert player.raw.kills == 10
    assert player.kd_ratio == 2.5
    assert player.headshot_rate == 0.4
    assert player.accuracy == 0.4
    assert player.entry_success_rate == 0.75
    assert player.supported_clutch_success_rate == pytest.approx(2 / 3)
    assert player.flash_success_rate == 0.4
    assert player.enemies_flashed_per_flash == 1.4
    assert player.utility_success_rate == 0.75
    assert player.utility_damage_per_use == 25.0
    assert player.multikill_events == 3


@pytest.mark.parametrize(
    ("best_of", "map_count"),
    [
        (BestOf.BO1, 1),
        (BestOf.BO3, 1),
        (BestOf.BO3, 3),
        (BestOf.BO5, 2),
        (BestOf.BO5, 5),
        (None, 2),
    ],
)
def test_complete_incomplete_and_unknown_best_of_series_aggregate(
    best_of: BestOf | None, map_count: int
) -> None:
    maps = tuple(
        played_map("series", number, performance(kills=number + 1))
        for number in range(map_count)
    )
    source = (
        imported_series("series", maps, best_of)
        if best_of is None
        else PlayedSeries("series", best_of, maps)
    )
    result = aggregate_series(source)
    assert result.best_of is best_of
    assert result.maps_played == map_count
    assert result.players[0].maps_played == map_count
    assert result.players[0].raw.kills == sum(range(1, map_count + 1))


def test_tournament_identity_alias_team_and_participation_counts() -> None:
    first = played_map(
        "a-series",
        0,
        performance("2", name="old-name", team="red", kills=1),
        performance("1", name="other", team="blue", kills=2),
    )
    second = played_map(
        "a-series",
        1,
        performance("2", name="middle-name", team="green", kills=3),
    )
    third = played_map(
        "b-series",
        0,
        performance("2", name="latest-name", team="red", kills=5),
    )
    result = aggregate_tournament(import_result(third, second, first))
    assert [item.player_id for item in result.players] == ["1", "2"]
    player = result.players[1]
    assert player.raw.kills == 9
    assert player.maps_played == 3
    assert player.series_played == 2
    assert player.display_name == "latest-name"
    assert player.observed_aliases == ("latest-name", "middle-name", "old-name")
    assert player.observed_teams == ("green", "red")
    assert result.series_count == 2
    assert result.map_count == 3


def test_every_raw_field_reconciles_exactly_from_maps() -> None:
    first_values = {name: index + 1 for index, name in enumerate(RAW_ADDITIVE_FIELDS)}
    second_values = {name: (index + 1) * 10 for index, name in enumerate(RAW_ADDITIVE_FIELDS)}
    maps = (
        played_map("series", 0, performance(**first_values)),
        played_map("series", 1, performance(**second_values)),
    )
    total = aggregate_tournament(import_result(*maps)).players[0].raw
    for field in fields(PlayerRawTotals):
        assert getattr(total, field.name) == first_values[field.name] + second_values[field.name]


def test_aggregate_ratios_use_total_numerators_and_denominators() -> None:
    maps = (
        played_map(
            "series",
            0,
            performance(
                kills=1,
                head_shot_kills=1,
                shots_fired_total=1,
                shots_on_target_total=1,
                entry_count=1,
                entry_wins=1,
                v1_count=1,
                v1_wins=1,
                utility_count=1,
                utility_successes=1,
                flash_count=1,
                flash_successes=1,
            ),
        ),
        played_map(
            "series",
            1,
            performance(
                kills=9,
                head_shot_kills=0,
                shots_fired_total=9,
                shots_on_target_total=1,
                entry_count=9,
                entry_wins=1,
                v2_count=9,
                v2_wins=1,
                utility_count=9,
                utility_successes=1,
                flash_count=9,
                flash_successes=1,
            ),
        ),
    )
    player = aggregate_tournament(import_result(*maps)).players[0]
    assert player.headshot_rate == 0.1
    assert player.accuracy == 0.2
    assert player.entry_success_rate == 0.2
    assert player.supported_clutch_success_rate == 0.2
    assert player.utility_success_rate == 0.2
    assert player.flash_success_rate == 0.2


def test_zero_denominators_are_finite_zero_except_zero_death_kd() -> None:
    player = aggregate_map(played_map("series", 0, performance(kills=10))).players[0]
    assert player.kd_ratio == 10.0
    ratios = (
        player.headshot_rate,
        player.accuracy,
        player.entry_success_rate,
        player.v1_clutch_success_rate,
        player.v2_clutch_success_rate,
        player.supported_clutch_success_rate,
        player.flash_success_rate,
        player.enemies_flashed_per_flash,
        player.utility_success_rate,
        player.utility_damage_per_use,
        player.kills_per_map,
        player.deaths_per_map,
        player.damage_per_map,
        player.assists_per_map,
        player.utility_damage_per_map,
        player.enemies_flashed_per_map,
        player.entry_attempts_per_map,
        player.multikill_events_per_map,
    )
    assert ratios[:10] == (0.0,) * 10
    assert all(math.isfinite(value) for value in ratios + (player.kd_ratio,))
    zero_kill_player = aggregate_map(
        played_map("series", 0, performance(kills=0, deaths=2))
    ).players[0]
    assert zero_kill_player.kd_ratio == 0.0
    assert zero_kill_player.headshot_rate == 0.0


def test_dominant_alias_wins_regardless_of_map_input_order() -> None:
    maps = (
        played_map("series", 2, performance(name="SNKR2")),
        played_map("series", 0, performance(name="Snkr")),
        played_map("series", 1, performance(name="Snkr")),
    )
    forward = aggregate_series(imported_series("series", maps, None)).players[0]
    reverse = aggregate_series(imported_series("series", tuple(reversed(maps)), None)).players[0]
    assert forward == reverse
    assert forward.display_name == "Snkr"
    assert forward.observed_aliases == ("Snkr", "SNKR2")


def test_equal_frequency_aliases_use_lexical_tie_break_without_splitting_identity() -> None:
    maps = (
        played_map("series", 1, performance("same-id", name="Zulu")),
        played_map("series", 0, performance("same-id", name="Alpha")),
    )
    player = aggregate_series(imported_series("series", maps, None)).players[0]
    assert player.player_id == "same-id"
    assert player.display_name == "Alpha"
    assert player.observed_aliases == ("Alpha", "Zulu")
    assert len(aggregate_series(imported_series("series", maps, None)).players) == 1


def test_map_and_series_input_order_do_not_change_results() -> None:
    later_map = played_map("series", 1, performance(name="new", kills=2))
    earlier_map = played_map("series", 0, performance(name="old", kills=1))
    assert aggregate_series(
        imported_series("series", (later_map, earlier_map), None)
    ) == aggregate_series(
        imported_series("series", (earlier_map, later_map), None)
    )
    later_series = played_map("b-series", 0, performance(name="new", kills=2))
    earlier_series = played_map("a-series", 0, performance(name="old", kills=1))
    assert aggregate_tournament(
        import_result(later_series, earlier_series)
    ) == aggregate_tournament(
        import_result(earlier_series, later_series)
    )


def test_duplicate_player_in_constructed_map_is_rejected() -> None:
    duplicate = played_map("series", 0, performance("1"), performance("1"))
    with pytest.raises(ValueError, match="duplicate players"):
        aggregate_map(duplicate)


def test_duplicate_accepted_fingerprint_cannot_be_double_counted() -> None:
    source = played_map("series", 0, performance(kills=10))
    result = import_result(source, source)
    duplicate_file = ImportedFile(
        result.imported_files[1].path,
        result.imported_files[0].fingerprint,
        source,
    )
    duplicate_result = TournamentImportResult(
        root=result.root,
        discovered_series_folders=result.discovered_series_folders,
        discovered_csv_count=result.discovered_csv_count,
        imported_files=(result.imported_files[0], duplicate_file),
        skipped_duplicates=(),
        invalid_files=(),
        series_issues=(),
        imported_series=result.imported_series,
        series=(),
    )
    with pytest.raises(ValueError, match="duplicate accepted map fingerprints"):
        aggregate_tournament(duplicate_result)


def test_real_scrum_18_fixture_reconciles_all_raw_totals() -> None:
    fixture = Path(__file__).parents[2] / "fixtures" / "match_data_map0_1.csv"
    with fixture.open(encoding="utf-8", newline="") as source:
        records = tuple(parse_player_map_row(row) for row in csv.DictReader(source))
    result = aggregate_map(
        PlayedMap("fixture-series", records[0].matchid, records[0].mapnumber, records)
    )
    by_player = {item.player_id: item for item in result.players}
    for record in records:
        totals = by_player[record.player_id].raw
        assert all(getattr(totals, field) == getattr(record, field) for field in RAW_ADDITIVE_FIELDS)
