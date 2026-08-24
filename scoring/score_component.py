from __future__ import annotations

from abc import ABC, abstractmethod

from models.player import Player


class ScoreComponent(ABC):
    """
    Contrato base para los componentes del ScoringModel.

    Cada componente evalúa una característica del jugador y devuelve
    una puntuación normalizada entre 0 y 100.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre único del componente.
        """
        ...

    @abstractmethod
    def score(
        self,
        player: Player,
    ) -> float:
        """
        Devuelve una puntuación entre 0 y 100.
        """
        ...

    def __call__(
        self,
        player: Player,
    ) -> float:
        return self.score(player)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}')"
        )
