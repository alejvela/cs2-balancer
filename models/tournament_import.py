"""Immutable structured results for a tournament-folder import."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.lan_match import BestOf, PlayedMap, PlayedSeries


@dataclass(frozen=True, slots=True)
class ImportIssue:
    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class ImportedFile:
    path: Path
    fingerprint: str
    played_map: PlayedMap


@dataclass(frozen=True, slots=True)
class SkippedDuplicateFile:
    path: Path
    original_path: Path
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ImportedSeries:
    """Valid maps grouped by folder, whether or not BestOf is known yet."""

    series_id: str
    folder: Path
    maps: tuple[PlayedMap, ...]
    best_of: BestOf | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "maps", tuple(self.maps))


@dataclass(frozen=True, slots=True)
class TournamentImportResult:
    root: Path
    discovered_series_folders: tuple[Path, ...]
    discovered_csv_count: int
    imported_files: tuple[ImportedFile, ...]
    skipped_duplicates: tuple[SkippedDuplicateFile, ...]
    invalid_files: tuple[ImportIssue, ...]
    series_issues: tuple[ImportIssue, ...]
    imported_series: tuple[ImportedSeries, ...]
    series: tuple[PlayedSeries, ...]

    @property
    def maps(self) -> tuple[PlayedMap, ...]:
        return tuple(item.played_map for item in self.imported_files)
