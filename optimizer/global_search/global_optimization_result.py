from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.team import Team


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalOptimizationResult:
    """
    Resultado de una búsqueda GLOBAL.

    optimality_proven:
        True únicamente cuando todo el espacio relevante ha sido
        explorado o podado de forma matemáticamente segura.

    stopped_by_limit:
        True si la búsqueda terminó por tiempo, nodos o evaluaciones.

    incumbent_improved:
        Indica si GLOBAL consiguió superar la solución inicial.
    """

    teams: tuple[Team, ...]

    score: float

    initial_incumbent_score: float

    nodes_visited: int

    complete_solutions_evaluated: int

    pruned_nodes: int

    capacity_prunes: int

    seed_prunes: int

    bound_prunes: int

    elapsed_seconds: float

    optimality_proven: bool

    stopped_by_limit: bool

    stop_reason: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "teams",
            tuple(self.teams),
        )

    @property
    def incumbent_improved(
        self,
    ) -> bool:
        return (
            self.score
            > self.initial_incumbent_score
        )

    @property
    def improvement(
        self,
    ) -> float:
        return (
            self.score
            - self.initial_incumbent_score
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "score": self.score,
            "initial_incumbent_score": (
                self.initial_incumbent_score
            ),
            "improvement": self.improvement,
            "incumbent_improved": (
                self.incumbent_improved
            ),
            "nodes_visited": (
                self.nodes_visited
            ),
            "complete_solutions_evaluated": (
                self.complete_solutions_evaluated
            ),
            "pruned_nodes": (
                self.pruned_nodes
            ),
            "capacity_prunes": (
                self.capacity_prunes
            ),
            "seed_prunes": (
                self.seed_prunes
            ),
            "bound_prunes": (
                self.bound_prunes
            ),
            "elapsed_seconds": (
                self.elapsed_seconds
            ),
            "optimality_proven": (
                self.optimality_proven
            ),
            "stopped_by_limit": (
                self.stopped_by_limit
            ),
            "stop_reason": (
                self.stop_reason
            ),
        }
