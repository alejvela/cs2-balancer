from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from application.results.base_report_result import (
    BaseReportResult,
)
from application.results.report_mode import (
    ReportMode,
)
from models.team import Team
from objective.objective_result import ObjectiveResult


class EmptyEvaluationHistory:
    """
    Historial vacío utilizado por EvaluationResult.

    Permite que las capas de presentación trabajen con una interfaz
    similar a OptimizationHistory sin tener que comprobar si history
    es None o una tupla.

    Una evaluación de equipos predeterminados:

        - No aplica movimientos.
        - No contiene iteraciones.
        - No modifica los equipos.
        - Solo ejecuta una evaluación objetiva.
    """

    __slots__ = ()

    @property
    def is_empty(
        self,
    ) -> bool:
        return True

    @property
    def count(
        self,
    ) -> int:
        return 0

    @property
    def total_evaluations(
        self,
    ) -> int:
        return 1

    @property
    def total_elapsed(
        self,
    ) -> float:
        return 0.0

    @property
    def total_elapsed_ms(
        self,
    ) -> float:
        return 0.0

    @property
    def initial_score(
        self,
    ) -> None:
        return None

    @property
    def final_score(
        self,
    ) -> None:
        return None

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "is_empty": True,
            "count": 0,
            "total_evaluations": 1,
            "total_elapsed": 0.0,
            "total_elapsed_ms": 0.0,
            "initial_score": None,
            "final_score": None,
            "iterations": [],
        }

    def __iter__(
        self,
    ) -> Iterator[Any]:
        return iter(())

    def __len__(
        self,
    ) -> int:
        return 0

    def __bool__(
        self,
    ) -> bool:
        return False

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            "count=0, "
            "is_empty=True)"
        )


_EMPTY_EVALUATION_HISTORY = EmptyEvaluationHistory()


class EvaluationResult(BaseReportResult):
    """
    Resultado de evaluar equipos previamente definidos.

    Los equipos proceden de una asignación externa, normalmente de la
    columna Team del CSV, y deben conservarse sin modificaciones.

    A diferencia de OptimizationResult:

        - No se ejecuta SnakeDraftGenerator.
        - No se ejecuta LocalOptimizer.
        - No se aplican movimientos.
        - No existe mejora entre una solución inicial y final.
        - La puntuación inicial coincide con la final.
        - El historial siempre está vacío.

    La clase hereda de BaseReportResult toda la funcionalidad común:

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
        - team_sizes
        - acceso a equipos
        - acceso a restricciones
        - serialización común
    """

    __slots__ = (
        "_elapsed_ms",
        "_total_evaluations",
    )

    def __init__(
        self,
        teams: Sequence[Team],
        objective_result: ObjectiveResult,
        elapsed_ms: float = 0.0,
        total_evaluations: int = 1,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Construye el resultado de una evaluación.

        Args:
            teams:
                Equipos predeterminados evaluados.

            objective_result:
                Resultado producido por ObjectiveEngine.

            elapsed_ms:
                Tiempo total de evaluación en milisegundos.

            total_evaluations:
                Número de evaluaciones realizadas. Normalmente será 1.

            title:
                Título opcional para informes.

            metadata:
                Información adicional del evento o ejecución.
        """
        self._elapsed_ms = self._validate_non_negative_number(
            value=elapsed_ms,
            field_name="elapsed_ms",
        )

        self._total_evaluations = self._validate_positive_integer(
            value=total_evaluations,
            field_name="total_evaluations",
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

    # ========================================================
    # Modalidad
    # ========================================================

    @property
    def mode(
        self,
    ) -> ReportMode:
        """
        Indica que los equipos estaban previamente asignados.
        """
        return ReportMode.PREASSIGNED

    # ========================================================
    # Puntuación
    # ========================================================

    @property
    def initial_score(
        self,
    ) -> float:
        """
        La puntuación inicial coincide con la final porque no existe
        un proceso de optimización.
        """
        return self.final_score

    # ========================================================
    # Historial y ejecución
    # ========================================================

    @property
    def history(
        self,
    ) -> EmptyEvaluationHistory:
        """
        Devuelve un historial vacío compatible con los exportadores.
        """
        return _EMPTY_EVALUATION_HISTORY

    @property
    def iterations(
        self,
    ) -> int:
        """
        No existen movimientos aceptados.
        """
        return 0

    @property
    def total_evaluations(
        self,
    ) -> int:
        """
        Número de evaluaciones realizadas por el ObjectiveEngine.
        """
        return self._total_evaluations

    @property
    def elapsed_ms(
        self,
    ) -> float:
        """
        Tiempo consumido por la evaluación, en milisegundos.
        """
        return self._elapsed_ms

    # ========================================================
    # Información específica de evaluación
    # ========================================================

    @property
    def composition_preserved(
        self,
    ) -> bool:
        """
        Indica que la composición proporcionada no fue modificada.
        """
        return True

    @property
    def movements_applied(
        self,
    ) -> int:
        return 0

    @property
    def has_movements(
        self,
    ) -> bool:
        return False

    @property
    def improved(
        self,
    ) -> bool:
        return False

    @property
    def unchanged(
        self,
    ) -> bool:
        return True

    @property
    def worsened(
        self,
    ) -> bool:
        return False

    # ========================================================
    # Serialización
    # ========================================================

    def summary(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve un resumen compacto de la evaluación.
        """
        data = super().summary()

        data.update(
            {
                "optimized": False,
                "evaluation_only": True,
                "composition_preserved": (
                    self.composition_preserved
                ),
                "movements_applied": 0,
            }
        )

        return data

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable completa.
        """
        data = super().as_dict()

        data.update(
            {
                "composition_preserved": (
                    self.composition_preserved
                ),

                "movements_applied": (
                    self.movements_applied
                ),

                "has_movements": (
                    self.has_movements
                ),

                "improved": self.improved,
                "unchanged": self.unchanged,
                "worsened": self.worsened,

                "history": (
                    self.history.as_dict()
                ),
            }
        )

        return data

    # ========================================================
    # Constructores auxiliares
    # ========================================================

    @classmethod
    def from_objective_result(
        cls,
        teams: Sequence[Team],
        objective_result: ObjectiveResult,
        elapsed_ms: float = 0.0,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> EvaluationResult:
        """
        Construye un EvaluationResult desde ObjectiveEngine.evaluate().

        Mantiene una firma equivalente al constructor auxiliar de la
        antigua clase TeamEvaluationResult.
        """
        return cls(
            teams=teams,
            objective_result=objective_result,
            elapsed_ms=elapsed_ms,
            total_evaluations=1,
            title=title,
            metadata=metadata,
        )

    @classmethod
    def create(
        cls,
        teams: Sequence[Team],
        objective_result: ObjectiveResult,
        elapsed_ms: float = 0.0,
        title: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> EvaluationResult:
        """
        Alias más breve para servicios o fábricas de aplicación.
        """
        return cls.from_objective_result(
            teams=teams,
            objective_result=objective_result,
            elapsed_ms=elapsed_ms,
            title=title,
            metadata=metadata,
        )

    # ========================================================
    # Validaciones específicas
    # ========================================================

    @staticmethod
    def _validate_non_negative_number(
        value: Any,
        field_name: str,
    ) -> float:
        if isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        try:
            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise TypeError(
                f"{field_name} must be numeric."
            ) from error

        if numeric_value < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return numeric_value

    @staticmethod
    def _validate_positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return value

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
            f"score={self.final_score:.2f}, "
            f"penalty={self.penalty:.2f}, "
            f"balance={self.balance_label!r}, "
            f"evaluations={self.total_evaluations}, "
            f"elapsed_ms={self.elapsed_ms:.2f})"
        )
