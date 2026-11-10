"""Real application-to-report regression for the v0.8 publication blocker."""

import pytest

from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from configuration.reporting_factory import create_reporting_components
from main import print_global_optimization, print_result
from optimizer.modes.optimization_mode import OptimizationMode
from tests.acceptance.test_engine_acceptance import synthetic_players
from tests.acceptance.test_v08_engine_contracts import acceptance_config


@pytest.mark.parametrize(
    "mode,use_incumbent,preassigned",
    [
        (OptimizationMode.GLOBAL, False, False),
        (OptimizationMode.GLOBAL, True, False),
        (OptimizationMode.FAST, True, False),
        (OptimizationMode.STABLE, True, False),
        (OptimizationMode.GLOBAL, False, True),
        (OptimizationMode.GLOBAL, True, True),
        (OptimizationMode.FAST, True, True),
        (OptimizationMode.STABLE, True, True),
    ],
)
def test_application_exports_html_and_console_without_changing_results(
    tmp_path, capsys, mode, use_incumbent, preassigned,
):
    config = acceptance_config(mode, use_incumbent=use_incumbent)
    players = synthetic_players()[:4]
    if preassigned:
        for index, player in enumerate(players):
            player.team_number = 1 + index // 2
    result = BalancingApplication(config).run(BalancingRequest(players, 2, mode))
    before = result.as_dict()
    reporting = create_reporting_components(config)
    destination = tmp_path / "report.html"
    assert reporting.exporter.export(result, destination) == destination
    html = destination.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    for section in ("summary", "ranking", "activity", "teams"):
        assert f'id="panel-{section}"' in html
    assert f"{result.final_score:.2f}" in html
    print_result(result, reporting.scoring_model)
    if mode is OptimizationMode.GLOBAL and not preassigned:
        print_global_optimization(result)
    console = capsys.readouterr().out

    if preassigned:
        assert 'data-report-mode="preassigned"' in html
        assert "La distribución se ha evaluado sin modificar la asignación de jugadores." in html
        assert "Mejora obtenida:" not in html
        assert "Mejora no disponible" not in html
        assert f"Puntuación equilibrio: {result.final_score:.2f}" in console
    elif mode is OptimizationMode.GLOBAL and not use_incumbent:
        assert result.initial_score is None
        assert result.improvement is None
        assert "Mejora no disponible (sin solución inicial)" in html
        assert "Mejora obtenida:" not in html
        assert "Sin incumbent inicial" in html
        assert "N/A" in html
        assert "Puntuación inicial:   No disponible (sin solución inicial)" in console
        assert "Mejora total:         No disponible (sin solución inicial)" in console
        assert "Incumbent inicial:      No disponible (sin solución inicial)" in console
        assert "Mejora GLOBAL:          No disponible (sin solución inicial)" in console
    else:
        assert result.initial_score is not None
        assert result.improvement is not None
        assert f"Mejora obtenida: {result.improvement:+.2f} puntos." in html
        assert "Mejora no disponible" not in html
        assert f"Puntuación inicial:   {result.initial_score:.2f}" in console
        assert f"Mejora total:         {result.improvement:+.2f}" in console
        if mode is OptimizationMode.GLOBAL:
            assert f"Incumbent inicial:      {result.initial_score:.4f}" in console
            assert f"Mejora GLOBAL:          {result.improvement:+.4f}" in console
    assert result.as_dict() == before
