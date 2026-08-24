from __future__ import annotations

from dataclasses import dataclass

from optimizer.strategies.search_result import SearchResult


@dataclass(slots=True)
class OptimizationIteration:
    """
    Representa una iteración aceptada durante el proceso de optimización.

    Almacena:

    - La fase que estaba ejecutándose.
    - El número de iteración dentro de esa fase.
    - La estrategia utilizada.
    - El vecindario explorado.
    - El resultado de la búsqueda.

    Solo se deberían registrar iteraciones en las que se haya
    seleccionado y aplicado un movimiento.
    """

    phase: str

    iteration: int

    strategy: str

    neighborhood: str

    result: SearchResult

    def __post_init__(self) -> None:
        self.phase = self._validate_name(
            self.phase,
            "phase",
        )

        self.strategy = self._validate_name(
            self.strategy,
            "strategy",
        )

        self.neighborhood = self._validate_name(
            self.neighborhood,
            "neighborhood",
        )

        if self.iteration <= 0:
            raise ValueError(
                "iteration must be greater than zero."
            )

        if self.result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not self.result.has_move:
            raise ValueError(
                "An optimization iteration must contain a movement."
            )

    @property
    def move(self):
        """
        Devuelve el movimiento seleccionado en esta iteración.
        """
        return self.result.move

    @property
    def score_before(self) -> float:
        """
        Puntuación existente antes de aplicar el movimiento.
        """
        return self.result.score_before

    @property
    def score_after(self) -> float:
        """
        Puntuación obtenida después de aplicar el movimiento.
        """
        return self.result.score_after

    @property
    def improvement(self) -> float:
        """
        Diferencia entre la puntuación posterior y la anterior.

        Puede ser negativa cuando se utiliza una estrategia como
        Simulated Annealing.
        """
        return self.result.improvement

    @property
    def improved(self) -> bool:
        """
        Indica si el movimiento mejoró la puntuación.
        """
        return self.result.improved

    @property
    def evaluations(self) -> int:
        """
        Número de movimientos evaluados para encontrar el seleccionado.
        """
        return self.result.evaluations

    @property
    def elapsed(self) -> float:
        """
        Tiempo empleado por la estrategia, expresado en segundos.
        """
        return self.result.elapsed

    @property
    def elapsed_ms(self) -> float:
        """
        Tiempo empleado por la estrategia, expresado en milisegundos.
        """
        return self.result.elapsed_ms

    def as_dict(self) -> dict:
        """
        Devuelve una representación serializable de la iteración.
        """
        return {
            "phase": self.phase,
            "iteration": self.iteration,
            "strategy": self.strategy,
            "neighborhood": self.neighborhood,
            "move": (
                repr(self.move)
                if self.move is not None
                else None
            ),
            "score_before": self.score_before,
            "score_after": self.score_after,
            "improvement": self.improvement,
            "improved": self.improved,
            "evaluations": self.evaluations,
            "elapsed": self.elapsed,
            "elapsed_ms": self.elapsed_ms,
            "search_result": self.result.as_dict(),
        }

    @staticmethod
    def _validate_name(
        value: str,
        field_name: str,
    ) -> str:
        """
        Valida y normaliza los campos de texto.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"phase='{self.phase}', "
            f"iteration={self.iteration}, "
            f"strategy='{self.strategy}', "
            f"neighborhood='{self.neighborhood}', "
            f"score={self.score_before:.2f}"
            f"->{self.score_after:.2f}, "
            f"improvement={self.improvement:+.2f})"
        )
