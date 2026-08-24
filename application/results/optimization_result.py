from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from application.results.base_report_result import (
    BaseReportResult,
)
from application.results.report_mode import (
    ReportMode,
)
from models.team import Team
from objective.objective_result import ObjectiveResult
from optimizer.optimization_history import (
    OptimizationHistory,
)


class OptimizationResult(BaseReportResult):
    """
    Resultado completo de un proceso de generación y optimización.

    Extiende BaseReportResult con la información específica del
    optimizador:

        - Historial de movimientos aceptados.
        - Puntuación inicial.
        - Número de iteraciones.
        - Número total de evaluaciones.
        - Tiempo consumido por las estrategias.

    El resto de propiedades comunes se heredan de BaseReportResult:

        - teams
        - objective_result
        - score
        - final_score
        - improvement
        - penalty
        - restrictions
        - is_valid
        - balance_label
        - balance_level
        - team_count
        - player_count
        - metadata
        - serialización común

    Esta clase mantiene compatibilidad con el código anterior que
    construía resultados mediante:

        OptimizationResult(
            teams=teams,
            objective_result=objective_result,
            history=history,
        )
    """

    __slots__ = (
        "_history",
    )

    def __init__(
        self,
        teams: Sequence[Team],
        objective_result: ObjectiveResult,
        history: OptimizationHistory,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Construye un resultado de optimización.

        Args:
            teams:
                Equipos finales producidos por el optimizador.

            objective_result:
                Evaluación objetiva de la solución final.

            history:
                Historial completo de la optimización.

            title:
                Título opcional para informes o exportaciones.

            metadata:
                Información adicional relacionada con el evento,
                configuración o ejecución.
        """
        if history is None:
            raise ValueError(
                "history cannot be None."
            )

        if not isinstance(
            history,
            OptimizationHistory,
        ):
            raise TypeError(
                "history must be an OptimizationHistory instance."
            )

        self._history = history

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

    # ========================================================
    # Modalidad
    # ========================================================

    @property
    def mode(
        self,
    ) -> ReportMode:
        """
        Indica que los equipos proceden del motor de optimización.
        """
        return ReportMode.OPTIMIZED

    # ========================================================
    # Historial
    # ========================================================

    @property
    def history(
        self,
    ) -> OptimizationHistory:
        """
        Historial completo de movimientos y evaluaciones.
        """
        return self._history

    # ========================================================
    # Puntuaciones
    # ========================================================

    @property
    def initial_score(
        self,
    ) -> float:
        """
        Devuelve la puntuación anterior a la optimización.

        Cuando el historial no contiene una puntuación inicial, se
        considera que no hubo una evaluación inicial separada y se
        utiliza la puntuación final.
        """
        initial_score = self._history.initial_score

        if initial_score is None:
            return self.final_score

        return float(
            initial_score
        )

    # ========================================================
    # Métricas de optimización
    # ========================================================

    @property
    def iterations(
        self,
    ) -> int:
        """
        Número total de movimientos aceptados.
        """
        return int(
            self._history.count
        )

    @property
    def total_evaluations(
        self,
    ) -> int:
        """
        Número total de movimientos o soluciones evaluados.
        """
        return int(
            self._history.total_evaluations
        )

    @property
    def elapsed_ms(
        self,
    ) -> float:
        """
        Tiempo total consumido por las estrategias, en milisegundos.
        """
        return float(
            self._history.total_elapsed_ms
        )

    # ========================================================
    # Datos derivados específicos
    # ========================================================

    @property
    def accepted_movements(
        self,
    ) -> int:
        """
        Alias descriptivo del número de movimientos aceptados.
        """
        return self.iterations

    @property
    def has_movements(
        self,
    ) -> bool:
        """
        Indica si el optimizador aceptó al menos un movimiento.
        """
        return self.iterations > 0

    @property
    def improved(
        self,
    ) -> bool:
        """
        Indica si la solución final supera la puntuación inicial.
        """
        return self.improvement > 0.0

    @property
    def unchanged(
        self,
    ) -> bool:
        """
        Indica si la puntuación final coincide con la inicial.
        """
        return abs(
            self.improvement
        ) <= 1e-12

    @property
    def worsened(
        self,
    ) -> bool:
        """
        Indica si la solución final es peor que la inicial.

        En el pipeline estable del proyecto esta propiedad debería
        devolver siempre False.
        """
        return self.improvement < 0.0

    @property
    def average_evaluations_per_iteration(
        self,
    ) -> float:
        """
        Promedio de candidatos evaluados por movimiento aceptado.

        Cuando no hubo movimientos, devuelve el total de evaluaciones
        como referencia.
        """
        if self.iterations <= 0:
            return float(
                self.total_evaluations
            )

        return (
            self.total_evaluations
            / self.iterations
        )

    # ========================================================
    # Serialización
    # ========================================================

    def summary(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve un resumen compacto de la optimización.
        """
        data = super().summary()

        data.update(
            {
                "optimized": True,
                "improved": self.improved,
                "unchanged": self.unchanged,
                "worsened": self.worsened,
                "accepted_movements": (
                    self.accepted_movements
                ),
                "average_evaluations_per_iteration": (
                    self.average_evaluations_per_iteration
                ),
            }
        )

        return data

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable completa.

        Amplía la serialización común de BaseReportResult con el
        historial específico del optimizador.
        """
        data = super().as_dict()

        data.update(
            {
                "improved": self.improved,
                "unchanged": self.unchanged,
                "worsened": self.worsened,

                "accepted_movements": (
                    self.accepted_movements
                ),

                "has_movements": (
                    self.has_movements
                ),

                "average_evaluations_per_iteration": (
                    self.average_evaluations_per_iteration
                ),

                "history": (
                    self._history.as_dict()
                ),
            }
        )

        return data

    # ========================================================
    # Constructores auxiliares
    # ========================================================

    @classmethod
    def from_history(
        cls,
        teams: Sequence[Team],
        objective_result: ObjectiveResult,
        history: OptimizationHistory,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> OptimizationResult:
        """
        Constructor explícito equivalente al constructor principal.

        Puede resultar útil para fábricas, servicios de aplicación o
        futuras capas de persistencia.
        """
        return cls(
            teams=teams,
            objective_result=objective_result,
            history=history,
            title=title,
            metadata=metadata,
        )

    # ========================================================
    # Métodos especiales
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"mode={self.mode.value!r}, "
            f"teams={self.team_count}, "
            f"players={self.player_count}, "
            f"initial_score={self.initial_score:.2f}, "
            f"final_score={self.final_score:.2f}, "
            f"improvement={self.improvement:+.2f}, "
            f"iterations={self.iterations}, "
            f"evaluations={self.total_evaluations}, "
            f"elapsed_ms={self.elapsed_ms:.2f})"
        )
