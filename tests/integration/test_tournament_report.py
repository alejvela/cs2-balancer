"""SCRUM-23 composition and HTML contracts, using existing small factories."""

from dataclasses import FrozenInstanceError, replace
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import pytest

from application.player_rankings import rank_map, rank_series, rank_tournament
from application.tournament_report import (
    build_tournament_report,
    generate_tournament_report,
)
from exporters.tournament_html import (
    COMPONENT_LABELS,
    STAT_LABELS,
    TournamentHtmlExporter,
    _formula_label,
)
from models.lan_match import BestOf
from models.player_merit import ACTIVE_MERIT_IDS
from models.tournament_import import ImportIssue
from tests.integration.test_tournament_folder_import import write_map
from tests.unit.models.test_statistics import import_result, performance, played_map


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.ids = []
        self.links = []
        self.awards = []
        self.text = []
        self.stack = []
        self.feed(html)
        assert not self.stack

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag not in {"meta", "br", "hr", "img", "input", "link"}:
            self.stack.append(tag)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if "href" in attrs:
            self.links.append(attrs["href"])
        if "data-rule" in attrs:
            self.awards.append(attrs["data-rule"])
        assert not any(key.startswith("on") for key in attrs)

    def handle_endtag(self, tag):
        assert self.stack.pop() == tag

    def handle_data(self, data):
        self.text.append(data)


def sample_import():
    return import_result(
        *(
            played_map(
                "series",
                number,
                performance(
                    "regular",
                    name="Regular",
                    kills=10,
                    damage=1000,
                    head_shot_kills=3,
                    shots_fired_total=10,
                    shots_on_target_total=5,
                    utility_damage=100,
                ),
                *(
                    (performance("star", name="Star", kills=40, damage=4000),)
                    if number == 0
                    else ()
                ),
            )
            for number in range(4)
        )
    )


def test_global_order_eligibility_mvp_and_impact_are_existing_results():
    source = sample_import()
    report = build_tournament_report(source, tournament_id="lan")
    ranking = rank_tournament(source, tournament_id="lan")
    assert report.leaderboard.ranking == ranking
    assert (
        tuple(player.entry for player in report.leaderboard.players) == ranking.entries
    )
    assert ranking.entries[0].player_id == "star"
    assert not ranking.entries[0].tournament_eligibility.eligible
    assert report.mvp.entry.player_id == "regular"
    html = TournamentHtmlExporter().render(report)
    global_table = html.split('id="leaderboard"')[1].split('id="merits"')[0]
    assert global_table.index("Star") < global_table.index("Regular")
    assert "No elegible para MVP global" in global_table
    for player in report.leaderboard.players:
        for component in player.entry.impact.components:
            assert escape(COMPONENT_LABELS[component.component_id]) in html
            assert f"Contribución: {component.weighted_contribution:.2f}" in html
            for evidence in component.evidence:
                assert escape(STAT_LABELS[evidence.metric]) in html
    assert f"Impact v{ranking.model_version}" in html


def test_no_eligible_player_mvp_unavailable_and_empty_document():
    source = sample_import()
    report = build_tournament_report(source, tournament_id="lan")
    entries = tuple(
        replace(
            entry,
            tournament_eligibility=replace(
                entry.tournament_eligibility, eligible=False
            ),
        )
        for entry in report.leaderboard.ranking.entries
    )
    board = replace(
        report.leaderboard,
        ranking=replace(report.leaderboard.ranking, entries=entries),
        players=tuple(
            replace(player, entry=entry)
            for player, entry in zip(report.leaderboard.players, entries, strict=True)
        ),
    )
    report = replace(report, leaderboard=board)
    assert report.mvp is None
    assert "MVP no disponible" in TournamentHtmlExporter().render(report)
    empty = build_tournament_report(import_result(), tournament_id="empty")
    html = TournamentHtmlExporter().render(empty)
    assert empty.mvp is None
    assert "No hay jugadores con datos validados" in html
    assert Document(html).awards == []


def test_merit_order_multiple_titles_and_generic_utility():
    report = build_tournament_report(sample_import(), tournament_id="lan")
    html = TournamentHtmlExporter().render(report)
    assert Document(html).awards == list(ACTIVE_MERIT_IDS)
    assert any(len(player.merits) > 1 for player in report.leaderboard.players)
    assert all(merit.rule_id != "charmander" for merit in report.merits.merits)
    assert "Charmander no está disponible" in html
    assert "El Alquimista utiliza únicamente daño de utilidad genérico" in html
    for merit in report.merits.merits:
        assert escape(_formula_label(merit.explanation)) in html
        assert escape(_formula_label(merit.evidence_label)) in html


@pytest.mark.parametrize(
    ("best_of", "count"), [(BestOf.BO1, 1), (BestOf.BO3, 2), (BestOf.BO5, 3)]
)
def test_folder_to_html_series_and_map_rankings(tmp_path, best_of, count):
    from importers.tournament_folder import import_tournament_folder

    root = tmp_path / "tournament"
    for number in range(count):
        write_map(
            root / "final" / f"map-{number}.csv",
            mapnumber=number,
            row_overrides={0: {"kills": str(number + 1), "damage": str(100 + number)}},
        )
    metadata = {"final": best_of}
    imported = import_tournament_folder(root, best_of_by_series=metadata)
    report = build_tournament_report(imported, tournament_id="lan")
    assert report.series[0].accepted
    assert report.series[0].leaderboard.ranking == rank_series(imported.series[0])
    assert tuple(item.leaderboard.ranking for item in report.series[0].maps) == tuple(
        rank_map(item) for item in imported.series[0].maps
    )
    output = generate_tournament_report(
        root,
        tmp_path / "report" / "lan.html",
        best_of_by_series=metadata,
        tournament_id="lan",
    )
    html = output.read_text(encoding="utf-8")
    assert html == TournamentHtmlExporter().render(report)
    assert best_of.name in html
    assert "Resultado agregado de la serie" in html
    assert html.count("Clasificación del mapa") == count
    assert "map-0.csv" in html and "match-1" in html
    document = Document(html)
    assert html.startswith("<!DOCTYPE html>") and "style" in document.tags
    assert "script" not in document.tags
    assert len(document.ids) == len(set(document.ids))
    assert all(
        link.startswith("#") and link[1:] in document.ids for link in document.links
    )


def test_identity_details_undefined_ratios_and_determinism():
    maps = (
        played_map("s", 0, performance("1", name="Old", team="Blue")),
        played_map("s", 1, performance("1", name="New", team="Red")),
    )
    source = import_result(*maps)
    first = build_tournament_report(source, tournament_id="lan")
    # Reverse enumeration without changing the fixture's synthetic fingerprints.
    reversed_source = replace(
        source,
        imported_files=tuple(reversed(source.imported_files)),
        imported_series=tuple(
            replace(series, maps=tuple(reversed(series.maps)))
            for series in reversed(source.imported_series)
        ),
    )
    second = build_tournament_report(reversed_source, tournament_id="lan")
    assert first.leaderboard == second.leaderboard
    assert len(first.leaderboard.players) == 1
    player = first.leaderboard.players[0]
    metrics = {item.label: item.value for item in player.metrics}
    assert (
        metrics["Headshot rate"]
        == metrics["Accuracy"]
        == metrics["Entry conversion"]
        == "—"
    )
    # Preserve the existing SCRUM-20 finite K/D convention explicitly.
    assert metrics["K/D"] == "0.00"
    html = TournamentHtmlExporter().render(first)
    assert html == TournamentHtmlExporter().render(first)
    assert html == TournamentHtmlExporter().render(second)
    for text in (
        "Old",
        "New",
        "Blue",
        "Red",
        "steamid64: 1",
        "Totales",
        "Estadísticas derivadas",
        "Tiempo con vida",
        "Dinero ahorrado",
    ):
        assert text in html
    with pytest.raises(FrozenInstanceError):
        first.title = "changed"


def test_partial_import_diagnostics_preserve_valid_maps_and_reject_invalid(tmp_path):
    from importers.tournament_folder import import_tournament_folder

    root = tmp_path / "tournament"
    write_map(root / "accepted" / "map.csv")
    write_map(root / "accepted" / "duplicate.csv")
    write_map(root / "pending" / "map.csv", matchid="other")
    write_map(root / "bad-count" / "bad.csv", row_order=(0,))
    (root / "malformed").mkdir()
    (root / "malformed" / "bad.csv").write_text("not,a,valid,csv\n", encoding="utf-8")
    (root / "empty").mkdir()
    imported = import_tournament_folder(
        root, best_of_by_series={"accepted": BestOf.BO1}
    )
    report = build_tournament_report(imported, tournament_id="lan")
    assert report.statistics.map_count == 2
    assert len(imported.series) == 1
    assert len(imported.invalid_files) == 2
    assert len(imported.skipped_duplicates) == 1
    assert any(not series.accepted for series in report.series)
    assert report.leaderboard.ranking == rank_tournament(imported, tournament_id="lan")
    html = TournamentHtmlExporter().render(report)
    for issue in imported.invalid_files + imported.series_issues:
        assert escape(issue.message) in html
    assert "Formato BO no disponible" in html
    assert "Duplicados omitidos · 1" in html
    assert "sin mapas aceptados" in html
    assert "Metadatos de serie pendientes o no válidos" in html
    assert "huella digital" in html
    Document(html)


def test_unconstructible_series_retains_diagnostics_and_maps(tmp_path):
    from importers.tournament_folder import import_tournament_folder

    for number in range(2):
        write_map(tmp_path / "s" / f"{number}.csv", mapnumber=number)
    imported = import_tournament_folder(tmp_path, best_of_by_series={"s": BestOf.BO1})
    assert not imported.series
    report = build_tournament_report(imported, tournament_id="lan")
    assert report.statistics.map_count == 2
    assert not report.series[0].accepted
    assert "BO1 cannot contain 2 maps" in TournamentHtmlExporter().render(report)


def test_all_untrusted_text_is_escaped():
    malicious = "<script>alert(\"x\")</script> & 'quoted'"
    source = import_result(
        played_map(malicious, 0, performance("1", name=malicious, team=malicious))
    )
    source = replace(source, invalid_files=(ImportIssue(Path(malicious), malicious),))
    report = build_tournament_report(source, tournament_id="lan", title=malicious)
    html = TournamentHtmlExporter().render(report)
    assert malicious not in html
    assert escape(malicious) in html
    document = Document(html)
    assert "script" not in document.tags
    assert document.text.count(malicious) > 1


def test_exporter_does_not_invoke_domain_services(monkeypatch):
    import application.player_merits as merits_service
    import application.player_rankings as ranking_service
    import application.statistics_aggregation as statistics_service

    report = build_tournament_report(sample_import(), tournament_id="lan")

    def forbidden(*args, **kwargs):
        raise AssertionError("exporter must not calculate domain results")

    monkeypatch.setattr(merits_service, "generate_tournament_merits", forbidden)
    for name in ("rank_map", "rank_series", "rank_tournament"):
        monkeypatch.setattr(ranking_service, name, forbidden)
    monkeypatch.setattr(statistics_service, "aggregate_tournament", forbidden)
    assert '<html lang="es">' in TournamentHtmlExporter().render(report)


def test_spanish_player_facing_contract():
    source = sample_import()
    report = build_tournament_report(source, tournament_id="lan")
    html = TournamentHtmlExporter().render(report)
    assert '<html lang="es">' in html
    assert "<title>CS2 LAN · Informe del torneo</title>" in html
    for label in (
        "Resumen del torneo",
        "Clasificación general",
        "MVP del torneo",
        "Premios y títulos",
        "Estadísticas por jugador",
        "Calidad de los datos",
        "Posición",
        "Jugador",
        "Mapas",
        "Bajas",
        "Muertes",
        "Asistencias",
        "Daño / mapa",
        "% Headshots",
        "Elegible para MVP",
        "No elegible para MVP global",
        "Desglose de impacto",
        "Combate",
        "Aperturas / Entry",
        "Multikill",
        "Clutch",
        "Juego en equipo",
        "Utilidad / Flash",
        "Evidencia numérica",
        "Dinero ahorrado",
        "Tiempo con vida",
        "Enemigos cegados",
        "Mapas jugados:",
        "Mínimo requerido:",
    ):
        assert label in html
    # Neither headings nor surrounding explanations should leak the old UI.
    for old in (
        "Tournament overview",
        "Global leaderboard",
        "Tournament MVP",
        "Merit titles",
        "Player details",
        "Data quality",
        "Numeric evidence",
        "Eligible for MVP",
        "Not eligible for global MVP",
        "Component evidence",
        "Supported Clutch",
        "Teamplay",
        "Utility / Flash",
        "played mapas",
        "Competitive recognition",
        "Global results include",
        "weight ",
    ):
        assert old not in html
    assert report.leaderboard.ranking == rank_tournament(source, tournament_id="lan")
    assert tuple(merit.rule_id for merit in report.merits.merits) == ACTIVE_MERIT_IDS
    assert report.leaderboard.players[0].entry.impact.components[0].label == "Combat"
    assert report.leaderboard.players[0].entry.tournament_eligibility.reason.startswith(
        "played "
    )


def test_spanish_unavailable_states_and_original_diagnostic_context():
    original = "best_of metadata is required for series pending"
    source = replace(
        import_result(), series_issues=(ImportIssue(Path("pending"), original),)
    )
    html = TournamentHtmlExporter().render(
        build_tournament_report(source, tournament_id="empty")
    )
    for label in (
        "MVP no disponible",
        "No hay títulos disponibles",
        "No hay jugadores con datos validados",
        "Incidencias de las series",
        "Los mensajes técnicos originales se conservan",
    ):
        assert label in html
    assert original in html
    assert "pending" in html
