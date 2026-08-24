from __future__ import annotations

from dataclasses import dataclass

from objective.objective_result import ObjectiveResult
from optimizer.moves.move import Move


@dataclass(slots=True)
class EvaluationResult:
    """
    Resultado de evaluar una distribución de equipos.

    Puede representar:

    - La evaluación de un movimiento concreto.
    - La evaluación del estado actual, en cuyo caso `move` será None.
    """

    move: Move | None

    objective_result: ObjectiveResult

    @property
    def score(self) -> float:
        """
        Devuelve la puntuación global obtenida.
        """
        return self.objective_result.score

    @property
    def penalty(self) -> float:
        """
        Devuelve la penalización total.
        """
        return self.objective_result.penalty

    @property
    def restrictions(self):
        """
        Devuelve los resultados de las restricciones evaluadas.
        """
        return self.objective_result.restrictions

    @property
    def is_valid(self) -> bool:
        """
        Considera válida una evaluación sin penalizaciones.

        Esta propiedad será especialmente útil para restricciones
        estrictas como TeamSizeRestriction.
        """
        return self.penalty <= 0.0

    def get_restriction(self, name: str):
        """
        Devuelve el resultado de una restricción por su nombre.
        """
        return self.objective_result.get(name)

    def as_dict(self) -> dict:
        """
        Devuelve una representación serializable del resultado.
        """
        move_description = None

        if self.move is not None:
            move_description = repr(self.move)

        return {
            "move": move_description,
            "score": self.score,
            "penalty": self.penalty,
            "is_valid": self.is_valid,
            "objective": self.objective_result.as_dict(),
        }

    def __repr__(self) -> str:
        move_name = (
            repr(self.move)
            if self.move is not None
            else "CurrentSolution"
        )

        return (
            f"EvaluationResult("
            f"move={move_name}, "
            f"score={self.score:.2f}, "
            f"penalty={self.penalty:.2f})"
        )
