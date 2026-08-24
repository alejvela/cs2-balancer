from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from optimizer.modes.stable_optimization_config import (
    StableOptimizationConfig,
)
from optimizer.optimization_result import (
    OptimizationResult,
)
from optimizer.stable.solution_signature import (
    SolutionSignature,
)


@dataclass(
    frozen=True,
    slots=True,
)
class RestartRecord:
    """
    Registro de una ejecución individual del modo STABLE.
    """

    restart_index: int

    seed: int

    score: float

    penalty: float

    signature_hash: str

    improved_best: bool

    target_reached: bool

    perfect_reached: bool

    total_evaluations: int

    elapsed_ms: float

    @property
    def restart_number(
        self,
    ) -> int:
        return (
            self.restart_index
            + 1
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "restart_index": (
                self.restart_index
            ),

            "restart_number": (
                self.restart_number
            ),

            "seed": (
                self.seed
            ),

            "score": (
                self.score
            ),

            "penalty": (
                self.penalty
            ),

            "signature_hash": (
                self.signature_hash
            ),

            "improved_best": (
                self.improved_best
            ),

            "target_reached": (
                self.target_reached
            ),

            "perfect_reached": (
                self.perfect_reached
            ),

            "total_evaluations": (
                self.total_evaluations
            ),

            "elapsed_ms": (
                self.elapsed_ms
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ConvergenceSnapshot:
    """
    Estado inmutable del proceso de convergencia.
    """

    completed_restarts: int

    unique_solutions: int

    best_score: float | None

    best_penalty: float | None

    best_restart_index: int | None

    restarts_without_improvement: int

    target_was_reached: bool

    restart_where_target_was_reached: int | None

    restarts_since_target: int

    perfect_was_reached: bool

    total_evaluations: int

    elapsed_seconds: float

    convergence_reached: bool

    target_confirmed: bool

    restart_limit_reached: bool

    evaluation_limit_reached: bool

    elapsed_limit_reached: bool

    should_stop: bool

    stop_reason: str | None

    confidence: str

    @property
    def best_restart_number(
        self,
    ) -> int | None:
        if self.best_restart_index is None:
            return None

        return (
            self.best_restart_index
            + 1
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "completed_restarts": (
                self.completed_restarts
            ),

            "unique_solutions": (
                self.unique_solutions
            ),

            "best_score": (
                self.best_score
            ),

            "best_penalty": (
                self.best_penalty
            ),

            "best_restart_index": (
                self.best_restart_index
            ),

            "best_restart_number": (
                self.best_restart_number
            ),

            "restarts_without_improvement": (
                self.restarts_without_improvement
            ),

            "target_was_reached": (
                self.target_was_reached
            ),

            "restart_where_target_was_reached": (
                self.restart_where_target_was_reached
            ),

            "restarts_since_target": (
                self.restarts_since_target
            ),

            "perfect_was_reached": (
                self.perfect_was_reached
            ),

            "total_evaluations": (
                self.total_evaluations
            ),

            "elapsed_seconds": (
                self.elapsed_seconds
            ),

            "convergence_reached": (
                self.convergence_reached
            ),

            "target_confirmed": (
                self.target_confirmed
            ),

            "restart_limit_reached": (
                self.restart_limit_reached
            ),

            "evaluation_limit_reached": (
                self.evaluation_limit_reached
            ),

            "elapsed_limit_reached": (
                self.elapsed_limit_reached
            ),

            "should_stop": (
                self.should_stop
            ),

            "stop_reason": (
                self.stop_reason
            ),

            "confidence": (
                self.confidence
            ),
        }


@dataclass(
    slots=True,
)
class ConvergenceTracker:
    """
    Controla la convergencia del modo STABLE.

    Responsabilidades:

        - Registrar cada restart.
        - Detectar nuevas mejores soluciones.
        - Contar soluciones únicas.
        - Medir reinicios sin mejora.
        - Detectar cuándo se alcanza target_score.
        - Confirmar estabilidad después de alcanzar el objetivo.
        - Aplicar límites de tiempo y evaluaciones.
        - Decidir cuándo detener la búsqueda.
        - Estimar un nivel de confianza operativo.

    IMPORTANTE:

    `confidence` NO representa una probabilidad matemática de que la
    solución sea el óptimo global.

    Es una clasificación heurística de estabilidad basada en:

        - cantidad de exploración;
        - ausencia prolongada de mejoras;
        - número de soluciones únicas;
        - proximidad al target;
        - confirmación del target.
    """

    config: StableOptimizationConfig

    _records: list[RestartRecord] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    _unique_signatures: set[
        SolutionSignature
    ] = field(
        default_factory=set,
        init=False,
        repr=False,
    )

    _best_result: OptimizationResult | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _best_signature: SolutionSignature | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _best_restart_index: int | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _restarts_without_improvement: int = field(
        default=0,
        init=False,
        repr=False,
    )

    _target_was_reached: bool = field(
        default=False,
        init=False,
        repr=False,
    )

    _restart_where_target_was_reached: int | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _perfect_was_reached: bool = field(
        default=False,
        init=False,
        repr=False,
    )

    _total_evaluations: int = field(
        default=0,
        init=False,
        repr=False,
    )

    _started_at: float = field(
        default_factory=perf_counter,
        init=False,
        repr=False,
    )

    def __post_init__(
        self,
    ) -> None:
        if self.config is None:
            raise ValueError(
                "config cannot be None."
            )

        if not isinstance(
            self.config,
            StableOptimizationConfig,
        ):
            raise TypeError(
                "config must be a StableOptimizationConfig instance."
            )

    # ========================================================
    # Registro
    # ========================================================

    def register(
        self,
        result: OptimizationResult,
        restart_index: int,
        seed: int,
        improved_best: bool,
    ) -> RestartRecord:
        """
        Registra una ejecución completa.

        El parámetro improved_best debe venir del SolutionSelector o
        del StableOptimizer.

        El tracker no decide qué solución es mejor; únicamente registra
        la decisión para mantener separadas las responsabilidades.
        """
        result = self._validate_result(
            result
        )

        restart_index = (
            self._validate_non_negative_integer(
                restart_index,
                "restart_index",
            )
        )

        seed = self._validate_integer(
            seed,
            "seed",
        )

        if not isinstance(
            improved_best,
            bool,
        ):
            raise TypeError(
                "improved_best must be a boolean."
            )

        expected_restart_index = len(
            self._records
        )

        if (
            restart_index
            != expected_restart_index
        ):
            raise ValueError(
                "restart_index must be sequential. "
                f"Expected {expected_restart_index}, "
                f"received {restart_index}."
            )

        signature = (
            SolutionSignature.from_teams(
                result.teams
            )
        )

        self._unique_signatures.add(
            signature
        )

        if improved_best:
            self._best_result = result

            self._best_signature = (
                signature
            )

            self._best_restart_index = (
                restart_index
            )

            self._restarts_without_improvement = 0

        else:
            self._restarts_without_improvement += 1

        target_reached = (
            self.config.target_reached(
                result.score
            )
        )

        perfect_reached = (
            self.config.perfect_reached(
                result.score
            )
        )

        if (
            target_reached
            and not self._target_was_reached
        ):
            self._target_was_reached = True

            self._restart_where_target_was_reached = (
                restart_index
            )

        if perfect_reached:
            self._perfect_was_reached = True

        evaluations = max(
            0,
            int(
                result.total_evaluations
            ),
        )

        self._total_evaluations += (
            evaluations
        )

        elapsed_ms = max(
            0.0,
            float(
                result.elapsed_ms
            ),
        )

        record = RestartRecord(
            restart_index=restart_index,

            seed=seed,

            score=float(
                result.score
            ),

            penalty=float(
                result.penalty
            ),

            signature_hash=(
                signature.stable_hash
            ),

            improved_best=(
                improved_best
            ),

            target_reached=(
                target_reached
            ),

            perfect_reached=(
                perfect_reached
            ),

            total_evaluations=(
                evaluations
            ),

            elapsed_ms=(
                elapsed_ms
            ),
        )

        self._records.append(
            record
        )

        return record

    # ========================================================
    # Estado
    # ========================================================

    @property
    def records(
        self,
    ) -> tuple[RestartRecord, ...]:
        return tuple(
            self._records
        )

    @property
    def completed_restarts(
        self,
    ) -> int:
        return len(
            self._records
        )

    @property
    def unique_solution_count(
        self,
    ) -> int:
        return len(
            self._unique_signatures
        )

    @property
    def best_result(
        self,
    ) -> OptimizationResult | None:
        return self._best_result

    @property
    def best_signature(
        self,
    ) -> SolutionSignature | None:
        return self._best_signature

    @property
    def best_restart_index(
        self,
    ) -> int | None:
        return self._best_restart_index

    @property
    def best_score(
        self,
    ) -> float | None:
        if self._best_result is None:
            return None

        return float(
            self._best_result.score
        )

    @property
    def best_penalty(
        self,
    ) -> float | None:
        if self._best_result is None:
            return None

        return float(
            self._best_result.penalty
        )

    @property
    def restarts_without_improvement(
        self,
    ) -> int:
        return (
            self._restarts_without_improvement
        )

    @property
    def target_was_reached(
        self,
    ) -> bool:
        return self._target_was_reached

    @property
    def perfect_was_reached(
        self,
    ) -> bool:
        return self._perfect_was_reached

    @property
    def restart_where_target_was_reached(
        self,
    ) -> int | None:
        return (
            self._restart_where_target_was_reached
        )

    @property
    def restarts_since_target(
        self,
    ) -> int:
        if (
            not self._target_was_reached
            or self._restart_where_target_was_reached
            is None
        ):
            return 0

        return max(
            0,
            (
                self.completed_restarts
                - self._restart_where_target_was_reached
                - 1
            ),
        )

    @property
    def total_evaluations(
        self,
    ) -> int:
        return self._total_evaluations

    @property
    def elapsed_seconds(
        self,
    ) -> float:
        return max(
            0.0,
            (
                perf_counter()
                - self._started_at
            ),
        )

    # ========================================================
    # Condiciones
    # ========================================================

    @property
    def convergence_reached(
        self,
    ) -> bool:
        return self.config.convergence_reached(
            completed_restarts=(
                self.completed_restarts
            ),

            restarts_without_improvement=(
                self.restarts_without_improvement
            ),

            unique_solution_count=(
                self.unique_solution_count
            ),
        )

    @property
    def target_confirmed(
        self,
    ) -> bool:
        return self.config.target_confirmed(
            target_was_reached=(
                self.target_was_reached
            ),

            restarts_since_target=(
                self.restarts_since_target
            ),
        )

    @property
    def restart_limit_reached(
        self,
    ) -> bool:
        return self.config.restart_limit_reached(
            self.completed_restarts
        )

    @property
    def evaluation_limit_reached(
        self,
    ) -> bool:
        return self.config.evaluation_limit_reached(
            self.total_evaluations
        )

    @property
    def elapsed_limit_reached(
        self,
    ) -> bool:
        return self.config.elapsed_limit_reached(
            self.elapsed_seconds
        )

    @property
    def perfect_stop_reached(
        self,
    ) -> bool:
        if not self.config.stop_on_perfect_score:
            return False

        if not self.perfect_was_reached:
            return False

        return (
            self.config.minimum_search_completed(
                self.completed_restarts
            )
        )

    # ========================================================
    # Parada
    # ========================================================

    @property
    def stop_reason(
        self,
    ) -> str | None:
        """
        Prioridad de parada:

            1. Perfect score confirmado mediante búsqueda mínima.
            2. Límite temporal.
            3. Límite de evaluaciones.
            4. Límite máximo de restarts.
            5. Target alcanzado y confirmado.
            6. Convergencia sin alcanzar necesariamente target.
        """
        if self.perfect_stop_reached:
            return "perfect_score"

        if self.elapsed_limit_reached:
            return "elapsed_limit"

        if self.evaluation_limit_reached:
            return "evaluation_limit"

        if self.restart_limit_reached:
            return "restart_limit"

        if (
            self.target_was_reached
            and self.target_confirmed
            and self.config.minimum_search_completed(
                self.completed_restarts
            )
        ):
            return "target_confirmed"

        if self.convergence_reached:
            return "convergence"

        return None

    @property
    def should_stop(
        self,
    ) -> bool:
        return (
            self.stop_reason
            is not None
        )

    # ========================================================
    # Confianza
    # ========================================================

    @property
    def confidence(
        self,
    ) -> str:
        """
        Clasificación heurística de estabilidad.

        No equivale a probabilidad matemática.

        VERY HIGH:
            target confirmado o convergencia fuerte después de una
            exploración amplia.

        HIGH:
            convergencia alcanzada o target alcanzado con suficiente
            exploración.

        MEDIUM:
            búsqueda mínima realizada y varias soluciones exploradas.

        LOW:
            exploración todavía escasa.
        """
        if self.completed_restarts <= 0:
            return "NONE"

        if (
            self.target_confirmed
            and self.completed_restarts
            >= self.config.minimum_restarts
            and self.unique_solution_count
            >= self.config.minimum_unique_solutions
        ):
            return "VERY_HIGH"

        if (
            self.convergence_reached
            and self.completed_restarts
            >= (
                self.config.minimum_restarts
                + self.config.convergence_patience
            )
        ):
            return "VERY_HIGH"

        if (
            self.convergence_reached
            or (
                self.target_was_reached
                and self.config.minimum_search_completed(
                    self.completed_restarts
                )
            )
        ):
            return "HIGH"

        if (
            self.config.minimum_search_completed(
                self.completed_restarts
            )
            and self.unique_solution_count
            >= max(
                1,
                self.config.minimum_unique_solutions // 2,
            )
        ):
            return "MEDIUM"

        return "LOW"

    # ========================================================
    # Snapshot
    # ========================================================

    def snapshot(
        self,
    ) -> ConvergenceSnapshot:
        return ConvergenceSnapshot(
            completed_restarts=(
                self.completed_restarts
            ),

            unique_solutions=(
                self.unique_solution_count
            ),

            best_score=(
                self.best_score
            ),

            best_penalty=(
                self.best_penalty
            ),

            best_restart_index=(
                self.best_restart_index
            ),

            restarts_without_improvement=(
                self.restarts_without_improvement
            ),

            target_was_reached=(
                self.target_was_reached
            ),

            restart_where_target_was_reached=(
                self.restart_where_target_was_reached
            ),

            restarts_since_target=(
                self.restarts_since_target
            ),

            perfect_was_reached=(
                self.perfect_was_reached
            ),

            total_evaluations=(
                self.total_evaluations
            ),

            elapsed_seconds=(
                self.elapsed_seconds
            ),

            convergence_reached=(
                self.convergence_reached
            ),

            target_confirmed=(
                self.target_confirmed
            ),

            restart_limit_reached=(
                self.restart_limit_reached
            ),

            evaluation_limit_reached=(
                self.evaluation_limit_reached
            ),

            elapsed_limit_reached=(
                self.elapsed_limit_reached
            ),

            should_stop=(
                self.should_stop
            ),

            stop_reason=(
                self.stop_reason
            ),

            confidence=(
                self.confidence
            ),
        )

    # ========================================================
    # Serialización
    # ========================================================

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot": (
                self.snapshot().as_dict()
            ),

            "records": [
                record.as_dict()
                for record in self._records
            ],

            "best_signature": (
                self._best_signature.as_dict()
                if self._best_signature
                is not None
                else None
            ),

            "config": (
                self.config.as_dict()
            ),
        }

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_result(
        result: OptimizationResult,
    ) -> OptimizationResult:
        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not isinstance(
            result,
            OptimizationResult,
        ):
            raise TypeError(
                "result must be an OptimizationResult instance."
            )

        return result

    @staticmethod
    def _validate_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
        ):
            raise TypeError(
                f"{field_name} must be an integer."
            )

        return value

    @classmethod
    def _validate_non_negative_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int:
        validated = cls._validate_integer(
            value=value,
            field_name=field_name,
        )

        if validated < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return validated

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"restarts={self.completed_restarts}, "
            f"unique={self.unique_solution_count}, "
            f"best_score={self.best_score!r}, "
            f"without_improvement="
            f"{self.restarts_without_improvement}, "
            f"confidence={self.confidence!r})"
        )
