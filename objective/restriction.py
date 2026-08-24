from __future__ import annotations

from abc import ABC, abstractmethod

from objective.restriction_result import RestrictionResult
from scoring.scoring_model import ScoringModel


class Restriction(ABC):
    """
    Clase base para todas las restricciones del motor.

    Cada restricción evalúa una característica concreta
    del reparto de equipos y devuelve un RestrictionResult.
    """

    def __init__(
        self,
        weight: float = 1.0,
        scoring_model: ScoringModel | None = None
    ):

        if weight <= 0:
            raise ValueError(
                "weight must be greater than zero."
            )

        self.weight = weight
        self.scoring_model = scoring_model

    # -----------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    # -----------------------------------------------------

    @abstractmethod
    def evaluate(self, teams) -> RestrictionResult:
        """
        Evalúa la restricción y devuelve un RestrictionResult.
        """
        ...

    # -----------------------------------------------------

    def __repr__(self):

        return (
            f"{self.__class__.__name__}"
            f"(weight={self.weight})"
        )
