from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from application.results.optimization_result import (
    OptimizationResult,
)
from models.numeric import finite_real
from models.team import Team
from objective.objective_result import ObjectiveResult
from optimizer.local_optimizer import (
    LocalOptimizer,
)
from optimizer.modes.stable_optimization_config import (
    StableOptimizationConfig,
)
from optimizer.stable.convergence_tracker import (
    ConvergenceSnapshot,
    ConvergenceTracker,
)
from optimizer.stable.solution_selector import (
    SolutionSelector,
)
from optimizer.stable.solution_signature import (
    SolutionSignature,
)

RestartFactory = Callable[
    [Sequence[Team], int, int],
    Sequence[Team],
]


@dataclass(frozen=True, slots=True)
class _StructuralInvariant:
    team_count: int
    team_sizes: tuple[int, ...]
    signature: SolutionSignature

    @classmethod
    def capture(cls, teams: Sequence[Team]) -> _StructuralInvariant:
        signature = SolutionSignature.from_teams(teams)
        return cls(
            len(teams), tuple(sorted(len(team.players) for team in teams)), signature
        )

    def validate(self, teams: Sequence[Team], stage: str) -> SolutionSignature:
        if len(teams) != self.team_count:
            raise RuntimeError(
                f"Stable optimization changed the number of teams during {stage}."
            )
        if tuple(sorted(len(team.players) for team in teams)) != self.team_sizes:
            raise RuntimeError(
                f"Stable optimization changed team sizes during {stage}."
            )
        signature = SolutionSignature.from_teams(teams)
        StableOptimizer._validate_same_player_pool(self.signature, signature, stage)
        return signature


@dataclass(
    frozen=True,
    slots=True,
)
class StableOptimizationRun:
    """
    Información completa de una ejecución del modo STABLE.

    result:
        Mejor OptimizationResult encontrado.

    convergence:
        Snapshot final de convergencia.

    signature:
        Firma canónica de la solución seleccionada.

    elapsed_seconds:
        Tiempo real consumido por todo StableOptimizer.

    completed_restarts:
        Número de búsquedas locales ejecutadas.

    unique_solutions:
        Número de composiciones finales diferentes observadas.

    best_restart_index:
        Restart that produced the selected result, including tie-breaks.
        convergence.best_quality_restart_index separately identifies the last
        real quality improvement; its legacy best_restart_index is preserved.

    selection_changes:
        Número de veces que cambió la solución seleccionada.

        Incluye tanto mejoras reales como desempates canónicos.

    quality_improvements:
        Número de veces que aumentó realmente la calidad:

            - menor penalización;
            - o mayor score.

        Los desempates canónicos NO cuentan.
    """

    result: OptimizationResult

    convergence: ConvergenceSnapshot

    signature: SolutionSignature

    elapsed_seconds: float

    completed_restarts: int

    unique_solutions: int

    best_restart_index: int | None

    selection_changes: int

    quality_improvements: int

    def __post_init__(self) -> None:
        finite_real(self.elapsed_seconds, "elapsed_seconds")
        finite_real(self.result.objective_result.score, "score")
        finite_real(self.result.penalty, "penalty")

    @property
    def best_quality_restart_index(self) -> int | None:
        """Last real quality improvement; does not follow canonical ties."""
        return self.convergence.best_quality_restart_index

    @property
    def score(
        self,
    ) -> float:
        return float(
            self.result.score
        )

    @property
    def penalty(
        self,
    ) -> float:
        return float(
            self.result.penalty
        )

    @property
    def confidence(
        self,
    ) -> str:
        return (
            self.convergence.confidence
        )

    @property
    def stop_reason(
        self,
    ) -> str | None:
        return (
            self.convergence.stop_reason
        )

    @property
    def target_reached(
        self,
    ) -> bool:
        return (
            self.convergence.target_was_reached
        )

    @property
    def target_confirmed(
        self,
    ) -> bool:
        return (
            self.convergence.target_confirmed
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "score": self.score,

            "penalty": self.penalty,

            "signature": (
                self.signature.as_dict()
            ),

            "elapsed_seconds": (
                self.elapsed_seconds
            ),

            "completed_restarts": (
                self.completed_restarts
            ),

            "unique_solutions": (
                self.unique_solutions
            ),

            "best_restart_index": (
                self.best_restart_index
            ),

            "best_restart_number": (
                (
                    self.best_restart_index
                    + 1
                )
                if self.best_restart_index
                is not None
                else None
            ),

            "best_quality_restart_index": self.best_quality_restart_index,

            "selection_changes": (
                self.selection_changes
            ),

            "quality_improvements": (
                self.quality_improvements
            ),

            "confidence": (
                self.confidence
            ),

            "stop_reason": (
                self.stop_reason
            ),

            "target_reached": (
                self.target_reached
            ),

            "target_confirmed": (
                self.target_confirmed
            ),

            "convergence": (
                self.convergence.as_dict()
            ),
        }


class StableOptimizer:
    """
    Orquestador del modo de optimización STABLE.

    Ejecuta múltiples optimizaciones locales partiendo de soluciones
    iniciales diferentes pero reproducibles.

    Flujo:

        initial_teams
            ↓
        RestartFactory(seed)
            ↓
        LocalOptimizer
            ↓
        OptimizationResult
            ↓
        SolutionSelector
            ↓
        ConvergenceTracker
            ↓
        repetir hasta convergencia
            ↓
        UNA solución final

    StableOptimizer NO genera por sí mismo la diversidad inicial.

    Esa responsabilidad pertenece a RestartFactory.

    De esta forma mantenemos separadas:

        StableOptimizer
            decide CUÁNTO buscar.

        RestartFactory
            decide DESDE DÓNDE buscar.

        LocalOptimizer
            decide CÓMO mejorar una solución.

        SolutionSelector
            decide CUÁL conservar.

        ConvergenceTracker
            decide CUÁNDO parar.

    Reproducibilidad:

        Si RestartFactory es determinista respecto a `seed` y el
        LocalOptimizer no utiliza aleatoriedad no controlada:

            mismos jugadores
            + misma configuración
            + mismo base_seed

        producen exactamente la misma secuencia de búsquedas.
    """

    def __init__(
        self,
        local_optimizer: LocalOptimizer,
        restart_factory: RestartFactory,
        config: StableOptimizationConfig | None = None,
        selector: SolutionSelector | None = None,
    ) -> None:
        if local_optimizer is None:
            raise ValueError(
                "local_optimizer cannot be None."
            )

        if not isinstance(
            local_optimizer,
            LocalOptimizer,
        ):
            raise TypeError(
                "local_optimizer must be a "
                "LocalOptimizer instance."
            )

        if restart_factory is None:
            raise ValueError(
                "restart_factory cannot be None."
            )

        if not callable(
            restart_factory
        ):
            raise TypeError(
                "restart_factory must be callable."
            )

        if config is None:
            config = (
                StableOptimizationConfig.balanced()
            )

        if not isinstance(
            config,
            StableOptimizationConfig,
        ):
            raise TypeError(
                "config must be a "
                "StableOptimizationConfig instance."
            )

        if selector is None:
            selector = SolutionSelector(
                config=config
            )

        if not isinstance(
            selector,
            SolutionSelector,
        ):
            raise TypeError(
                "selector must be a "
                "SolutionSelector instance."
            )

        if (
            selector.config
            is not config
            and selector.config
            != config
        ):
            raise ValueError(
                "selector and StableOptimizer must use "
                "equivalent configurations."
            )

        self._local_optimizer = (
            local_optimizer
        )

        self._restart_factory = (
            restart_factory
        )

        self._config = config

        self._selector = selector

        self._last_run: (
            StableOptimizationRun
            | None
        ) = None

    # ========================================================
    # Optimización
    # ========================================================

    def optimize(
        self,
        initial_teams: Sequence[Team],
    ) -> OptimizationResult:
        """
        Ejecuta el modo STABLE y devuelve únicamente la mejor
        OptimizationResult.

        Para consultar información de convergencia después:

            optimizer.last_run

        o:

            optimizer.require_last_run()
        """
        run = self.optimize_with_details(
            initial_teams
        )

        return run.result

    def optimize_with_details(
        self,
        initial_teams: Sequence[Team],
    ) -> StableOptimizationRun:
        """
        Ejecuta la búsqueda estable completa y devuelve tanto el
        resultado final como la información de convergencia.
        """
        self._last_run = None

        validated_initial_teams = (
            self._validate_teams(
                initial_teams
            )
        )

        invariant = _StructuralInvariant.capture(validated_initial_teams)
        selected_restart_index: int | None = None

        tracker = ConvergenceTracker(
            config=self._config
        )

        selected_result: (
            OptimizationResult
            | None
        ) = None

        selected_signature: (
            SolutionSignature
            | None
        ) = None

        selection_changes = 0

        quality_improvements = 0

        started_at = perf_counter()

        for restart_index in range(
            self._config.maximum_restarts
        ):
            # ------------------------------------------------
            # Límites que pueden alcanzarse antes de iniciar
            # otra búsqueda costosa.
            # ------------------------------------------------

            if (
                tracker.completed_restarts > 0
                and tracker.should_stop
            ):
                break

            seed = (
                self._config.seed_for_restart(
                    restart_index
                )
            )

            restart_teams = (
                self._build_restart(
                    initial_teams=(
                        validated_initial_teams
                    ),
                    restart_index=(
                        restart_index
                    ),
                    seed=seed,
                )
            )

            invariant.validate(restart_teams, f"restart {restart_index}")

            # ------------------------------------------------
            # Optimización local.
            # ------------------------------------------------

            result = (
                self._local_optimizer.optimize(
                    restart_teams
                )
            )

            result = (
                self._validate_result(
                    result
                )
            )

            result_signature = invariant.validate(
                result.teams, f"optimized restart {restart_index}"
            )

            # ------------------------------------------------
            # Primera solución.
            # ------------------------------------------------

            if selected_result is None:
                selected_result = result
                selected_restart_index = restart_index

                selected_signature = (
                    result_signature
                )

                selection_changed = True

                quality_improved = True

            # ------------------------------------------------
            # Comparación determinista.
            # ------------------------------------------------

            else:
                comparison = (
                    self._selector.compare(
                        current=selected_result,
                        candidate=result,
                    )
                )

                quality_improved = (
                    self._is_quality_improvement(
                        current=selected_result,
                        candidate=result,
                    )
                )

                selection_changed = (
                    comparison.winner
                    is result
                    and not comparison.same_solution
                )

                if (
                    comparison.winner
                    is result
                ):
                    selected_result = result
                    selected_restart_index = restart_index

                    selected_signature = (
                        result_signature
                    )

            if selection_changed:
                selection_changes += 1

            if quality_improved:
                quality_improvements += 1

            # ------------------------------------------------
            # IMPORTANTE
            #
            # El tracker debe reiniciar su patience únicamente
            # cuando existe una mejora REAL de calidad.
            #
            # Un cambio por canonical_signature no es una mejora.
            # ------------------------------------------------

            tracker.register(
                result=result,

                restart_index=(
                    restart_index
                ),

                seed=seed,

                improved_best=(
                    quality_improved
                ),
            )

            # ------------------------------------------------
            # Comprobación posterior al restart.
            # ------------------------------------------------

            if tracker.should_stop:
                break

        # ====================================================
        # Resultado final
        # ====================================================

        if selected_result is None:
            raise RuntimeError(
                "StableOptimizer completed without "
                "producing any optimization result."
            )

        if selected_signature is None:
            selected_signature = (
                SolutionSignature.from_teams(
                    selected_result.teams
                )
            )

        if invariant.validate(selected_result.teams, "selected result") != selected_signature:
            raise RuntimeError("Selected solution changed after local optimization.")
        selected_result = self._verify_selected_result(selected_result)
        if invariant.validate(selected_result.teams, "final verification") != selected_signature:
            raise RuntimeError("Selected solution changed during final verification.")
        snapshot = tracker.snapshot()

        elapsed_seconds = max(
            0.0,
            (
                perf_counter()
                - started_at
            ),
        )

        run = StableOptimizationRun(
            result=selected_result,

            convergence=snapshot,

            signature=selected_signature,

            elapsed_seconds=(
                elapsed_seconds
            ),

            completed_restarts=(
                tracker.completed_restarts
            ),

            unique_solutions=(
                tracker.unique_solution_count
            ),

            best_restart_index=(
                selected_restart_index
            ),

            selection_changes=(
                selection_changes
            ),

            quality_improvements=(
                quality_improvements
            ),
        )

        self._last_run = run

        return run

    def _verify_selected_result(
        self, selected: OptimizationResult
    ) -> OptimizationResult:
        # Reuse the exact engine used by local move evaluation, never rebuild it.
        verified = self._local_optimizer.evaluator.objective.evaluate(selected.teams)
        if not isinstance(verified, ObjectiveResult):
            raise TypeError("Final verification must return ObjectiveResult.")
        claimed = selected.objective_result
        tolerance = self._config.score_tolerance

        def consistent(
            first: object, second: object, field: str, *, exact: bool = False
        ) -> None:
            left = finite_real(first, field)
            right = finite_real(second, field)
            mismatch = left != right if exact else abs(left - right) > tolerance
            if mismatch:
                raise RuntimeError(f"Final verification inconsistent {field}.")

        consistent(claimed.score, verified.score, "score")
        consistent(claimed.penalty, verified.penalty, "penalty", exact=True)
        if claimed.restrictions.keys() != verified.restrictions.keys():
            raise RuntimeError("Final verification inconsistent restrictions.")
        for name, actual in verified.restrictions.items():
            expected = claimed.restrictions[name]
            if expected.name != actual.name or expected.details != actual.details:
                raise RuntimeError(
                    f"Final verification inconsistent restriction {name}."
                )
            for field in ("score", "weight", "penalty"):
                consistent(
                    getattr(expected, field),
                    getattr(actual, field),
                    f"{name}.{field}",
                    exact=field != "score",
                )
        return OptimizationResult(
            teams=selected.teams,
            objective_result=verified,
            history=selected.history,
            initial_score=selected.initial_score,
            title=selected.title,
            metadata=selected.metadata,
        )

    # ========================================================
    # Restart
    # ========================================================

    def _build_restart(
        self,
        initial_teams: Sequence[Team],
        restart_index: int,
        seed: int,
    ) -> list[Team]:
        """
        Solicita al RestartFactory una nueva solución inicial.

        Firma esperada:

            factory(
                initial_teams,
                restart_index,
                seed,
            ) -> Sequence[Team]

        El RestartFactory debe:

            - preservar exactamente los jugadores;
            - preservar número de equipos;
            - preservar tamaños estructurales;
            - generar siempre lo mismo para la misma seed.
        """
        generated = self._restart_factory(
            initial_teams,
            restart_index,
            seed,
        )

        teams = self._validate_teams(
            generated
        )

        if (
            len(teams)
            != len(initial_teams)
        ):
            raise RuntimeError(
                "RestartFactory changed the number "
                "of teams."
            )

        return teams

    # ========================================================
    # Mejora real
    # ========================================================

    def _is_quality_improvement(
        self,
        current: OptimizationResult,
        candidate: OptimizationResult,
    ) -> bool:
        """
        Determina si candidate mejora realmente la calidad.

        Esta función se utiliza EXCLUSIVAMENTE para convergencia.

        Diferencia respecto a SolutionSelector:

            SolutionSelector también puede cambiar la solución por
            desempates secundarios o firma canónica.

            Eso NO debe reiniciar convergence_patience.

        Se considera mejora real cuando:

            1. disminuye la penalización estructural;

        o, con penalización equivalente:

            2. aumenta el score por encima de score_tolerance.
        """
        current_penalty = float(
            current.penalty
        )

        candidate_penalty = float(
            candidate.penalty
        )

        tolerance = (
            self._config.score_tolerance
        )

        penalty_difference = (
            current_penalty
            - candidate_penalty
        )

        if (
            penalty_difference
            > tolerance
        ):
            return True

        if (
            abs(
                penalty_difference
            )
            > tolerance
        ):
            return False

        return (
            self._config.score_improves(
                candidate=float(
                    candidate.score
                ),
                current_best=float(
                    current.score
                ),
            )
        )

    # ========================================================
    # Player pool
    # ========================================================

    @staticmethod
    def _validate_same_player_pool(
        expected: SolutionSignature,
        actual: SolutionSignature,
        stage: str,
    ) -> None:
        if expected.same_player_pool(
            actual
        ):
            return

        raise RuntimeError(
            "Stable optimization changed the "
            f"player pool during {stage}."
        )

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        try:
            team_list = list(
                teams
            )

        except TypeError as error:
            raise TypeError(
                "teams must be an iterable."
            ) from error

        if not team_list:
            raise ValueError(
                "At least one team is required."
            )

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            if team is None:
                raise ValueError(
                    f"Team {index} cannot be None."
                )

            if not isinstance(
                team,
                Team,
            ):
                raise TypeError(
                    f"Team {index} must be a "
                    "Team instance."
                )

        return team_list

    @staticmethod
    def _validate_result(
        result: OptimizationResult,
    ) -> OptimizationResult:
        if result is None:
            raise RuntimeError(
                "LocalOptimizer returned None."
            )

        if not isinstance(
            result,
            OptimizationResult,
        ):
            raise TypeError(
                "LocalOptimizer.optimize() must "
                "return OptimizationResult."
            )

        finite_real(result.objective_result.score, "score")
        finite_real(result.penalty, "penalty")
        for restriction in result.restrictions.values():
            for field in ("score", "weight", "penalty"):
                finite_real(getattr(restriction, field), f"{restriction.name}.{field}")
        return result

    # ========================================================
    # Estado de ejecución
    # ========================================================

    @property
    def last_run(
        self,
    ) -> StableOptimizationRun | None:
        return self._last_run

    def require_last_run(
        self,
    ) -> StableOptimizationRun:
        """
        Devuelve la última ejecución o genera error cuando todavía
        no se ha ejecutado el optimizador.
        """
        if self._last_run is None:
            raise RuntimeError(
                "StableOptimizer has not been executed yet."
            )

        return self._last_run

    # ========================================================
    # Componentes
    # ========================================================

    @property
    def local_optimizer(
        self,
    ) -> LocalOptimizer:
        return self._local_optimizer

    @property
    def config(
        self,
    ) -> StableOptimizationConfig:
        return self._config

    @property
    def selector(
        self,
    ) -> SolutionSelector:
        return self._selector

    @property
    def restart_factory(
        self,
    ) -> RestartFactory:
        return self._restart_factory

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"target_score="
            f"{self._config.target_score:.2f}, "
            f"maximum_restarts="
            f"{self._config.maximum_restarts}, "
            f"base_seed="
            f"{self._config.base_seed})"
        )
