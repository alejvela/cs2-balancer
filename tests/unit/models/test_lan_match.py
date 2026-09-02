import csv
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from importers.lan_match_csv import (
    REQUIRED_COLUMNS,
    SUPPORTED_COLUMNS,
    LanMatchCsvError,
    parse_player_map_row,
    validate_columns,
)
from models.lan_match import BestOf, PlayedMap, PlayedSeries, Tournament


def valid_row(**overrides: str | None) -> dict[str, str | None]:
    row = {column: "0" for column in SUPPORTED_COLUMNS}
    row.update(
        matchid="match-42",
        mapnumber="1",
        steamid64="76561198000000001",
        team="CT",
        name="old_nick",
    )
    row.update(overrides)
    return row


def played_map(series_id: str, mapnumber: int = 1) -> PlayedMap:
    performance = parse_player_map_row(valid_row(mapnumber=str(mapnumber)))
    return PlayedMap(
        series_id=series_id,
        matchid=performance.matchid,
        mapnumber=mapnumber,
        performances=(performance,),
        source=Path(f"{series_id}/map-{mapnumber}.csv"),
    )


def test_supported_schema_is_the_exact_36_column_contract() -> None:
    assert len(SUPPORTED_COLUMNS) == 36
    assert REQUIRED_COLUMNS == frozenset(SUPPORTED_COLUMNS)
    validate_columns(SUPPORTED_COLUMNS)


def test_missing_required_column_is_rejected() -> None:
    row = valid_row()
    del row["kills"]
    with pytest.raises(LanMatchCsvError, match="missing required columns: kills"):
        parse_player_map_row(row)


@pytest.mark.parametrize("value", ["bad", "1.5", "-1"])
def test_malformed_numeric_values_are_rejected(value: str) -> None:
    with pytest.raises(LanMatchCsvError, match="kills must be a non-negative integer"):
        parse_player_map_row(valid_row(kills=value))


def test_steamid64_is_canonical_identity() -> None:
    performance = parse_player_map_row(valid_row())
    assert performance.player_id == "76561198000000001"


def test_nickname_change_does_not_change_identity() -> None:
    old = parse_player_map_row(valid_row(name="old_nick"))
    new = parse_player_map_row(valid_row(name="new_nick"))
    assert old.player_id == new.player_id
    assert old.name != new.name


def test_zero_is_valid_but_blank_is_not_coerced_to_zero() -> None:
    assert parse_player_map_row(valid_row(kills="0")).kills == 0
    with pytest.raises(LanMatchCsvError, match="kills is required"):
        parse_player_map_row(valid_row(kills=""))
    with pytest.raises(LanMatchCsvError, match="kills is required"):
        parse_player_map_row(valid_row(kills=None))


def test_raw_representation_preserves_every_csv_statistic_and_is_immutable() -> None:
    row = valid_row(**{column: str(index) for index, column in enumerate(SUPPORTED_COLUMNS[5:], 1)})
    performance = parse_player_map_row(row)
    assert performance.as_dict() == {
        column: (row[column].strip() if column in {"matchid", "steamid64", "team", "name"} else int(row[column]))
        for column in SUPPORTED_COLUMNS
    }
    with pytest.raises(FrozenInstanceError):
        performance.kills = 99  # type: ignore[misc]


@pytest.mark.parametrize("best_of,map_count", [(BestOf.BO1, 1), (BestOf.BO3, 3), (BestOf.BO5, 5)])
def test_series_represent_bo1_bo3_and_bo5(best_of: BestOf, map_count: int) -> None:
    series = PlayedSeries(
        series_id="folder-a",
        best_of=best_of,
        maps=tuple(played_map("folder-a", number) for number in range(1, map_count + 1)),
    )
    assert len(series.maps) == map_count


def test_folder_is_the_series_boundary_even_when_matchids_are_equal() -> None:
    first = played_map("folder-a")
    second = played_map("folder-b")
    assert first.matchid == second.matchid
    assert first.series_id != second.series_id


def test_maps_from_different_folders_cannot_be_combined() -> None:
    with pytest.raises(ValueError, match="different series folders"):
        PlayedSeries(
            series_id="folder-a",
            best_of=BestOf.BO3,
            maps=(played_map("folder-a", 1), played_map("folder-b", 2)),
        )


def test_maps_are_ordered_by_mapnumber() -> None:
    series = PlayedSeries(
        series_id="folder-a",
        best_of=BestOf.BO3,
        maps=(played_map("folder-a", 3), played_map("folder-a", 1), played_map("folder-a", 2)),
    )
    assert [item.mapnumber for item in series.maps] == [1, 2, 3]


def test_unknown_extra_column_is_rejected() -> None:
    with pytest.raises(LanMatchCsvError, match="unknown columns"):
        parse_player_map_row(valid_row(future_metric="1"))


def test_tournament_is_only_a_container_boundary() -> None:
    series = PlayedSeries("folder-a", BestOf.BO1, (played_map("folder-a"),))
    tournament = Tournament("lan-2026", (series,), display_name="LAN 2026")
    assert tournament.series == (series,)


def test_real_sample_matches_schema_and_parses_losslessly() -> None:
    fixture = Path(__file__).parents[2] / "fixtures" / "match_data_map0_1.csv"
    with fixture.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        assert tuple(reader.fieldnames or ()) == SUPPORTED_COLUMNS
        source_rows = list(reader)

    records = [parse_player_map_row(row) for row in source_rows]

    assert len(records) == 10
    assert all(tuple(record.as_dict()) == SUPPORTED_COLUMNS for record in records)
    assert [record.as_dict() for record in records] == [
        {
            column: (
                value.strip()
                if column in {"matchid", "steamid64", "team", "name"}
                else int(value)
            )
            for column, value in row.items()
        }
        for row in source_rows
    ]
