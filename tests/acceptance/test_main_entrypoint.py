"""Offline bootstrap boundaries and operator failure semantics."""

import ast
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from configuration.application_config import ApplicationConfig
from configuration.composition_root import create_balancing_composition
from configuration.reporting_factory import create_reporting_components
from optimizer.modes.optimization_mode import OptimizationMode
from tests.unit.test_composition_root import players, small_config


def test_main_has_no_engine_factories_or_alternative_global_path():
    for name in (
        "_composition_config",
        "create_scoring_model",
        "create_objective_engine",
        "create_pipeline",
        "create_optimization_pipeline",
        "create_optimizer",
        "create_balancer",
        "create_global_problem",
        "create_global_optimizer",
        "create_global_metrics",
        "run_global_optimization",
        "LegacyGlobalRunner",
        "APPLICATION_CONFIG",
        "STABLE_OPTIMIZATION_CONFIG",
        "GLOBAL_OPTIMIZATION_CONFIG",
        "NUMBER_OF_TEAMS",
        "TEAM_SIZE",
        "EXPECTED_PLAYER_COUNT",
        "OPTIMIZATION_MODE",
    ):
        assert not hasattr(main, name), name
    tree = ast.parse(Path(main.__file__).read_text(encoding="utf-8"))
    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert sum(isinstance(n, ast.Attribute) and n.attr == "run" for n in calls) == 1
    assert not any(
        isinstance(n, ast.Attribute) and n.attr in {"optimize", "detect_mode"}
        for n in calls
    )
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(
        name
        and name.startswith(
            (
                "configuration.composition_root",
                "objective.",
                "optimizer.global_search",
                "configuration.global_factory",
            )
        )
        for name in imports
    )


@pytest.mark.parametrize("mode", list(OptimizationMode))
@pytest.mark.parametrize("preassigned", [False, True])
def test_independent_reporting_preserves_html_and_console(
    tmp_path, capsys, mode, preassigned
):
    config = replace(small_config(), optimization_mode=mode)
    roster = players()
    if preassigned:
        for i, player in enumerate(roster):
            player.team_number = i // 2 + 1
    result = BalancingApplication(config).run(BalancingRequest(roster, 2, mode))
    composition = create_balancing_composition(config)
    reporting = create_reporting_components(config)
    old = composition.balancer.export(result=result, output=tmp_path / "old.html")
    new = reporting.exporter.export(result=result, output=tmp_path / "new.html")
    assert new.read_bytes() == old.read_bytes()
    assert reporting.exporter.scoring_model is reporting.scoring_model
    main.print_result(result, composition.scoring_model)
    expected = capsys.readouterr().out
    main.print_result(result, reporting.scoring_model)
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize(
    "value,message", [(None, "no está definida"), ("  ", "está vacía")]
)
def test_faceit_key_errors(monkeypatch, value, message):
    if value is None:
        monkeypatch.delenv("FACEIT_API_KEY", raising=False)
    else:
        monkeypatch.setenv("FACEIT_API_KEY", value)
    with pytest.raises(RuntimeError, match=message):
        main.get_faceit_api_key()


def test_faceit_refresh_configuration_and_files_offline(monkeypatch, tmp_path):
    config = small_config()
    source = tmp_path / "players.csv"
    source.write_text("Nick,FaceitNickname,Seed,Team\n", encoding="utf-8")
    config = replace(
        config,
        paths=replace(
            config.paths,
            source_players=source,
            generated_stats=tmp_path / "stats.csv",
            faceit_errors=tmp_path / "errors.csv",
        ),
    )
    monkeypatch.setenv("FACEIT_API_KEY", "  offline-key  ")
    seen = {}
    records = [SimpleNamespace(is_valid=True) for _ in range(4)]
    records.append(
        SimpleNamespace(is_valid=False, nickname="Failed", error="offline error")
    )

    class Client:
        def __init__(self, **kwargs):
            seen["client"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            seen["closed"] = True

    class Scraper:
        errors = [
            {
                "row": 5,
                "nick": "Failed",
                "faceit_nickname": "Failed",
                "error": "offline error",
            }
        ]

        def __init__(self, **kwargs):
            seen["scraper"] = kwargs

        def scrape(self, path):
            assert path == source
            return records

    exports = []

    def export(self, *, records, output):
        exports.append((records, output))
        return output

    monkeypatch.setattr(main, "FaceitApiClient", Client)
    monkeypatch.setattr(main, "FaceitScraper", Scraper)
    monkeypatch.setattr(main.CsvScraperExporter, "export", export)
    assert main.resolve_players_file(config) == config.paths.generated_stats
    assert seen["closed"]
    assert seen["client"] == dict(
        api_key="offline-key",
        preferred_game_id=config.faceit.preferred_game_id,
        fallback_game_ids=config.faceit.fallback_game_ids,
        timeout=config.faceit.timeout_seconds,
        retries=config.faceit.retries,
        retry_delay=config.faceit.retry_delay_seconds,
    )
    assert seen["scraper"]["recent_matches"] == config.faceit.recent_matches
    assert seen["scraper"]["strict"] == config.faceit.strict
    assert seen["scraper"]["delay"] == config.faceit.delay_seconds
    assert seen["scraper"]["maximum_seed_one_players"] == config.event.number_of_teams
    assert exports == [
        (records[-1:], config.paths.faceit_errors),
        (records[:4], config.paths.generated_stats),
    ]
    records.pop(0)
    with pytest.raises(
        RuntimeError, match="El número de jugadores válidos no coincide"
    ):
        main.resolve_players_file(config)
    assert exports[-1] == (records[-1:], config.paths.faceit_errors)


def test_generated_csv_reuse_and_missing_source(monkeypatch, tmp_path):
    config = small_config()
    config = replace(
        config,
        faceit=replace(config.faceit, run_import=False),
        paths=replace(
            config.paths,
            generated_stats=tmp_path / "stats.csv",
            source_players=tmp_path / "missing.csv",
        ),
    )
    with pytest.raises(FileNotFoundError, match="No existe el archivo generado"):
        main.resolve_players_file(config)
    config.paths.generated_stats.write_text("offline", encoding="utf-8")
    assert main.resolve_players_file(config) == config.paths.generated_stats
    with pytest.raises(FileNotFoundError, match="No existe el archivo de entrada"):
        main.run_faceit_import(config)


@pytest.mark.parametrize(
    "error,code,message",
    [
        (FileNotFoundError("missing"), 1, "ERROR DE ARCHIVO: missing"),
        (TypeError("bad"), 1, "ERROR: bad"),
        (ValueError("bad"), 1, "ERROR: bad"),
        (RuntimeError("bad"), 1, "ERROR: bad"),
        (KeyError("bad"), 1, "ERROR:"),
        (AssertionError("bad"), 1, "ERROR: bad"),
        (KeyboardInterrupt(), 130, "Proceso cancelado por el usuario."),
    ],
)
def test_exit_codes_and_messages(monkeypatch, capsys, error, code, message):
    def fail(config):
        raise error

    monkeypatch.setattr(main, "resolve_players_file", fail)
    assert main.main() == code
    assert message in capsys.readouterr().out


def test_unhandled_errors_still_propagate(monkeypatch):
    def fail(config):
        raise OSError("unhandled")

    monkeypatch.setattr(main, "resolve_players_file", fail)
    with pytest.raises(OSError, match="unhandled"):
        main.main()


def test_roster_validation_prevents_application_call(monkeypatch, tmp_path, capsys):
    config = small_config()
    monkeypatch.setattr(
        ApplicationConfig, "production_defaults", classmethod(lambda cls: config)
    )
    monkeypatch.setattr(
        main, "resolve_players_file", lambda config: tmp_path / "players.csv"
    )
    monkeypatch.setattr(
        main.CssStatsImporter, "load", lambda self, source: players()[:1]
    )

    def forbidden(*args):
        pytest.fail("Invalid roster must not reach application")

    monkeypatch.setattr(BalancingApplication, "run", forbidden)
    assert main.main() == 1
    assert "Se han importado 1 jugadores. Se esperaban 4." in capsys.readouterr().out


@pytest.mark.parametrize(
    "mode,assigned",
    [
        (OptimizationMode.FAST, False),
        (OptimizationMode.STABLE, False),
        (OptimizationMode.GLOBAL, False),
        (OptimizationMode.GLOBAL, True),
    ],
)
def test_csv_to_application_to_html(monkeypatch, tmp_path, mode, assigned):
    """Real resolution/import/export, including the application-owned Team mode."""
    config = small_config()
    source = tmp_path / "stats.csv"
    source.write_text(
        "Nick,SteamID,ELO,KD,Team\n"
        + "\n".join(
            f"P{i},S{i},{1500 + i * 100},1.0,{i // 2 + 1 if assigned else ''}"
            for i in range(4)
        ),
        encoding="utf-8",
    )
    config = replace(
        config,
        optimization_mode=mode,
        faceit=replace(config.faceit, run_import=False),
        paths=replace(
            config.paths, generated_stats=source, output_report=tmp_path / "report.html"
        ),
    )
    monkeypatch.setattr(
        ApplicationConfig, "production_defaults", classmethod(lambda cls: config)
    )
    events, requests, results = [], [], []
    load = main.CssStatsImporter.load

    def import_players(self, path):
        assert path == source
        assert self.strict is config.event.importer_strict
        events.append("import")
        return load(self, path)

    class ObservedApplication(BalancingApplication):
        def __init__(self, received_config):
            assert received_config is config
            super().__init__(received_config)

        def run(self, request):
            events.append("application")
            requests.append(request)
            result = super().run(request)
            results.append(result)
            return result

    from exporters.html_v2.html_exporter import HtmlExporterV2

    export = HtmlExporterV2.export

    def export_report(self, result, output):
        events.append("export")
        assert result is results[0]
        assert output == config.paths.output_report
        return export(self, result, output)

    monkeypatch.setattr(main.CssStatsImporter, "load", import_players)
    monkeypatch.setattr(main, "BalancingApplication", ObservedApplication)
    monkeypatch.setattr(HtmlExporterV2, "export", export_report)
    assert main.main() == 0
    assert events == ["import", "application", "export"]
    (request,) = requests
    (result,) = results
    assert request.number_of_teams == config.event.number_of_teams
    assert request.optimization_mode is mode
    assert request.title == config.event.report_title
    assert result.evaluation_only is assigned
    assert result.metadata["source"] == "CSV"
    assert result.metadata["source_file"] == str(source)
    assert result.metadata["mode"] == result.mode.value
    assert result.metadata["optimization_mode"] == (None if assigned else mode.value)
    assert config.paths.output_report.is_file()
