"""Deterministic, partial-success import of a LAN tournament folder."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from importers.lan_match_csv import (
    SUPPORTED_COLUMNS,
    LanMatchCsvError,
    parse_lan_match_csv,
)
from models.lan_match import BestOf, PlayedMap, PlayedSeries
from models.tournament_import import (
    ImportedFile,
    ImportedSeries,
    ImportIssue,
    SkippedDuplicateFile,
    TournamentImportResult,
)


class TournamentFolderError(ValueError):
    """Raised only when the tournament root itself is invalid."""


def _path_key(path: Path) -> tuple[str, str]:
    return (path.name.casefold(), path.name)


def _map_fingerprint(played_map: PlayedMap) -> str:
    records = sorted(played_map.performances, key=lambda item: item.steamid64)
    canonical_records = [
        [getattr(record, column) for column in SUPPORTED_COLUMNS] for record in records
    ]
    payload = json.dumps(
        canonical_records,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def import_tournament_folder(
    root: Path | str,
    *,
    best_of_by_series: Mapping[str, object],
) -> TournamentImportResult:
    """Import direct-child series folders using explicit BestOf metadata."""
    root = Path(root)
    if not root.exists():
        raise TournamentFolderError(f"tournament root does not exist: {root}")
    if not root.is_dir():
        raise TournamentFolderError(f"tournament root is not a directory: {root}")

    folders = tuple(sorted((item for item in root.iterdir() if item.is_dir()), key=_path_key))
    imported: list[ImportedFile] = []
    duplicates: list[SkippedDuplicateFile] = []
    invalid: list[ImportIssue] = []
    series_issues: list[ImportIssue] = []
    accepted_fingerprints: dict[str, Path] = {}
    maps_by_series: dict[str, list[PlayedMap]] = {folder.name: [] for folder in folders}
    discovered_csv_count = 0

    for folder in folders:
        csv_files = sorted(
            (item for item in folder.iterdir() if item.is_file() and item.suffix.lower() == ".csv"),
            key=_path_key,
        )
        discovered_csv_count += len(csv_files)
        mapnumbers: set[int] = set()
        for path in csv_files:
            try:
                played_map = parse_lan_match_csv(path, folder.name)
            except (LanMatchCsvError, ValueError) as error:
                invalid.append(ImportIssue(path, str(error)))
                continue
            fingerprint = _map_fingerprint(played_map)
            if fingerprint in accepted_fingerprints:
                duplicates.append(
                    SkippedDuplicateFile(path, accepted_fingerprints[fingerprint], fingerprint)
                )
                continue
            if played_map.mapnumber in mapnumbers:
                invalid.append(
                    ImportIssue(
                        path,
                        f"duplicate mapnumber {played_map.mapnumber} in series {folder.name}",
                    )
                )
                continue
            mapnumbers.add(played_map.mapnumber)
            accepted_fingerprints[fingerprint] = path
            maps_by_series[folder.name].append(played_map)
            imported.append(ImportedFile(path, fingerprint, played_map))

    folder_names = {folder.name for folder in folders}
    for key in sorted(best_of_by_series, key=lambda item: (str(item).casefold(), str(item))):
        if not isinstance(key, str) or key not in folder_names:
            series_issues.append(
                ImportIssue(root / str(key), f"best_of metadata references unknown series: {key}")
            )
        elif not isinstance(best_of_by_series[key], BestOf):
            series_issues.append(
                ImportIssue(
                    root / key,
                    f"best_of metadata for series {key} must be a BestOf value",
                )
            )

    imported_series: list[ImportedSeries] = []
    series: list[PlayedSeries] = []
    for folder in folders:
        maps = tuple(sorted(maps_by_series[folder.name], key=lambda item: item.mapnumber))
        if not maps:
            continue
        supplied_best_of = best_of_by_series.get(folder.name)
        best_of = supplied_best_of if isinstance(supplied_best_of, BestOf) else None
        imported_series.append(ImportedSeries(folder.name, folder, maps, best_of))
        if folder.name not in best_of_by_series:
            series_issues.append(
                ImportIssue(folder, f"best_of metadata is required for series {folder.name}")
            )
            continue
        if best_of is None:
            continue
        try:
            series.append(PlayedSeries(folder.name, best_of, maps))
        except ValueError as error:
            series_issues.append(ImportIssue(folder, str(error)))

    return TournamentImportResult(
        root=root,
        discovered_series_folders=folders,
        discovered_csv_count=discovered_csv_count,
        imported_files=tuple(imported),
        skipped_duplicates=tuple(duplicates),
        invalid_files=tuple(invalid),
        series_issues=tuple(series_issues),
        imported_series=tuple(imported_series),
        series=tuple(series),
    )
