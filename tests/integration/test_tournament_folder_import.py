import csv
import shutil
from pathlib import Path

import pytest

from importers.lan_match_csv import SUPPORTED_COLUMNS
from importers.tournament_folder import TournamentFolderError, import_tournament_folder
from models.lan_match import BestOf


def write_map(
    path: Path,
    *,
    matchid: str = "match-1",
    mapnumber: int = 0,
    row_overrides: dict[int, dict[str, str]] | None = None,
    columns: tuple[str, ...] = SUPPORTED_COLUMNS,
    encoding: str = "utf-8",
    lineterminator: str = "\r\n",
    quoting: int = csv.QUOTE_MINIMAL,
    row_order: tuple[int, ...] = tuple(range(10)),
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    overrides = row_overrides or {}
    with path.open("w", encoding=encoding, newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=columns,
            lineterminator=lineterminator,
            quoting=quoting,
        )
        writer.writeheader()
        for index in row_order:
            row = {column: "0" for column in SUPPORTED_COLUMNS}
            row.update(
                matchid=matchid,
                mapnumber=str(mapnumber),
                steamid64=f"7656119800000000{index}",
                team="team-a" if index < 5 else "team-b",
                name=f"player-{index}",
            )
            row.update(overrides.get(index, {}))
            writer.writerow({column: row.get(column, "extra") for column in columns})


def scan(root: Path, **metadata: BestOf):
    return import_tournament_folder(root, best_of_by_series=metadata)


def test_invalid_root_is_the_only_folder_level_failure(tmp_path: Path) -> None:
    with pytest.raises(TournamentFolderError, match="does not exist"):
        scan(tmp_path / "missing")
    file_root = tmp_path / "file"
    file_root.write_text("x", encoding="utf-8")
    with pytest.raises(TournamentFolderError, match="not a directory"):
        scan(file_root)


def test_real_fixture_imports_one_map_with_ten_players(tmp_path: Path) -> None:
    folder = tmp_path / "series-a"
    folder.mkdir()
    fixture = Path(__file__).parents[1] / "fixtures" / "match_data_map0_1.csv"
    shutil.copyfile(fixture, folder / "map.csv")

    result = scan(tmp_path, **{"series-a": BestOf.BO1})

    assert len(result.series) == 1
    assert len(result.maps) == 1
    assert len(result.maps[0].performances) == 10


def test_folders_are_series_boundaries_and_maps_are_ordered(tmp_path: Path) -> None:
    write_map(tmp_path / "z-series" / "map-2.csv", mapnumber=2)
    write_map(tmp_path / "a-series" / "map-1.csv", mapnumber=1)
    write_map(tmp_path / "a-series" / "map-0.csv", mapnumber=0)

    result = scan(tmp_path, **{"a-series": BestOf.BO3, "z-series": BestOf.BO1})

    assert [item.series_id for item in result.series] == ["a-series", "z-series"]
    assert [item.mapnumber for item in result.series[0].maps] == [0, 1]
    assert result.series[0].maps[0].matchid == result.series[1].maps[0].matchid


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({1: {"steamid64": "76561198000000000"}}, "duplicate steamid64"),
        ({1: {"matchid": "other"}}, "same matchid"),
        ({1: {"mapnumber": "2"}}, "same mapnumber"),
    ],
)
def test_map_consistency_errors_are_reported(
    tmp_path: Path, overrides: dict[int, dict[str, str]], message: str
) -> None:
    write_map(tmp_path / "series" / "bad.csv", row_overrides=overrides)
    result = scan(tmp_path, series=BestOf.BO1)
    assert not result.maps
    assert message in result.invalid_files[0].message


def test_empty_csv_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "series" / "empty.csv"
    path.parent.mkdir()
    path.write_text(",".join(SUPPORTED_COLUMNS) + "\n", encoding="utf-8")
    result = scan(tmp_path, series=BestOf.BO1)
    assert "at least one player row" in result.invalid_files[0].message


@pytest.mark.parametrize(
    ("columns", "overrides", "message"),
    [
        (SUPPORTED_COLUMNS[:-1], {}, "missing required columns"),
        ((*SUPPORTED_COLUMNS, "future"), {}, "unknown columns"),
        (SUPPORTED_COLUMNS, {0: {"kills": "bad"}}, "non-negative integer"),
    ],
)
def test_scrum_18_schema_errors_are_structured(
    tmp_path: Path,
    columns: tuple[str, ...],
    overrides: dict[int, dict[str, str]],
    message: str,
) -> None:
    write_map(tmp_path / "series" / "bad.csv", columns=columns, row_overrides=overrides)
    result = scan(tmp_path, series=BestOf.BO1)
    assert message in result.invalid_files[0].message


def test_exact_content_duplicates_are_global_and_first_sorted_path_wins(
    tmp_path: Path,
) -> None:
    write_map(tmp_path / "a-series" / "z.csv")
    (tmp_path / "a-series" / "a.txt").write_text("ignored", encoding="utf-8")
    shutil.copyfile(tmp_path / "a-series" / "z.csv", tmp_path / "a-series" / "copy.csv")
    (tmp_path / "b-series").mkdir()
    shutil.copyfile(tmp_path / "a-series" / "z.csv", tmp_path / "b-series" / "map.csv")

    result = scan(tmp_path, **{"a-series": BestOf.BO1, "b-series": BestOf.BO1})

    assert result.discovered_csv_count == 3
    assert [item.path.name for item in result.imported_files] == ["copy.csv"]
    assert [item.path.name for item in result.skipped_duplicates] == ["z.csv", "map.csv"]
    assert [item.series_id for item in result.series] == ["a-series"]


def test_semantic_duplicates_ignore_csv_serialization_and_row_order(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "series"
    write_map(folder / "a-normal.csv")
    write_map(folder / "b-lf.csv", lineterminator="\n")
    write_map(folder / "c-bom.csv", encoding="utf-8-sig")
    write_map(folder / "d-quoted.csv", quoting=csv.QUOTE_ALL)
    write_map(folder / "e-reversed.csv", row_order=tuple(reversed(range(10))))

    result = scan(tmp_path, series=BestOf.BO1)

    assert [item.path.name for item in result.imported_files] == ["a-normal.csv"]
    assert [item.path.name for item in result.skipped_duplicates] == [
        "b-lf.csv",
        "c-bom.csv",
        "d-quoted.csv",
        "e-reversed.csv",
    ]
    assert len({item.fingerprint for item in result.skipped_duplicates}) == 1


def test_actual_statistical_difference_is_not_normalized_as_duplicate(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "series"
    write_map(folder / "a.csv")
    write_map(folder / "b.csv", row_overrides={0: {"kills": "1"}})

    result = scan(tmp_path, series=BestOf.BO1)

    assert not result.skipped_duplicates
    assert "duplicate mapnumber" in result.invalid_files[0].message


def test_root_csv_nested_directories_and_non_csv_files_are_ignored(tmp_path: Path) -> None:
    write_map(tmp_path / "root.csv")
    write_map(tmp_path / "series" / "nested" / "map.csv")
    (tmp_path / "series" / "notes.txt").write_text("ignored", encoding="utf-8")

    result = scan(tmp_path, series=BestOf.BO1)

    assert result.discovered_csv_count == 0
    assert result.discovered_series_folders == (tmp_path / "series",)
    assert not result.series


def test_duplicate_mapnumber_rejects_later_deterministic_file(tmp_path: Path) -> None:
    write_map(tmp_path / "series" / "a.csv", matchid="first")
    write_map(tmp_path / "series" / "b.csv", matchid="second")
    result = scan(tmp_path, series=BestOf.BO1)
    assert [item.path.name for item in result.imported_files] == ["a.csv"]
    assert result.invalid_files[0].path.name == "b.csv"


def test_missing_best_of_is_reported_without_guessing(tmp_path: Path) -> None:
    write_map(tmp_path / "series" / "map.csv")
    result = scan(tmp_path)
    assert len(result.maps) == 1
    assert not result.series
    assert len(result.imported_series) == 1
    assert result.imported_series[0].series_id == "series"
    assert result.imported_series[0].best_of is None
    assert result.imported_series[0].maps == result.maps
    assert "best_of metadata is required" in result.series_issues[0].message


def test_rescan_turns_unknown_best_of_import_into_played_series(tmp_path: Path) -> None:
    write_map(tmp_path / "series" / "map.csv")

    unknown = scan(tmp_path)
    known = scan(tmp_path, series=BestOf.BO3)

    assert len(unknown.imported_series[0].maps) == 1
    assert unknown.imported_series[0].best_of is None
    assert len(known.imported_series[0].maps) == 1
    assert known.imported_series[0].best_of is BestOf.BO3
    assert known.series[0].maps == known.imported_series[0].maps
    assert len(known.maps) == 1


def test_best_of_metadata_edges_are_explicit_and_keep_valid_maps(tmp_path: Path) -> None:
    for mapnumber in range(4):
        write_map(
            tmp_path / "too-many" / f"map-{mapnumber}.csv",
            mapnumber=mapnumber,
            matchid=f"too-many-{mapnumber}",
        )
    write_map(tmp_path / "partial-bo3" / "map.csv", matchid="partial-3")
    write_map(tmp_path / "partial-bo5" / "map.csv", matchid="partial-5")

    result = import_tournament_folder(
        tmp_path,
        best_of_by_series={
            "too-many": BestOf.BO3,
            "partial-bo3": BestOf.BO3,
            "partial-bo5": BestOf.BO5,
            "unknown": BestOf.BO1,
        },
    )

    assert len(result.maps) == 6
    assert [item.series_id for item in result.series] == ["partial-bo3", "partial-bo5"]
    assert any("BO3 cannot contain 4 maps" in issue.message for issue in result.series_issues)
    assert any("unknown series" in issue.message for issue in result.series_issues)
    assert len(next(item for item in result.imported_series if item.series_id == "too-many").maps) == 4


@pytest.mark.parametrize(
    ("best_of", "map_count", "valid"),
    [
        (BestOf.BO1, 2, False),
        (BestOf.BO3, 4, False),
        (BestOf.BO5, 5, True),
        (BestOf.BO3, 1, True),
        (BestOf.BO5, 1, True),
        (BestOf.BO5, 2, True),
    ],
)
def test_best_of_map_count_contract(
    tmp_path: Path, best_of: BestOf, map_count: int, valid: bool
) -> None:
    for mapnumber in range(map_count):
        write_map(
            tmp_path / "series" / f"map-{mapnumber}.csv",
            mapnumber=mapnumber,
            matchid=f"match-{mapnumber}",
        )
    result = scan(tmp_path, series=best_of)
    assert bool(result.series) is valid
    assert len(result.maps) == map_count
    assert len(result.imported_series[0].maps) == map_count


def test_invalid_best_of_type_is_an_issue_even_for_empty_folder(tmp_path: Path) -> None:
    (tmp_path / "series").mkdir()
    result = import_tournament_folder(
        tmp_path,
        best_of_by_series={"series": 3},
    )
    assert "must be a BestOf value" in result.series_issues[0].message


def test_bad_csv_does_not_remove_good_map(tmp_path: Path) -> None:
    write_map(tmp_path / "series" / "good.csv")
    write_map(
        tmp_path / "series" / "bad.csv",
        mapnumber=1,
        row_overrides={0: {"damage": "bad"}},
    )
    result = scan(tmp_path, series=BestOf.BO3)
    assert [item.path.name for item in result.imported_files] == ["good.csv"]
    assert [item.path.name for item in result.invalid_files] == ["bad.csv"]
    assert len(result.series) == 1


def test_rescans_discover_new_series_and_new_map_without_hidden_state(tmp_path: Path) -> None:
    write_map(tmp_path / "series-a" / "map-0.csv")
    first = scan(tmp_path, **{"series-a": BestOf.BO3})
    assert len(first.maps) == 1

    write_map(tmp_path / "series-b" / "map-0.csv", matchid="match-b")
    second = scan(tmp_path, **{"series-a": BestOf.BO3, "series-b": BestOf.BO1})
    assert len(second.maps) == 2

    write_map(tmp_path / "series-a" / "map-1.csv", mapnumber=1, matchid="match-a")
    third = scan(tmp_path, **{"series-a": BestOf.BO3, "series-b": BestOf.BO1})
    assert len(third.maps) == 3
    assert [item.mapnumber for item in third.series[0].maps] == [0, 1]
