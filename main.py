from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from application.lan_balancer import (
    LanBalancer,
)
from application.results.base_report_result import (
    BaseReportResult,
)
from application.results.report_mode import (
    ReportMode,
)
from evaluation.preassigned_team_evaluator import (
    PreassignedTeamEvaluator,
)
from exporters.html_v2.html_exporter import (
    HtmlExporterV2,
)
from generators.preassigned_team_generator import (
    PreassignedTeamGenerator,
)
from generators.snake_draft_generator import (
    SnakeDraftGenerator,
)
from importers.csstats_importer import (
    CssStatsImporter,
)
from objective.objective_engine import (
    ObjectiveEngine,
)
from objective.restrictions.elo_balance_restriction import (
    EloBalanceRestriction,
)
from objective.restrictions.elo_spread_restriction import (
    EloSpreadRestriction,
)
from objective.restrictions.kd_balance_restriction import (
    KdBalanceRestriction,
)
from objective.restrictions.power_balance_restriction import (
    PowerBalanceRestriction,
)
from objective.restrictions.seed_separation_restriction import (
    SeedSeparationRestriction,
)
from objective.restrictions.team_size_restriction import (
    TeamSizeRestriction,
)
from optimizer.activity.activity_factor_model import (
    ActivityFactorModel,
)
from optimizer.evaluator.move_evaluator import (
    MoveEvaluator,
)
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
)
from optimizer.global_search.global_optimization_config import (
    GlobalOptimizationConfig,
)
from optimizer.global_search.global_optimization_result import (
    GlobalOptimizationResult,
)
from optimizer.global_search.global_optimizer import (
    GlobalOptimizer,
)
from optimizer.global_search.global_player_ordering import (
    GlobalPlayerOrdering,
)
from optimizer.global_search.global_root_builder import (
    GlobalRootBuilder,
)
from optimizer.global_search.global_search_problem import (
    GlobalSearchProblem,
)
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
)
from optimizer.local_optimizer import (
    LocalOptimizer,
)
from optimizer.modes.optimization_mode import (
    OptimizationMode,
)
from optimizer.modes.stable_optimization_config import (
    StableOptimizationConfig,
)
from optimizer.neighborhoods.swap_neighborhood import (
    SwapNeighborhood,
)
from optimizer.normalization.factory import (
    NormalizerFactory,
)
from optimizer.optimization_phase import (
    OptimizationPhase,
)
from optimizer.optimization_pipeline import (
    OptimizationPipeline,
)
from optimizer.stable.deterministic_restart_generator import (
    DeterministicRestartGenerator,
)
from optimizer.stable.solution_selector import (
    SolutionSelector,
)
from optimizer.stable.stable_optimizer import (
    StableOptimizer,
)
from optimizer.strategies.exhaustive_strategy import (
    ExhaustiveStrategy,
)
from optimizer.strategies.first_improvement_strategy import (
    FirstImprovementStrategy,
)
from scoring.attribute_score_component import (
    AttributeScoreComponent,
)
from scoring.scoring_model import (
    ScoringModel,
)
from scrapers.csv_escraper_exporter import (
    CsvScraperExporter,
)
from scrapers.faceit.faceit_api_client import (
    FaceitApiClient,
)
from scrapers.faceit.faceit_player_record_map import (
    FaceitPlayerRecordMapper,
)
from scrapers.faceit.faceit_scrapper import (
    FaceitScraper,
)

# ============================================================
# Rutas
# ============================================================

SOURCE_PLAYERS_FILE = Path(
    "data/players.csv"
)

GENERATED_STATS_FILE = Path(
    "data/players_stats.csv"
)

FACEIT_ERRORS_FILE = Path(
    "data/faceit_errors.csv"
)

OUTPUT_REPORT_FILE = Path(
    "output/lan_report.html"
)


# ============================================================
# Configuración del evento
# ============================================================

NUMBER_OF_TEAMS = 4
TEAM_SIZE = 5

EXPECTED_PLAYER_COUNT = (
    NUMBER_OF_TEAMS
    * TEAM_SIZE
)

EVENT_NAME = (
    "LAN CS2"
)

REPORT_TITLE = (
    "LAN CS2 — Análisis de equipos"
)


# ============================================================
# Configuración FACEIT
# ============================================================

RUN_FACEIT_IMPORT = True

FACEIT_PREFERRED_GAME_ID = "cs2"

FACEIT_FALLBACK_GAME_IDS = (
    "csgo",
)

FACEIT_RECENT_MATCHES = 30

FACEIT_STRICT = False

FACEIT_DELAY_SECONDS = 0.25

FACEIT_TIMEOUT_SECONDS = 20.0

FACEIT_RETRIES = 3

FACEIT_RETRY_DELAY_SECONDS = 1.0


# ============================================================
# Depuración
# ============================================================

DEBUG_PLAYERS = False
DEBUG_FINAL_TEAMS = True

# ============================================================
# Configuración de optimización
# ============================================================

# Modos disponibles:
#
#     FAST   -> generación + optimización local
#     STABLE -> múltiples restarts deterministas
#     GLOBAL -> STABLE como warm start + Branch & Bound global
#
OPTIMIZATION_MODE = (
    OptimizationMode.GLOBAL
)

STABLE_OPTIMIZATION_CONFIG = (
    StableOptimizationConfig(
        target_score=100.0,
        maximum_restarts=150,
        minimum_restarts=30,
        convergence_patience=30,
        score_tolerance=1e-6,
        base_seed=2026,
        target_confirmation_restarts=10,
        minimum_unique_solutions=20,
        maximum_total_evaluations=None,
        maximum_elapsed_seconds=None,
        stop_on_perfect_score=False,
        perfect_score=100.0,
    )
)

GLOBAL_OPTIMIZATION_CONFIG = (
    GlobalOptimizationConfig(
        maximum_nodes=500_000,
        maximum_evaluations=100_000,
        maximum_elapsed_seconds=60.0,
        score_tolerance=1e-6,
        minimum_improvement=1e-6,
        use_incumbent=True,
        use_symmetry_breaking=True,
        use_seed_pruning=True,
        use_capacity_pruning=True,
        use_power_bound=True,
        use_elo_bound=False,
        deterministic=True,
        require_proof=False,
        base_seed=2026,
    )
)


# ============================================================
# Scoring individual
# ============================================================

def create_scoring_model() -> ScoringModel:
    """
    Construye el modelo de Power Score individual.

    Cada AttributeScoreComponent devuelve una puntuación
    normalizada entre 0 y 100.

    ScoringModel combina posteriormente los componentes
    utilizando sus pesos relativos.
    """

    components = [
        AttributeScoreComponent(
            name="ELO",
            attribute="elo",
            normalizer=NormalizerFactory.logistic(
                midpoint=1800.0,
                steepness=-0.003,
            ),
            default_score=0.0,
        ),
        AttributeScoreComponent(
            name="KD",
            attribute="kd",
            normalizer=NormalizerFactory.logistic(
                midpoint=1.00,
                steepness=-8.0,
            ),
            default_score=0.0,
        ),
        AttributeScoreComponent(
            name="ADR",
            attribute="adr",
            normalizer=NormalizerFactory.logistic(
                midpoint=75.0,
                steepness=-0.10,
            ),
            default_score=0.0,
        ),
        AttributeScoreComponent(
            name="KPR",
            attribute="kpr",
            normalizer=NormalizerFactory.logistic(
                midpoint=0.70,
                steepness=-12.0,
            ),
            default_score=0.0,
        ),
        AttributeScoreComponent(
            name="Winrate",
            attribute="winrate",
            normalizer=NormalizerFactory.logistic(
                midpoint=50.0,
                steepness=-0.12,
            ),
            default_score=0.0,
        ),
        AttributeScoreComponent(
            name="HS",
            attribute="hs",
            normalizer=NormalizerFactory.logistic(
                midpoint=45.0,
                steepness=-0.08,
            ),
            default_score=0.0,
        ),
    ]

    weights = {
        "ELO": 40.0,
        "KD": 25.0,
        "ADR": 15.0,
        "KPR": 10.0,
        "Winrate": 7.0,
        "HS": 3.0,
    }

    return ScoringModel(
        components=components,
        weights=weights,
        minimum_available_weight=40.0,
        default_power=0.0,
        activity_factor_model=(
            ActivityFactorModel()
        ),
    )


# ============================================================
# Objective Engine
# ============================================================

def create_objective_engine(
    scoring_model: ScoringModel,
) -> ObjectiveEngine:
    """
    Construye el motor de evaluación global.

    Distribución actual de pesos:

        Power Balance:       55 %
        ELO Balance:         10 %
        ELO Spread:           5 %
        KD Balance:          20 %
        Team Size:            9 %
        Seed Separation:      1 %

        Total:              100 %
    """

    restrictions = [
        PowerBalanceRestriction(
            scoring_model=scoring_model,
            weight=55.0,
        ),

        EloBalanceRestriction(
            weight=10.0,
        ),

        EloSpreadRestriction(
            weight=5.0,
        ),

        KdBalanceRestriction(
            weight=20.0,
            max_deviation=0.35,
        ),

        TeamSizeRestriction(
            expected_size=TEAM_SIZE,
            weight=9.0,
        ),

        SeedSeparationRestriction(
            seed_level=1,
            maximum_per_team=1,
            penalty_per_excess_player=100.0,
            maximum_penalty=100.0,
            weight=1.0,
        ),
    ]

    return ObjectiveEngine(
        restrictions=restrictions,
    )


# ============================================================
# Pipeline de optimización
# ============================================================

def create_pipeline() -> OptimizationPipeline:
    """
    Pipeline estable del optimizador.

    Primera fase:
        busca rápidamente mejoras mediante swaps.

    Segunda fase:
        realiza una búsqueda exhaustiva final sobre swaps.

    En este punto no se utilizan movimientos que puedan empeorar
    deliberadamente la solución.
    """

    return (
        OptimizationPipeline()

        .add(
            OptimizationPhase(
                name="Quick Swap Improvement",
                neighborhood=SwapNeighborhood(),
                strategy=FirstImprovementStrategy(
                    minimum_improvement=0.01,
                ),
                max_iterations=100,
                enabled=True,
                stop_when_no_move=True,
            )
        )

        .add(
            OptimizationPhase(
                name="Final Swap Polish",
                neighborhood=SwapNeighborhood(),
                strategy=ExhaustiveStrategy(
                    minimum_improvement=0.01,
                ),
                max_iterations=30,
                enabled=True,
                stop_when_no_move=True,
            )
        )
    )


# ============================================================
# Construcción de la aplicación
# ============================================================

def create_balancer(
    scoring_model: ScoringModel,
    objective_engine: ObjectiveEngine | None = None,
) -> LanBalancer:
    """
    Construye la fachada completa de la aplicación.

    PREASSIGNED:
        Evalúa exactamente los equipos definidos por CSV.Team.

    OPTIMIZED + FAST:
        SnakeDraftGenerator
            ↓
        LocalOptimizer

    OPTIMIZED + STABLE:
        SnakeDraftGenerator
            ↓
        StableOptimizer
            ↓
        múltiples restarts deterministas
            ↓
        una única solución seleccionada de forma reproducible

    OPTIMIZED + GLOBAL:
        LanBalancer ejecuta internamente STABLE para obtener el warm start.
        El Branch & Bound GLOBAL se ejecuta después en main().
    """
    if objective_engine is None:
        objective_engine = create_objective_engine(
            scoring_model=scoring_model,
        )

    move_evaluator = MoveEvaluator(
        objective=objective_engine,
    )

    local_optimizer = LocalOptimizer(
        evaluator=move_evaluator,
        pipeline=create_pipeline(),
    )

    restart_generator = (
        DeterministicRestartGenerator(
            separated_seed_level=1,
            maximum_seeded_players_per_team=1,
            minimum_swaps=1,
            maximum_swaps=6,
            partial_redistribution_ratio=0.50,
        )
    )

    stable_selector = SolutionSelector(
        config=(
            STABLE_OPTIMIZATION_CONFIG
        )
    )

    stable_optimizer = StableOptimizer(
        local_optimizer=(
            local_optimizer
        ),
        restart_factory=(
            restart_generator
        ),
        config=(
            STABLE_OPTIMIZATION_CONFIG
        ),
        selector=(
            stable_selector
        ),
    )

    return LanBalancer(
        importer=CssStatsImporter(
            strict=True,
        ),

        generator=SnakeDraftGenerator(
            scoring_model=scoring_model,
            team_name_prefix="Equipo",
            separated_seed_level=1,
            maximum_seeded_players_per_team=1,
        ),

        optimizer=local_optimizer,

        preassigned_generator=PreassignedTeamGenerator(
            expected_team_size=TEAM_SIZE,
            expected_player_count=EXPECTED_PLAYER_COUNT,
            team_name_prefix="Equipo",
            require_all_teams=True,
        ),

        preassigned_evaluator=PreassignedTeamEvaluator(
            objective_engine=objective_engine,
            title=(
                "Evaluación de equipos predeterminados"
            ),
        ),

        exporter=HtmlExporterV2(
            scoring_model=scoring_model,
            title=REPORT_TITLE,
        ),

        optimization_mode=(
            OptimizationMode.STABLE
            if OPTIMIZATION_MODE
            is OptimizationMode.GLOBAL
            else OPTIMIZATION_MODE
        ),

        stable_optimizer=(
            stable_optimizer
        ),
    )


# ============================================================
# Adaptador de resultado GLOBAL para informes
# ============================================================

class GlobalReportResult(BaseReportResult):
    """
    Adapta GlobalOptimizationResult al contrato BaseReportResult.

    Esto permite que HtmlExporterV2 y el resto de la capa de informe
    trabajen directamente con la solución GLOBAL sin depender de un
    OptimizationHistory basado en movimientos locales.
    """

    __slots__ = (
        "_initial_score",
        "_global_result",
    )

    def __init__(
        self,
        teams,
        objective_result,
        initial_score: float,
        global_result: GlobalOptimizationResult,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._initial_score = float(
            initial_score
        )

        self._global_result = (
            global_result
        )

        super().__init__(
            teams=teams,
            objective_result=objective_result,
            title=title,
            metadata=(
                dict(metadata)
                if metadata is not None
                else {}
            ),
        )

    @property
    def mode(self) -> ReportMode:
        return ReportMode.OPTIMIZED

    @property
    def initial_score(self) -> float:
        return self._initial_score

    @property
    def final_score(self) -> float:
        return float(
            self.objective_result.score
        )

    @property
    def score(self) -> float:
        return self.final_score

    @property
    def improvement(self) -> float:
        return (
            self.final_score
            - self.initial_score
        )

    @property
    def iterations(self) -> int:
        # GLOBAL no acepta movimientos locales.
        return 0

    @property
    def total_evaluations(self) -> int:
        return int(
            self._global_result
            .complete_solutions_evaluated
        )

    @property
    def elapsed_ms(self) -> float:
        return (
            float(
                self._global_result
                .elapsed_seconds
            )
            * 1000.0
        )

    @property
    def optimized(self) -> bool:
        return True

    @property
    def evaluation_only(self) -> bool:
        return False

    @property
    def history(self) -> tuple:
        # No existe historial de SwapMove en Branch & Bound.
        return tuple()

    @property
    def optimization_engine(self) -> str:
        return "GLOBAL"

    @property
    def optimality_proven(self) -> bool:
        return bool(
            self._global_result.optimality_proven
        )

    @property
    def nodes_visited(self) -> int:
        return int(
            self._global_result.nodes_visited
        )

    @property
    def complete_solutions_evaluated(self) -> int:
        return int(
            self._global_result.complete_solutions_evaluated
        )

    @property
    def pruned_nodes(self) -> int:
        return int(
            self._global_result.pruned_nodes
        )

    @property
    def bound_prunes(self) -> int:
        return int(
            self._global_result.bound_prunes
        )

    @property
    def global_stop_reason(self) -> str:
        return str(
            self._global_result.stop_reason
        )

    @property
    def search_exhausted(self) -> bool:
        return (
            self.global_stop_reason
            == "SEARCH_EXHAUSTED"
        )


# ============================================================
# GLOBAL - construcción del problema
# ============================================================

def create_global_metrics(
    players: Iterable[Any],
    scoring_model: ScoringModel,
) -> tuple[GlobalPlayerMetrics, ...]:
    metrics: list[GlobalPlayerMetrics] = []

    for player in players:
        elo = get_player_attribute(
            player,
            "elo",
            "faceit_elo",
        )

        kd = get_player_attribute(
            player,
            "kd",
        )

        seed = getattr(
            player,
            "seed",
            None,
        )

        if elo is None:
            raise ValueError(
                f"{get_player_nickname(player)} no contiene ELO."
            )

        if kd is None:
            raise ValueError(
                f"{get_player_nickname(player)} no contiene KD."
            )

        metrics.append(
            GlobalPlayerMetrics(
                player=player,
                power=float(
                    scoring_model.power(
                        player
                    )
                ),
                elo=float(elo),
                kd=float(kd),
                seed=(
                    int(seed)
                    if seed is not None
                    else None
                ),
            )
        )

    return tuple(
        metrics
    )


def create_global_problem(
    players: Iterable[Any],
    scoring_model: ScoringModel,
) -> GlobalSearchProblem:
    metrics = create_global_metrics(
        players=players,
        scoring_model=scoring_model,
    )

    ordering = GlobalPlayerOrdering(
        protected_seed_level=1,
    )

    builder = GlobalRootBuilder(
        number_of_teams=NUMBER_OF_TEAMS,
        team_size=TEAM_SIZE,
        protected_seed_level=1,
        maximum_protected_seeds_per_team=1,
    )

    return builder.build(
        players=metrics,
        ordering=ordering,
    )


def create_global_optimizer(
    objective_engine: ObjectiveEngine,
) -> GlobalOptimizer:
    """
    Construye el Branch & Bound GLOBAL.

    Los pesos deben coincidir exactamente con create_objective_engine().
    Solo Power aporta actualmente una cota blanda real; ELO/KD se
    mantienen optimistas a 100 durante la poda.
    """

    bound_calculator = (
        GlobalBoundCalculator(
            power_weight=55.0,
            elo_balance_weight=10.0,
            elo_spread_weight=5.0,
            kd_weight=20.0,
            team_size_weight=9.0,
            seed_weight=1.0,
            score_tolerance=1e-6,
        )
    )

    return GlobalOptimizer(
        objective_engine=objective_engine,
        config=GLOBAL_OPTIMIZATION_CONFIG,
        bound_calculator=(
            bound_calculator
        ),
    )


def run_global_optimization(
    players: Iterable[Any],
    scoring_model: ScoringModel,
    objective_engine: ObjectiveEngine,
    stable_result: BaseReportResult,
) -> tuple[
    GlobalReportResult,
    GlobalOptimizationResult,
]:
    """
    Ejecuta GLOBAL utilizando la solución STABLE como incumbent.
    """

    problem = create_global_problem(
        players=players,
        scoring_model=scoring_model,
    )

    optimizer = create_global_optimizer(
        objective_engine=objective_engine,
    )

    global_result = optimizer.optimize(
        problem=problem,
        incumbent_teams=(
            stable_result.teams
        ),
        incumbent_score=(
            stable_result.final_score
        ),
    )

    # Re-evaluación final con la autoridad real del ObjectiveEngine.
    objective_result = (
        objective_engine.evaluate(
            global_result.teams
        )
    )

    if abs(
        float(objective_result.score)
        - float(global_result.score)
    ) > GLOBAL_OPTIMIZATION_CONFIG.score_tolerance:
        raise RuntimeError(
            "GLOBAL devolvió un score inconsistente con "
            "ObjectiveEngine. "
            f"GLOBAL={global_result.score:.8f}, "
            f"ObjectiveEngine={objective_result.score:.8f}."
        )

    metadata = dict(
        getattr(
            stable_result,
            "metadata",
            {},
        )
    )

    metadata["optimization_applied"] = True
    metadata["optimization_mode"] = (
        OptimizationMode.GLOBAL.value
    )
    metadata["optimization_mode_label"] = (
        OptimizationMode.GLOBAL.label
    )
    metadata["optimization_deterministic"] = (
        OptimizationMode.GLOBAL.deterministic
    )

    metadata["global_optimization"] = {
        "initial_incumbent_score": (
            global_result
            .initial_incumbent_score
        ),
        "final_score": global_result.score,
        "improvement": (
            global_result.improvement
        ),
        "nodes_visited": (
            global_result.nodes_visited
        ),
        "complete_solutions_evaluated": (
            global_result
            .complete_solutions_evaluated
        ),
        "pruned_nodes": (
            global_result.pruned_nodes
        ),
        "capacity_prunes": (
            global_result.capacity_prunes
        ),
        "seed_prunes": (
            global_result.seed_prunes
        ),
        "bound_prunes": (
            global_result.bound_prunes
        ),
        "elapsed_seconds": (
            global_result.elapsed_seconds
        ),
        "optimality_proven": (
            global_result.optimality_proven
        ),
        "stopped_by_limit": (
            global_result.stopped_by_limit
        ),
        "stop_reason": (
            global_result.stop_reason
        ),
    }

    report_result = GlobalReportResult(
        teams=global_result.teams,
        objective_result=objective_result,
        initial_score=(
            global_result
            .initial_incumbent_score
        ),
        global_result=global_result,
        title=REPORT_TITLE,
        metadata=metadata,
    )

    return (
        report_result,
        global_result,
    )


def print_global_optimization(
    result: GlobalOptimizationResult,
) -> None:
    print()
    print("=" * 72)
    print("OPTIMIZACIÓN GLOBAL")
    print("=" * 72)

    print(
        f"Incumbent inicial:      "
        f"{result.initial_incumbent_score:.4f}"
    )

    print(
        f"Score final:            "
        f"{result.score:.4f}"
    )

    print(
        f"Mejora GLOBAL:          "
        f"{result.improvement:+.4f}"
    )

    print(
        f"Nodos explorados:       "
        f"{result.nodes_visited:,}"
    )

    print(
        f"Soluciones evaluadas:   "
        f"{result.complete_solutions_evaluated:,}"
    )

    print(
        f"Ramas podadas:          "
        f"{result.pruned_nodes:,}"
    )

    print(
        f"  Capacidad:            "
        f"{result.capacity_prunes:,}"
    )

    print(
        f"  Seeds:                "
        f"{result.seed_prunes:,}"
    )

    print(
        f"  Bound / Power:        "
        f"{result.bound_prunes:,}"
    )

    print(
        f"Tiempo GLOBAL:          "
        f"{format_elapsed_seconds(result.elapsed_seconds)}"
    )

    print(
        f"Límite alcanzado:       "
        f"{'SÍ' if result.stopped_by_limit else 'NO'}"
    )

    print(
        f"Espacio agotado:        "
        f"{'SÍ' if result.stop_reason == 'SEARCH_EXHAUSTED' else 'NO'}"
    )

    print(
        f"Óptimo demostrado:      "
        f"{'SÍ' if result.optimality_proven else 'NO'}"
    )

    print(
        f"Motivo de parada:       "
        f"{result.stop_reason}"
    )


# ============================================================
# FACEIT API key
# ============================================================

def get_faceit_api_key() -> str:
    """
    Obtiene la API key de FACEIT desde la variable de entorno
    FACEIT_API_KEY.
    """

    api_key = os.environ.get(
        "FACEIT_API_KEY"
    )

    if api_key is None:
        raise RuntimeError(
            "La variable de entorno FACEIT_API_KEY "
            "no está definida."
        )

    normalized = api_key.strip()

    if not normalized:
        raise RuntimeError(
            "La variable de entorno FACEIT_API_KEY "
            "está vacía."
        )

    return normalized


# ============================================================
# Importación FACEIT
# ============================================================

def run_faceit_import() -> Path:
    """
    Consulta FACEIT para todos los jugadores del CSV inicial.

    El CSV de entrada contiene la configuración manual:

        Nick
        FaceitNickname
        Seed
        Team

    El scraper y CsvScraperExporter deben conservar Seed y Team
    durante todo el proceso para que el CSV generado pueda utilizarse
    posteriormente tanto en modo automático como preasignado.
    """

    if not SOURCE_PLAYERS_FILE.exists():
        raise FileNotFoundError(
            "No existe el archivo de entrada: "
            f"{SOURCE_PLAYERS_FILE.resolve()}"
        )

    api_key = get_faceit_api_key()

    print()
    print("=" * 72)
    print(
        "IMPORTACIÓN DE JUGADORES DESDE FACEIT"
    )
    print("=" * 72)

    print(
        f"Entrada:              "
        f"{SOURCE_PLAYERS_FILE}"
    )

    print(
        f"Juego preferido:      "
        f"{FACEIT_PREFERRED_GAME_ID}"
    )

    print(
        "Juegos fallback:      "
        f"{', '.join(FACEIT_FALLBACK_GAME_IDS)}"
    )

    print(
        f"Partidas recientes:   "
        f"{FACEIT_RECENT_MATCHES}"
    )

    print()

    with FaceitApiClient(
        api_key=api_key,
        preferred_game_id=(
            FACEIT_PREFERRED_GAME_ID
        ),
        fallback_game_ids=(
            FACEIT_FALLBACK_GAME_IDS
        ),
        timeout=FACEIT_TIMEOUT_SECONDS,
        retries=FACEIT_RETRIES,
        retry_delay=(
            FACEIT_RETRY_DELAY_SECONDS
        ),
    ) as client:

        mapper = FaceitPlayerRecordMapper(
            game_id=FACEIT_PREFERRED_GAME_ID,
            source_name="FACEIT",
        )

        scraper = FaceitScraper(
            client=client,
            mapper=mapper,
            recent_matches=FACEIT_RECENT_MATCHES,
            strict=FACEIT_STRICT,
            delay=FACEIT_DELAY_SECONDS,
            maximum_seed_one_players=(
                NUMBER_OF_TEAMS
            ),
        )

        records = scraper.scrape(
            SOURCE_PLAYERS_FILE
        )

        scraper_errors = (
            scraper.errors
        )

    valid_records = [
        record
        for record in records
        if record.is_valid
    ]

    failed_records = [
        record
        for record in records
        if not record.is_valid
    ]

    print(
        f"Jugadores esperados:  "
        f"{EXPECTED_PLAYER_COUNT}"
    )

    print(
        f"Jugadores válidos:    "
        f"{len(valid_records)}"
    )

    print(
        f"Jugadores con error:  "
        f"{len(failed_records)}"
    )

    if failed_records:
        print()
        print(
            "JUGADORES CON ERROR"
        )
        print("-" * 72)

        for record in failed_records:
            print(
                f"- {record.nickname}: "
                f"{record.error or 'Error desconocido'}"
            )

        CsvScraperExporter(
            include_errors=True,
        ).export(
            records=failed_records,
            output=FACEIT_ERRORS_FILE,
        )

        print()

        print(
            "Errores guardados en: "
            f"{FACEIT_ERRORS_FILE.resolve()}"
        )

    if scraper_errors:
        print()
        print(
            "DETALLE TÉCNICO"
        )
        print("-" * 72)

        for error in scraper_errors:
            print(
                f"Fila {error.get('row')}: "
                f"{error.get('nick')} / "
                f"{error.get('faceit_nickname')} -> "
                f"{error.get('error')}"
            )

    if (
        len(valid_records)
        != EXPECTED_PLAYER_COUNT
    ):
        raise RuntimeError(
            "El número de jugadores válidos no coincide "
            "con el esperado. "
            f"Esperados: {EXPECTED_PLAYER_COUNT}. "
            f"Obtenidos: {len(valid_records)}."
        )

    generated_file = CsvScraperExporter(
        include_errors=False,
    ).export(
        records=valid_records,
        output=GENERATED_STATS_FILE,
    )

    print()

    print(
        "CSV de estadísticas generado: "
        f"{generated_file.resolve()}"
    )

    return generated_file


def resolve_players_file() -> Path:
    """
    Devuelve el CSV que debe utilizar la aplicación.

    Cuando RUN_FACEIT_IMPORT=True se regeneran primero las
    estadísticas.

    Cuando es False se reutiliza players_stats.csv.
    """

    if RUN_FACEIT_IMPORT:
        return run_faceit_import()

    if not GENERATED_STATS_FILE.exists():
        raise FileNotFoundError(
            "No existe el archivo generado: "
            f"{GENERATED_STATS_FILE.resolve()}"
        )

    return GENERATED_STATS_FILE


# ============================================================
# Identidad de jugadores
# ============================================================

def get_player_attribute(
    player: Any,
    primary: str,
    alternative: str | None = None,
) -> Any:
    """
    Obtiene un atributo contemplando un nombre alternativo.
    """

    value = getattr(
        player,
        primary,
        None,
    )

    if (
        value is None
        and alternative is not None
    ):
        value = getattr(
            player,
            alternative,
            None,
        )

    return value


def get_player_nickname(
    player: Any,
) -> str:
    """
    Nick mostrado del jugador.
    """

    return str(
        get_player_attribute(
            player,
            "nickname",
            "nick",
        )
        or "Unknown"
    )


def get_player_identity(
    player: Any,
) -> str:
    """
    Construye una identidad estable.

    Prioridad:

        1. player.identity
        2. Steam ID
        3. nickname
    """

    identity = getattr(
        player,
        "identity",
        None,
    )

    if identity:
        return (
            str(identity)
            .strip()
            .casefold()
        )

    steam_id = get_player_attribute(
        player,
        "steam_id",
    )

    if steam_id:
        return (
            "steam:"
            f"{str(steam_id).strip().casefold()}"
        )

    nickname = get_player_nickname(
        player
    )

    return (
        "nick:"
        f"{nickname.strip().casefold()}"
    )


# ============================================================
# Validación de jugadores de entrada
# ============================================================

def validate_players(
    players: Iterable[Any],
    expected_player_count: int,
) -> None:
    """
    Verifica la colección de jugadores antes de ejecutar el
    balanceador.
    """

    player_list = list(
        players
    )

    if (
        len(player_list)
        != expected_player_count
    ):
        raise RuntimeError(
            f"Se han importado {len(player_list)} jugadores. "
            f"Se esperaban {expected_player_count}."
        )

    object_ids = [
        id(player)
        for player in player_list
    ]

    if (
        len(object_ids)
        != len(set(object_ids))
    ):
        raise RuntimeError(
            "La colección de entrada contiene instancias "
            "de Player duplicadas."
        )

    identities = [
        get_player_identity(
            player
        )
        for player in player_list
    ]

    duplicated = [
        identity
        for identity, count
        in Counter(
            identities
        ).items()
        if count > 1
    ]

    if duplicated:
        raise RuntimeError(
            "La colección de entrada contiene jugadores "
            "duplicados: "
            f"{duplicated}."
        )


# ============================================================
# Validación estructural de equipos
# ============================================================

def validate_teams(
    teams: Iterable[Any],
    expected_team_size: int,
    expected_player_count: int,
    stage: str,
) -> None:
    """
    Comprueba:

        - Número de equipos.
        - Tamaño de cada equipo.
        - Número total de jugadores.
        - Instancias duplicadas.
        - Identidades duplicadas.
    """

    team_list = list(
        teams
    )

    if (
        len(team_list)
        != NUMBER_OF_TEAMS
    ):
        raise RuntimeError(
            f"[{stage}] Se esperaban "
            f"{NUMBER_OF_TEAMS} equipos, "
            f"pero existen {len(team_list)}."
        )

    object_locations: dict[
        int,
        list[str],
    ] = {}

    identity_locations: dict[
        str,
        list[str],
    ] = {}

    total_players = 0

    for team_index, team in enumerate(
        team_list,
        start=1,
    ):
        team_name = (
            getattr(
                team,
                "name",
                None,
            )
            or f"Equipo {team_index}"
        )

        players = list(
            getattr(
                team,
                "players",
                (),
            )
        )

        if (
            len(players)
            != expected_team_size
        ):
            raise RuntimeError(
                f"[{stage}] {team_name} contiene "
                f"{len(players)} jugadores. "
                f"Se esperaban {expected_team_size}."
            )

        total_players += len(
            players
        )

        for player_index, player in enumerate(
            players,
            start=1,
        ):
            location = (
                f"{team_name}[{player_index}]"
            )

            object_locations.setdefault(
                id(player),
                [],
            ).append(
                location
            )

            identity_locations.setdefault(
                get_player_identity(
                    player
                ),
                [],
            ).append(
                location
            )

    if (
        total_players
        != expected_player_count
    ):
        raise RuntimeError(
            f"[{stage}] Existen "
            f"{total_players} posiciones de jugadores. "
            f"Se esperaban {expected_player_count}."
        )

    duplicated_objects = {
        object_id: locations
        for object_id, locations
        in object_locations.items()
        if len(locations) > 1
    }

    duplicated_identities = {
        identity: locations
        for identity, locations
        in identity_locations.items()
        if len(locations) > 1
    }

    if duplicated_objects:
        details = "; ".join(
            (
                f"object_id={object_id}: "
                f"{', '.join(locations)}"
            )
            for object_id, locations
            in duplicated_objects.items()
        )

        raise RuntimeError(
            f"[{stage}] Se han detectado instancias "
            f"de Player repetidas. {details}"
        )

    if duplicated_identities:
        details = "; ".join(
            (
                f"{identity}: "
                f"{', '.join(locations)}"
            )
            for identity, locations
            in duplicated_identities.items()
        )

        raise RuntimeError(
            f"[{stage}] Se han detectado jugadores "
            f"duplicados por identidad. {details}"
        )


def validate_same_player_collection(
    players_before: Iterable[Any],
    teams_after: Iterable[Any],
) -> None:
    """
    Garantiza que el proceso conserva exactamente la misma
    colección lógica de jugadores.
    """

    before_counter = Counter(
        get_player_identity(
            player
        )
        for player in players_before
    )

    after_counter = Counter(
        get_player_identity(
            player
        )
        for team in teams_after
        for player in team.players
    )

    if (
        before_counter
        == after_counter
    ):
        return

    missing = (
        before_counter
        - after_counter
    )

    unexpected = (
        after_counter
        - before_counter
    )

    raise RuntimeError(
        "El proceso ha modificado la colección de jugadores. "
        f"Ausentes: {dict(missing)}. "
        f"Inesperados: {dict(unexpected)}."
    )


# ============================================================
# Validación específica por modo
# ============================================================

def validate_result(
    result: BaseReportResult,
    players: Iterable[Any],
) -> None:
    """
    Ejecuta las validaciones comunes y específicas del modo.
    """

    if not isinstance(
        result,
        BaseReportResult,
    ):
        raise TypeError(
            "result must be a BaseReportResult instance."
        )

    validate_teams(
        teams=result.teams,
        expected_team_size=TEAM_SIZE,
        expected_player_count=(
            EXPECTED_PLAYER_COUNT
        ),
        stage="Resultado",
    )

    validate_same_player_collection(
        players_before=players,
        teams_after=result.teams,
    )

    if (
        result.mode
        is ReportMode.OPTIMIZED
    ):
        if (
            result.final_score
            < result.initial_score
        ):
            raise RuntimeError(
                "La optimización ha terminado con una "
                "puntuación inferior a la inicial. "
                f"Inicial: {result.initial_score:.2f}. "
                f"Final: {result.final_score:.2f}."
            )

    elif (
        result.mode
        is ReportMode.PREASSIGNED
    ):
        validate_preassigned_result(
            result
        )


def validate_preassigned_result(
    result: BaseReportResult,
) -> None:
    """
    Comprueba que la composición final coincide con los Team
    indicados en cada Player.
    """

    errors: list[str] = []

    for team_index, team in enumerate(
        result.teams,
        start=1,
    ):
        team_id = getattr(
            team,
            "id",
            team_index,
        )

        for player in team.players:
            assigned_team = getattr(
                player,
                "team_number",
                getattr(
                    player,
                    "assigned_team_number",
                    None,
                ),
            )

            if assigned_team is None:
                errors.append(
                    f"{get_player_nickname(player)} "
                    "no contiene Team."
                )

                continue

            try:
                assigned_team_value = int(
                    assigned_team
                )

            except (
                TypeError,
                ValueError,
            ):
                errors.append(
                    f"{get_player_nickname(player)} "
                    f"contiene Team={assigned_team!r}."
                )

                continue

            try:
                actual_team_value = int(
                    team_id
                )

            except (
                TypeError,
                ValueError,
            ):
                actual_team_value = (
                    team_index
                )

            if (
                assigned_team_value
                != actual_team_value
            ):
                errors.append(
                    f"{get_player_nickname(player)} "
                    f"tiene Team={assigned_team_value}, "
                    f"pero aparece en "
                    f"Equipo {actual_team_value}."
                )

    if errors:
        raise RuntimeError(
            "La evaluación preasignada no ha conservado "
            "correctamente los equipos: "
            + " | ".join(errors)
        )


# ============================================================
# Información del modo
# ============================================================

def print_mode(
    mode: ReportMode,
) -> None:
    """
    Muestra por consola qué flujo va a ejecutarse.
    """

    print()
    print("=" * 72)
    print(
        "MODO DE EJECUCIÓN"
    )
    print("=" * 72)

    print(
        f"Modo:                 "
        f"{mode.value}"
    )

    print(
        f"Descripción:          "
        f"{mode.label}"
    )

    if mode is ReportMode.PREASSIGNED:
        print(
            "Acción:               "
            "Evaluar equipos del CSV"
        )

        print(
            "Optimización:         "
            "NO"
        )

    else:
        print(
            "Acción:               "
            "Generar y optimizar equipos"
        )

        print(
            "Optimización:         "
            "SÍ"
        )

        print(
            "Motor:                "
            f"{OPTIMIZATION_MODE.value.upper()}"
        )


# ============================================================
# Depuración de jugadores
# ============================================================

def print_players_debug(
    players: Iterable[Any],
) -> None:
    """
    Muestra los datos básicos importados.
    """

    print()
    print("=" * 72)
    print(
        "JUGADORES IMPORTADOS"
    )
    print("=" * 72)

    for index, player in enumerate(
        players,
        start=1,
    ):
        nickname = get_player_nickname(
            player
        )

        team_number = getattr(
            player,
            "team_number",
            None,
        )

        seed = getattr(
            player,
            "seed",
            None,
        )

        print(
            f"[{index:02d}] "
            f"{nickname:<20} "
            f"| Team: "
            f"{str(team_number or '—'):<3} "
            f"| Seed: "
            f"{str(seed or '—'):<3} "
            f"| identity="
            f"{get_player_identity(player)!r}"
        )


# ============================================================
# Depuración de equipos
# ============================================================

def print_team_debug(
    teams: Iterable[Any],
    title: str,
) -> None:
    """
    Muestra la composición de los equipos.
    """

    print()
    print("=" * 72)
    print(
        title
    )
    print("=" * 72)

    for team_index, team in enumerate(
        teams,
        start=1,
    ):
        team_name = (
            getattr(
                team,
                "name",
                None,
            )
            or f"Equipo {team_index}"
        )

        print()
        print(
            str(team_name).upper()
        )
        print("-" * 72)

        for player_index, player in enumerate(
            team.players,
            start=1,
        ):
            nickname = get_player_nickname(
                player
            )

            assigned_team = getattr(
                player,
                "team_number",
                None,
            )

            print(
                f"[{player_index}] "
                f"{nickname:<20} "
                f"| Team CSV: "
                f"{str(assigned_team or '—'):<3} "
                f"| identity="
                f"{get_player_identity(player)!r}"
            )


# ============================================================
# Diagnóstico STABLE
# ============================================================

def format_confidence(
    value: Any,
) -> str:
    normalized = (
        str(value or "UNKNOWN")
        .strip()
        .upper()
    )

    labels = {
        "NONE": "SIN DATOS",
        "LOW": "BAJA",
        "MEDIUM": "MEDIA",
        "HIGH": "ALTA",
        "VERY_HIGH": "MUY ALTA",
        "UNKNOWN": "DESCONOCIDA",
    }

    return labels.get(
        normalized,
        normalized.replace(
            "_",
            " ",
        ),
    )


def format_stop_reason(
    value: Any,
) -> str:
    if value is None:
        return "DESCONOCIDO"

    normalized = (
        str(value)
        .strip()
        .casefold()
    )

    labels = {
        "perfect_score": "PUNTUACIÓN PERFECTA",
        "target_confirmed": "TARGET CONFIRMADO",
        "convergence": "CONVERGENCIA",
        "restart_limit": "LÍMITE DE RESTARTS",
        "evaluation_limit": "LÍMITE DE EVALUACIONES",
        "elapsed_limit": "LÍMITE DE TIEMPO",
    }

    return labels.get(
        normalized,
        normalized.upper().replace(
            "_",
            " ",
        ),
    )


def format_restart_number(
    value: Any,
) -> str:
    if value is None:
        return "—"

    try:
        return str(
            int(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"


def format_elapsed_seconds(
    value: Any,
) -> str:
    try:
        seconds = max(
            0.0,
            float(value),
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"

    if seconds < 1.0:
        return (
            f"{seconds * 1000.0:.2f} ms"
        )

    if seconds < 60.0:
        return (
            f"{seconds:.2f} s"
        )

    minutes = int(
        seconds // 60.0
    )

    remaining_seconds = (
        seconds
        - minutes * 60.0
    )

    return (
        f"{minutes} min "
        f"{remaining_seconds:.1f} s"
    )


def print_stable_optimization(
    result: BaseReportResult,
) -> None:
    metadata = getattr(
        result,
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        return

    stable_data = metadata.get(
        "stable_optimization"
    )

    if not isinstance(
        stable_data,
        dict,
    ):
        return

    convergence = stable_data.get(
        "convergence",
        {},
    )

    if not isinstance(
        convergence,
        dict,
    ):
        convergence = {}

    signature = stable_data.get(
        "signature",
        {},
    )

    if not isinstance(
        signature,
        dict,
    ):
        signature = {}

    print()
    print("=" * 72)
    print("OPTIMIZACIÓN ESTABLE")
    print("=" * 72)

    score = stable_data.get(
        "score"
    )

    if score is not None:
        print(
            f"Score seleccionado:    "
            f"{float(score):.4f}"
        )

    penalty = stable_data.get(
        "penalty"
    )

    if penalty is not None:
        print(
            f"Penalización:          "
            f"{float(penalty):.2f}"
        )

    print(
        f"Confianza:             "
        f"{format_confidence(stable_data.get('confidence'))}"
    )

    print(
        f"Restarts completados:  "
        f"{stable_data.get('completed_restarts', 0)}"
    )

    print(
        f"Soluciones únicas:     "
        f"{stable_data.get('unique_solutions', 0)}"
    )

    print(
        f"Mejor encontrada en:   "
        f"{format_restart_number(stable_data.get('best_restart_number'))}"
    )

    print(
        f"Sin mejora:            "
        f"{convergence.get('restarts_without_improvement', 0)}"
    )

    print(
        f"Mejoras reales:        "
        f"{stable_data.get('quality_improvements', 0)}"
    )

    print(
        f"Cambios selección:     "
        f"{stable_data.get('selection_changes', 0)}"
    )

    print(
        f"Evaluaciones globales: "
        f"{convergence.get('total_evaluations', 0)}"
    )

    print(
        f"Target alcanzado:      "
        f"{'SÍ' if stable_data.get('target_reached', False) else 'NO'}"
    )

    print(
        f"Target confirmado:     "
        f"{'SÍ' if stable_data.get('target_confirmed', False) else 'NO'}"
    )

    print(
        f"Motivo de parada:      "
        f"{format_stop_reason(stable_data.get('stop_reason'))}"
    )

    print(
        f"Tiempo total STABLE:   "
        f"{format_elapsed_seconds(stable_data.get('elapsed_seconds', 0.0))}"
    )

    signature_hash = signature.get(
        "hash"
    )

    if signature_hash:
        print(
            f"Firma solución:        "
            f"{signature_hash}"
        )


def print_objective_breakdown(
    result: BaseReportResult,
) -> None:
    restrictions = getattr(
        result,
        "restrictions",
        {},
    )

    print()
    print("=" * 72)
    print("DESGLOSE DEL OBJECTIVE ENGINE")
    print("=" * 72)

    if not restrictions:
        print(
            "No hay restricciones disponibles."
        )
        return

    if isinstance(
        restrictions,
        dict,
    ):
        items = tuple(
            restrictions.items()
        )
    else:
        items = tuple(
            (
                getattr(
                    restriction,
                    "name",
                    "Unknown",
                ),
                restriction,
            )
            for restriction in restrictions
        )

    total_weighted = 0.0
    total_weight = 0.0
    total_penalty = 0.0

    for name, restriction in items:
        score = float(
            getattr(
                restriction,
                "score",
                0.0,
            )
        )

        weight = float(
            getattr(
                restriction,
                "weight",
                0.0,
            )
        )

        penalty = float(
            getattr(
                restriction,
                "penalty",
                0.0,
            )
        )

        weighted_score = (
            score
            * weight
        )

        contribution = (
            weighted_score
            / 100.0
        )

        total_weighted += weighted_score
        total_weight += weight
        total_penalty += penalty

        print(
            f"{str(name):<24}"
            f"| Score: {score:7.2f} "
            f"| Peso: {weight:6.2f} "
            f"| Aporta: {contribution:6.2f} "
            f"| Penalty: {penalty:6.2f}"
        )

    print("-" * 72)

    weighted_average = (
        total_weighted
        / total_weight
        if total_weight > 0.0
        else 0.0
    )

    print(
        f"{'MEDIA PONDERADA':<24}"
        f"| {weighted_average:7.2f}"
    )

    print(
        f"{'PENALIZACIÓN TOTAL':<24}"
        f"| {total_penalty:7.2f}"
    )

    print(
        f"{'SCORE FINAL':<24}"
        f"| {result.final_score:7.2f}"
    )


# ============================================================
# Resultado por consola
# ============================================================

def print_result(
    result: BaseReportResult,
    scoring_model: ScoringModel,
) -> None:
    """
    Muestra un resumen completo compatible con ambos modos.
    """

    print()
    print("=" * 72)
    print(
        "LAN CS2 TEAM BALANCER"
    )
    print("=" * 72)

    print(
        f"Modo:                 "
        f"{result.mode.label}"
    )

    if result.optimized:
        print(
            f"Puntuación inicial:   "
            f"{result.initial_score:.2f}"
        )

        print(
            f"Puntuación final:     "
            f"{result.final_score:.2f}"
        )

        print(
            f"Mejora total:         "
            f"{result.improvement:+.2f}"
        )

        print(
            f"Movimientos:          "
            f"{result.iterations}"
        )

        print(
            f"Evaluaciones:         "
            f"{result.total_evaluations}"
        )

        print(
            f"Tiempo optimización:  "
            f"{result.elapsed_ms:.2f} ms"
        )

        optimization_mode = (
            getattr(
                result,
                "metadata",
                {},
            )
            .get(
                "optimization_mode"
            )
        )

        print(
            f"Motor optimización:   "
            f"{str(optimization_mode or 'fast').upper()}"
        )

    else:
        print(
            f"Puntuación equilibrio:"
            f" {result.final_score:.2f}"
        )

        print(
            f"Clasificación:        "
            f"{result.balance_label}"
        )

        print(
            f"Evaluaciones:         "
            f"{result.total_evaluations}"
        )

        print(
            f"Tiempo evaluación:    "
            f"{result.elapsed_ms:.2f} ms"
        )

    print(
        f"Penalización:         "
        f"{result.penalty:.2f}"
    )

    print(
        f"Composición válida:   "
        f"{'SÍ' if result.is_valid else 'NO'}"
    )

    print(
        f"Equipos:              "
        f"{result.team_count}"
    )

    print(
        f"Jugadores:            "
        f"{result.player_count}"
    )

    if (
        result.optimized
        and getattr(
            result,
            "metadata",
            {},
        ).get(
            "optimization_mode"
        ) == OptimizationMode.STABLE.value
    ):
        print_stable_optimization(
            result
        )

    for team_index, team in enumerate(
        result.teams,
        start=1,
    ):
        team_name = (
            getattr(
                team,
                "name",
                None,
            )
            or f"Equipo {team_index}"
        )

        print()
        print("-" * 72)
        print(
            str(team_name).upper()
        )
        print("-" * 72)

        team_powers: list[float] = []

        for player in team.players:
            nickname = get_player_nickname(
                player
            )

            elo = get_player_attribute(
                player,
                "elo",
                "faceit_elo",
            )

            level = get_player_attribute(
                player,
                "faceit_level",
                "level",
            )

            kd = get_player_attribute(
                player,
                "kd",
            )

            adr = get_player_attribute(
                player,
                "adr",
            )

            team_number = getattr(
                player,
                "team_number",
                None,
            )

            power = scoring_model.power(
                player
            )

            team_powers.append(
                power
            )

            elo_text = (
                str(
                    int(
                        float(elo)
                    )
                )
                if elo is not None
                else "N/A"
            )

            level_text = (
                str(
                    int(
                        float(level)
                    )
                )
                if level is not None
                else "N/A"
            )

            kd_text = (
                f"{float(kd):.2f}"
                if kd is not None
                else "N/A"
            )

            adr_text = (
                f"{float(adr):.1f}"
                if adr is not None
                else "N/A"
            )

            team_text = (
                str(team_number)
                if team_number is not None
                else "—"
            )

            print(
                f"  {nickname:<20}"
                f"| Power: {power:6.2f} "
                f"| ELO: {elo_text:<5} "
                f"| LVL: {level_text:<3} "
                f"| KD: {kd_text:<5} "
                f"| ADR: {adr_text:<5} "
                f"| Team: {team_text}"
            )

        average_power = (
            sum(team_powers)
            / len(team_powers)
            if team_powers
            else 0.0
        )

        print(
            f"  {'':20}"
            f"| Power medio: "
            f"{average_power:.2f}"
        )

    print()


# ============================================================
# Metadata
# ============================================================

def create_run_metadata(
    players_file: Path,
    mode: ReportMode,
) -> dict[str, Any]:
    """
    Metadata básica que acompaña al resultado.

    Más adelante esta estructura podrá incluir identificador
    de evento, usuario, versión del algoritmo, configuración, etc.
    """

    return {
        "event_name": EVENT_NAME,

        "source_file": str(
            players_file
        ),

        "number_of_teams": (
            NUMBER_OF_TEAMS
        ),

        "team_size": (
            TEAM_SIZE
        ),

        "expected_player_count": (
            EXPECTED_PLAYER_COUNT
        ),

        "mode": mode.value,

        "optimization_mode": (
            OPTIMIZATION_MODE.value
            if mode is ReportMode.OPTIMIZED
            else None
        ),

        "source": (
            "FACEIT"
            if RUN_FACEIT_IMPORT
            else "CSV"
        ),
    }


# ============================================================
# Main
# ============================================================

def main() -> int:
    """
    Punto de entrada principal.

    Flujo:

        1. Obtiene/actualiza estadísticas FACEIT.
        2. Importa Player[].
        3. Detecta el modo mediante Team.
        4. Ejecuta LanBalancer.run_players().
        5. Si GLOBAL está activo, usa STABLE como warm start y ejecuta
           Branch & Bound.
        6. Valida el resultado final.
        7. Genera el informe HTML.

    La diferencia clave respecto al main anterior es que ya no
    construye ni optimiza equipos directamente.

    Toda esa responsabilidad pertenece a LanBalancer.
    """

    try:
        # ----------------------------------------------------
        # CSV de estadísticas
        # ----------------------------------------------------

        players_file = (
            resolve_players_file()
        )

        # ----------------------------------------------------
        # Aplicación
        # ----------------------------------------------------

        scoring_model = (
            create_scoring_model()
        )

        # Compartimos exactamente el mismo ObjectiveEngine entre STABLE
        # y GLOBAL para que ambos comparen exactamente la misma función
        # objetivo, con los mismos pesos y restricciones.
        objective_engine = (
            create_objective_engine(
                scoring_model=scoring_model,
            )
        )

        balancer = create_balancer(
            scoring_model=scoring_model,
            objective_engine=objective_engine,
        )

        # ----------------------------------------------------
        # Importación
        # ----------------------------------------------------

        players = balancer.importer.load(
            players_file
        )

        validate_players(
            players=players,
            expected_player_count=(
                EXPECTED_PLAYER_COUNT
            ),
        )

        if DEBUG_PLAYERS:
            print_players_debug(
                players
            )

        # ----------------------------------------------------
        # Detección del modo
        # ----------------------------------------------------

        mode = balancer.detect_mode(
            players
        )

        print_mode(
            mode
        )

        # ----------------------------------------------------
        # Ejecución
        # ----------------------------------------------------

        result = balancer.run_players(
            players=players,
            number_of_teams=(
                NUMBER_OF_TEAMS
            ),
            title=REPORT_TITLE,
            metadata=create_run_metadata(
                players_file=players_file,
                mode=mode,
            ),
        )

        global_result: (
            GlobalOptimizationResult
            | None
        ) = None

        # ----------------------------------------------------
        # GLOBAL
        # ----------------------------------------------------

        if (
            mode is ReportMode.OPTIMIZED
            and OPTIMIZATION_MODE
            is OptimizationMode.GLOBAL
        ):
            # `result` contiene aquí el warm start producido por STABLE.
            # GLOBAL lo conserva como incumbent y solo puede mantenerlo
            # o mejorarlo.
            result, global_result = (
                run_global_optimization(
                    players=players,
                    scoring_model=scoring_model,
                    objective_engine=(
                        objective_engine
                    ),
                    stable_result=result,
                )
            )

        # ----------------------------------------------------
        # Validación
        # ----------------------------------------------------

        validate_result(
            result=result,
            players=players,
        )

        if DEBUG_FINAL_TEAMS:
            debug_title = (
                "EQUIPOS PREASIGNADOS EVALUADOS"
                if result.evaluation_only
                else (
                    "EQUIPOS ÓPTIMOS GLOBAL"
                    if OPTIMIZATION_MODE
                    is OptimizationMode.GLOBAL
                    else "EQUIPOS OPTIMIZADOS"
                )
            )

            print_team_debug(
                teams=result.teams,
                title=debug_title,
            )

        # ----------------------------------------------------
        # Exportación
        # ----------------------------------------------------

        exported_path = balancer.export(
            result=result,
            output=OUTPUT_REPORT_FILE,
        )

        # ----------------------------------------------------
        # Consola
        # ----------------------------------------------------

        print_result(
            result=result,
            scoring_model=scoring_model,
        )

        if global_result is not None:
            print_global_optimization(
                global_result
            )

        print_objective_breakdown(
            result
        )

        print()

        print(
            "Informe HTML generado en: "
            f"{exported_path.resolve()}"
        )

        return 0

    except FileNotFoundError as error:
        print()
        print(
            f"ERROR DE ARCHIVO: {error}"
        )

        return 1

    except (
        TypeError,
        ValueError,
        RuntimeError,
        KeyError,
        AssertionError,
    ) as error:
        print()
        print(
            f"ERROR: {error}"
        )

        return 1

    except KeyboardInterrupt:
        print()
        print(
            "Proceso cancelado por el usuario."
        )

        return 130


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
