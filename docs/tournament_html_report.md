# Standalone LAN tournament HTML report (SCRUM-23)

## Public application flow

```python
from application.tournament_report import generate_tournament_report
from models.lan_match import BestOf

output = generate_tournament_report(
    r"D:\LAN\tournament",
    r"D:\LAN\reports\tournament.html",
    best_of_by_series={
        "opening": BestOf.BO1,
        "semifinal": BestOf.BO3,
        "final": BestOf.BO5,
    },
    tournament_id="lan-2026",
    title="LAN 2026 / Informe del torneo",
)
print(output)
```

Open the returned file locally in a browser. CSS is embedded; there are no remote
fonts, scripts, images, JavaScript frameworks, or server requirements. The output
is UTF-8. Parent directories are created; a non-HTML suffix is replaced with
`.html`. An existing destination is overwritten. Keep reports outside series
folders for a clear separation between source data and generated artifacts.

The expected folder layout is the SCRUM-19 layout:

```text
tournament/
  opening/      # authoritative series id "opening"
    map.csv
  semifinal/    # authoritative series id "semifinal"
    map-0.csv
    map-1.csv
  final/        # authoritative series id "final"
    map-0.csv
    map-1.csv
    map-2.csv
```

Only immediate child folders are series; their immediate CSV files are maps.
`matchid` never defines a series boundary. BestOf metadata uses exact folder
names and `BestOf` enum values, not strings or guessed map counts. Missing or
invalid metadata is reported. Missing/invalid root paths propagate the existing
`TournamentFolderError`. Output I/O failures propagate normally.

## Architecture and reused APIs

- `importers.tournament_folder.import_tournament_folder` performs SCRUM-19
  validation, folder grouping, deduplication, and partial-success diagnostics.
- `application.statistics_aggregation.aggregate_tournament` supplies SCRUM-20
  global raw totals and canonical identity. SCRUM-22 internally reuses
  `aggregate_map`, `aggregate_series`, and `aggregate_tournament`.
- `application.player_rankings.rank_map`, `rank_series`, `rank_tournament`
  supply complete ordered entries, each with statistics, SCRUM-21
  `PlayerImpactResult`, component evidence, and tournament eligibility.
  SCRUM-21 impact calculation and eligibility are used through these APIs.
- `application.player_merits.generate_tournament_merits` supplies SCRUM-25
  frozen-order, single-recipient titles and their numeric evidence.
- `application.tournament_report.build_tournament_report(imported, *,
  tournament_id, title=...) -> TournamentReport` builds immutable presentation
  data from an existing `TournamentImportResult` without file I/O.
- `exporters.tournament_html.TournamentHtmlExporter.render(report) -> str`
  renders only the prepared report. `.export(report, output) -> Path` writes it.
- `generate_tournament_report(root, output, *, best_of_by_series, tournament_id,
  title=...) -> Path` composes the complete flow.

Models in `models/tournament_report.py`: `ReportMetric`, `PlayerReport`,
`LeaderboardReport`, `MapReport`, `SeriesReport`, `TournamentReport`.
They reuse domain results rather than copying/redefining statistics. Collections
are tuples and the models are frozen. `LeaderboardReport` validates that its
player sequence matches the supplied ranking exactly. Rank generation performs
its own aggregation; the extra tournament aggregate needed by merits is left
with the existing public APIs instead of changing SCRUM-22 for this ticket.

The existing team-balancing `HtmlExporterV2`, scoring and optimization contracts
are unchanged.

## Sections

1. Overview: accepted `PlayedSeries`, validated map count, tournament players,
   imported/discovered CSV counts, duplicate/invalid/series-issue counts.
2. Competitive MVP and global leaderboard: every ranked player stays visible,
   including ineligible players. Tables link to canonical player details.
3. Merit titles: exactly the SCRUM-25 output sequence; title, category, recipient,
   explanation, metric/value, and expandable raw evidence. One player may have
   several titles. Pikachu retains its SUPPORT category.
4. Accepted BO1/BO3/BO5 series: aggregate series ranking and every constituent
   map ranking, map number, matchid, and source CSV. Series impact comes from
   aggregate statistics, never averaged map impacts.
5. Every player: steamid64, aliases, teams, maps/series, all raw totals, derived
   statistics, merit titles, final impact/version, six components, component
   weights/contributions and numeric evidence.
6. Data quality: invalid CSVs, series issues, skipped duplicates with provenance,
   folders without accepted maps, pending series and their validated map results,
   and accepted CSV fingerprints.

Native HTML details and anchor links work without JavaScript. Tables scroll
horizontally on small screens; styles include visible keyboard focus, reduced
motion and print handling. Details can be expanded before printing evidence.

## MVP and merit semantics

MVP is the first entry in the unchanged tournament ranking with
`tournament_eligibility.eligible == True`. The report uses the existing boolean
and reason, without recomputing its threshold or introducing a formula. No
eligible player means MVP unavailable; an empty tournament renders normally.
Competitive MVP is separate from statistical merit titles. Losing or winning
one title does not affect another title or ranking.

Charmander remains unavailable because the CSV has no explicit
molotov/incendiary/fire damage metric. It appears only in an explanatory
unavailability note, never as an awarded title. El Alquimista uses generic
`utility_damage` and is not a fire award.

## Partial and incomplete imports

The authoritative SCRUM-20/22 tournament dataset is
`TournamentImportResult.imported_files`, **not only `result.series`**. Therefore
validated, deduplicated maps from folders with missing BestOf or invalid series
metadata still contribute to global ranking and merits, exactly as before
SCRUM-23. They are explicitly labelled and shown under diagnostics, separate
from accepted `PlayedSeries`. No statistics are fabricated from rejected CSVs.

A folder with no accepted maps is listed as empty/rejected/duplicate-only; the
report does not invent an importer error when the importer supplied none. All
original file and series issues are preserved and displayed. The overview
counts accepted series separately from the global map set.

A `PlayedSeries` with fewer maps than its BestOf limit is valid under the current
contract. The source contains no series outcome or completion flag, so the
report displays BestOf and played-map count but does not declare completion,
guess missing matches, or invent bracket results.

## Numeric display, safety and determinism

Display rounding only: impact and scalar rates use two decimals; percentages use
one decimal. The builder reads existing `PlayerStatistics` properties and marks
zero-denominator rates unavailable (`—`) rather than displaying the domain's
safe-ratio zero as an observed percentage. K/D deliberately retains SCRUM-20's
explicit finite convention `kills / max(deaths, 1)`, explained in player details.
`live_time` has unspecified units. Economy values are raw totals with no claim
about strategic quality.

Every dynamic HTML text/attribute value is escaped with `html.escape(...,
quote=True)`. Player anchors encode canonical ids as UTF-8 hex and never place
CSV text into executable contexts. All links are local fragments. There are no
runtime scripts. Component bars consume existing component scores.

Global, series and map player sequences are consumed directly from SCRUM-22;
merits directly from SCRUM-25. Series are ordered by casefolded id then id, maps
by map number; diagnostics and provenance have explicit stable sorting. There
are no current timestamps or random ids. Repeated generation from the same
input (including title and source paths) produces identical HTML. Source paths
are intentionally shown, so moving the dataset can change provenance text.

## Validation

`tests/integration/test_tournament_report.py` uses existing SCRUM-19/20 small
factories and exercises the folder-to-file flow for BO1/BO3/BO5, ranking order,
eligibility/MVP, components, all titles, multi-title players, aliases, undefined
ratios, partial imports, invalid CSVs/player counts, deduplication, escaping,
determinism, immutable report data and balanced standalone HTML structure.
No SCRUM-24 full acceptance tournament is introduced.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
git diff --check
```


## Presentación en español

El HTML usa `lang="es"` y el título predeterminado «CS2 LAN · Informe del torneo».
Las etiquetas incluyen «Resumen del torneo», «Clasificación general», «MVP del
torneo», «Premios y títulos», «Estadísticas por jugador» y «Calidad de los datos».
La navegación, columnas, estados vacíos, explicaciones, categorías y evidencia
estadística también se presentan en español. Se conservan términos habituales
como Impact, Entry, Clutch, Multikill, Headshot, K/D y BO1/BO3/BO5.

Los componentes se muestran como Combate, Aperturas / Entry, Multikill, Clutch,
Juego en equipo y Utilidad / Flash. Las traducciones pertenecen exclusivamente
al exportador: no cambian los identificadores, enumeraciones, campos, nombres de
columnas CSV, fórmulas, APIs ni títulos congelados de SCRUM-25. Las fórmulas se
presentan con etiquetas españolas sin evaluarlas de nuevo. La explicación de
elegibilidad utiliza los mapas jugados y requeridos del resultado existente.

Los nombres y rutas de origen, alias y títulos personalizados del usuario se
conservan y se escapan. Los mensajes técnicos originales del importador se
mantienen para trazabilidad, precedidos de contexto y encabezados españoles.
Las pruebas fijan etiquetas representativas y descartan los antiguos
encabezados ingleses sin depender de una instantánea de todas las frases.
