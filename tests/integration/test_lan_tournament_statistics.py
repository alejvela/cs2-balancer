"""Frozen SCRUM-24 product acceptance, from on-disk CSVs to Spanish HTML."""

import csv
import json
import shutil
from dataclasses import asdict, replace
from html import escape
from pathlib import Path

import pytest

from application.player_merits import generate_tournament_merits
from application.tournament_report import (
    build_tournament_report,
    generate_tournament_report,
)
from exporters.tournament_html import TournamentHtmlExporter
from importers.tournament_folder import import_tournament_folder
from models.lan_match import BestOf
from models.player_impact import LAN_IMPACT_VERSION
from models.player_merit import ACTIVE_MERIT_IDS, MeritCategory
from tests.integration.test_tournament_report import Document

ROOT = Path(__file__).parents[1] / "fixtures" / "lan_tournament_acceptance"
EXPECTED = json.loads((ROOT / "expected.json").read_text(encoding="utf-8"))
BEST_OF = {name: BestOf(value) for name, value in EXPECTED["best_of"].items()}
WEIGHTS = dict(
    combat=0.40,
    opening=0.15,
    multikill=0.10,
    supported_clutch=0.15,
    teamplay=0.10,
    utility_flash=0.10,
)


def flow(root=ROOT):
    imported = import_tournament_folder(root, best_of_by_series=BEST_OF)
    return imported, build_tournament_report(imported, tournament_id="frozen-lan")


@pytest.fixture(scope="module")
def tournament():
    return flow()


def ids(board):
    return [entry.player_id for entry in board.ranking.entries]


def test_discovery_strict_validation_and_global_duplicate_provenance(tournament):
    imported, report = tournament
    assert (
        dict(
            folders=len(imported.discovered_series_folders),
            discovered_csv=imported.discovered_csv_count,
            imported_csv=len(imported.imported_files),
            duplicates=len(imported.skipped_duplicates),
            invalid=len(imported.invalid_files),
            accepted_series=len(imported.series),
            maps=len(imported.maps),
        )
        == EXPECTED["import_counts"]
    )
    assert sorted(
        str(item.path.relative_to(ROOT)).replace("\\", "/")
        for item in imported.imported_files
    ) == sorted(EXPECTED["valid_files"])
    assert all(len(item.performances) == 10 for item in imported.maps)
    (duplicate,) = imported.skipped_duplicates
    assert duplicate.path == ROOT / "zz-duplicate/reordered.csv"
    assert duplicate.original_path == ROOT / "final/map-0.csv"
    original = next(
        item for item in imported.imported_files if item.path == duplicate.original_path
    )
    assert duplicate.fingerprint == original.fingerprint
    (issue,) = imported.invalid_files
    assert issue.path == ROOT / "zz-malformed/bad.csv"
    assert issue.message == "missing required columns: kills"
    assert not imported.series_issues
    assert report.statistics.map_count == 7
    assert report.statistics.series_count == 4
    assert report.empty_folders == tuple(
        str(ROOT / name) for name in ("zz-duplicate", "zz-malformed")
    )


def test_every_raw_total_is_reconciled_without_production_aggregation(tournament):
    _, report = tournament
    # Only the explicit authoritative manifest is read: no production parser,
    # fingerprint, identity resolver, or aggregation is used for this sum.
    records = []
    for filename in EXPECTED["valid_files"]:
        with (ROOT / filename).open(encoding="utf-8", newline="") as source:
            records.extend(csv.DictReader(source))
    assert len(records) == 70
    assert {p.player_id for p in report.statistics.players} == set(EXPECTED["players"])
    for player in report.statistics.players:
        frozen = EXPECTED["players"][player.player_id]
        rows = [row for row in records if row["steamid64"] == player.player_id]
        summed = {
            field: sum(int(row[field]) for row in rows) for field in frozen["raw"]
        }
        assert summed == frozen["raw"] == asdict(player.raw)
        assert player.maps_played == frozen["maps_played"] == len(rows)
        assert player.series_played == frozen["series_played"]
        assert player.display_name == frozen["display_name"]
        for metric, value in frozen["derived"].items():
            assert getattr(player, metric) == pytest.approx(value, abs=1e-10)


def test_alias_frequency_and_lexical_tie_keep_one_canonical_identity(tournament):
    _, report = tournament
    players = {p.player_id: p for p in report.statistics.players}
    atlas = players["76561198000000000"]
    assert atlas.observed_aliases == ("Atlas", "Atlas_2")
    assert atlas.display_name == "Atlas"  # Four observations versus three.
    assert atlas.maps_played == 7
    saver = players["76561198000000009"]
    assert saver.observed_aliases == ("Ahorro", "Zorro")
    assert saver.display_name == "Ahorro"  # Three each; lexical tie.
    assert saver.maps_played == 6


def test_frozen_impact_components_ranking_eligibility_and_mvp(tournament):
    _, report = tournament
    assert LAN_IMPACT_VERSION == report.leaderboard.ranking.model_version == "1.0"
    assert ids(report.leaderboard) == EXPECTED["tournament_ranking"]
    for entry in report.leaderboard.ranking.entries:
        frozen = EXPECTED["players"][entry.player_id]
        assert {
            c.component_id: c.score for c in entry.impact.components
        } == pytest.approx(frozen["components"], abs=1e-10)
        assert {c.component_id: c.weight for c in entry.impact.components} == WEIGHTS
        independent_total = sum(
            frozen["components"][key] * weight for key, weight in WEIGHTS.items()
        )
        assert entry.impact.score == pytest.approx(frozen["impact"], abs=1e-10)
        assert independent_total == pytest.approx(frozen["impact"], abs=1e-10)
        eligibility = entry.tournament_eligibility
        assert eligibility.eligible is frozen["eligible"]
        assert eligibility.maps_played == frozen["maps_played"]
        assert eligibility.required_maps == 4  # ceil(7 * 0.5)
    assert report.leaderboard.ranking.entries[0].player_id == "76561198000000010"
    assert not report.leaderboard.ranking.entries[0].tournament_eligibility.eligible
    assert report.mvp.entry.player_id == EXPECTED["mvp"] == "76561198000000002"


def test_folders_define_series_and_aggregate_impact_is_not_mean_map_impact(tournament):
    imported, report = tournament
    assert {s.series_id: (s.best_of.value, len(s.maps)) for s in imported.series} == {
        "group-a": (1, 1),
        "group-b": (1, 1),
        "semifinal": (3, 2),
        "final": (5, 3),
    }
    assert all(s.accepted for s in report.series)
    for series in report.series:
        assert ids(series.leaderboard) == EXPECTED["series_rankings"][series.series_id]
        for played in series.maps:
            key = f"{series.series_id}/map-{played.mapnumber}.csv"
            assert ids(played.leaderboard) == EXPECTED["map_rankings"][key]
    final = next(s for s in report.series if s.series_id == "final")
    pid = "76561198000000000"
    scores = [
        next(
            e.impact.score for e in m.leaderboard.ranking.entries if e.player_id == pid
        )
        for m in final.maps
    ]
    aggregate = next(e for e in final.leaderboard.ranking.entries if e.player_id == pid)
    assert aggregate.statistics.raw.kills == 120
    assert aggregate.maps_played == 3
    assert aggregate.impact.score != pytest.approx(sum(scores) / 3)
    global_entry = next(
        e for e in report.leaderboard.ranking.entries if e.player_id == pid
    )
    all_scores = [
        next(
            e.impact.score for e in m.leaderboard.ranking.entries if e.player_id == pid
        )
        for s in report.series
        for m in s.maps
    ]
    assert global_entry.impact.score != pytest.approx(sum(all_scores) / 7)
    # Matchids are reused across folders, and differ within the semifinal.
    assert len({m.matchid for m in imported.maps}) == 3
    assert not hasattr(final, "winner") and not hasattr(final, "complete")


def test_all_thirteen_merits_and_precision_secondary_tie_break(tournament):
    _, report = tournament
    assert list(ACTIVE_MERIT_IDS) == list(EXPECTED["merits"])
    assert [m.rule_id for m in report.merits.merits] == list(EXPECTED["merits"])
    assert {m.rule_id: m.player_id for m in report.merits.merits} == EXPECTED["merits"]
    merits = {m.rule_id: m for m in report.merits.merits}
    assert merits["pikachu"].category == MeritCategory.SUPPORT
    assert "utility_damage" in merits["el_alquimista"].evidence_label
    assert "fire" not in merits["el_alquimista"].evidence_label
    assert "charmander" not in merits
    players = {p.player_id: p for p in report.statistics.players}
    surgeon, aim = (players[f"7656119800000000{i}"] for i in (7, 8))
    assert surgeon.headshot_rate == aim.headshot_rate == 0.8
    assert surgeon.raw.head_shot_kills == aim.raw.head_shot_kills == 96
    assert surgeon.raw.kills == aim.raw.kills == 120
    assert (
        surgeon.raw.shots_on_target_total == 240 < aim.raw.shots_on_target_total == 640
    )
    assert merits["el_cirujano"].player_id == aim.player_id
    reversed_stats = replace(
        report.statistics, players=tuple(reversed(report.statistics.players))
    )
    assert generate_tournament_merits(reversed_stats) == report.merits


def test_duplicate_and_malformed_exports_cannot_change_statistics(tmp_path, tournament):
    _, original = tournament
    # Copy only known valid maps, while retaining empty diagnostic directories.
    for name in BEST_OF:
        (tmp_path / name).mkdir()
    for filename in EXPECTED["valid_files"]:
        shutil.copyfile(ROOT / filename, tmp_path / filename)
    imported, clean = flow(tmp_path)
    assert not imported.invalid_files and not imported.skipped_duplicates
    assert imported.discovered_csv_count == 7
    assert clean.statistics == original.statistics
    assert clean.leaderboard == original.leaderboard
    assert clean.merits == original.merits
    assert [s.leaderboard for s in clean.series] == [
        s.leaderboard for s in original.series
    ]


def test_standalone_spanish_report_and_two_stateless_end_to_end_runs(
    tmp_path, tournament
):
    imported, report = tournament
    again, second = flow()
    assert again == imported
    assert second == report  # Includes aggregates, all rankings, merits and provenance.
    html = TournamentHtmlExporter().render(report)
    assert TournamentHtmlExporter().render(second) == html
    for number in range(2):
        output = generate_tournament_report(
            ROOT,
            tmp_path / f"report-{number}.html",
            best_of_by_series=BEST_OF,
            tournament_id="frozen-lan",
        )
        assert output.read_text(encoding="utf-8") == html
    assert html.startswith("<!DOCTYPE html>") and '<html lang="es">' in html
    for text in (
        "Resumen del torneo",
        "Clasificación general",
        "MVP del torneo",
        "Premios y títulos",
        "Estadísticas por jugador",
        "Calidad de los datos",
        "BO1",
        "BO3",
        "BO5",
        "Atlas",
        "Atlas_2",
        "Clutch",
        "No elegible para MVP global",
        "Duplicados omitidos",
        "reordered.csv",
        "bad.csv",
        "missing required columns: kills",
    ):
        assert text in html
    for merit in report.merits.merits:
        award = html.split(f'data-rule="{merit.rule_id}"', 1)[1].split("</article>", 1)[
            0
        ]
        assert (
            f">{escape(EXPECTED['players'][EXPECTED['merits'][merit.rule_id]]['display_name'])}</a>"
            in award
        )
    mvp_card = html.split('class="card mvp"', 1)[1].split("</section>", 1)[0]
    assert ">Clutch</a>" in mvp_card
    global_table = html.split('id="leaderboard"', 1)[1].split('id="merits"', 1)[0]
    assert ">Atlas</a>" in global_table
    assert ">Atlas_2</a>" not in global_table
    document = Document(html)
    assert document.awards == list(EXPECTED["merits"])
    assert "charmander" not in document.awards
    assert "style" in document.tags
    assert not {"script", "link", "iframe", "img"}.intersection(document.tags)
    assert all(
        link.startswith("#") and link[1:] in document.ids for link in document.links
    )
