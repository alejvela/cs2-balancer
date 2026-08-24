from __future__ import annotations

from dataclasses import dataclass

from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.strategies.search_strategy import SearchStrategy


@dataclass(slots=True)
class OptimizationPhase:
    """
    Representa una fase del proceso de optimización.

    Cada fase define:

    - El nombre de la fase.
    - El vecindario que genera movimientos.
    - La estrategia utilizada para buscar movimientos.
    - El número máximo de iteraciones.
    - Si la fase está habilitada.
    """

    name: str

    neighborhood: Neighborhood

    strategy: SearchStrategy

    max_iterations: int = 100

    enabled: bool = True

    stop_when_no_move: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError(
                "name cannot be empty."
            )

        if self.neighborhood is None:
            raise ValueError(
                "neighborhood cannot be None."
            )

        if self.strategy is None:
            raise ValueError(
                "strategy cannot be None."
            )

        if self.max_iterations <= 0:
            raise ValueError(
                "max_iterations must be greater than zero."
            )

        self.name = self.name.strip()

    def reset(self) -> None:
        """
        Reinicia el estado interno de la estrategia.

        Algunas estrategias, como SimulatedAnnealingStrategy,
        mantienen estado entre iteraciones.
        """
        reset_method = getattr(
            self.strategy,
            "reset",
            None,
        )

        if callable(reset_method):
            reset_method()

    @property
    def neighborhood_name(self) -> str:
        """
        Devuelve un nombre legible para el vecindario.
        """
        name = getattr(
            self.neighborhood,
            "name",
            None,
        )

        if name:
            return str(name)

        return self.neighborhood.__class__.__name__

    @property
    def strategy_name(self) -> str:
        """
        Devuelve el nombre legible de la estrategia.
        """
        return self.strategy.name

    def as_dict(self) -> dict:
        """
        Devuelve una representación serializable de la fase.
        """
        return {
            "name": self.name,
            "neighborhood": self.neighborhood_name,
            "strategy": self.strategy_name,
            "max_iterations": self.max_iterations,
            "enabled": self.enabled,
            "stop_when_no_move": self.stop_when_no_move,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"neighborhood='{self.neighborhood_name}', "
            f"strategy='{self.strategy_name}', "
            f"max_iterations={self.max_iterations}, "
            f"enabled={self.enabled})"
        )
