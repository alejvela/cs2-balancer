from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.numeric import finite_real
from models.team import Team
from optimizer.global_search.global_proof_certificate import GlobalProofCertificate


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

    initial_incumbent_score: float | None

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

    proof_certificate: GlobalProofCertificate | None = None

    def __post_init__(
        self,
    ) -> None:
        counters = (self.nodes_visited, self.complete_solutions_evaluated,
                    self.pruned_nodes, self.capacity_prunes, self.seed_prunes,
                    self.bound_prunes)
        if any(type(value) is not int for value in counters):
            raise TypeError("GLOBAL counters must be integers.")
        if any(value < 0 for value in counters):
            raise ValueError("GLOBAL counters must be nonnegative.")
        if self.capacity_prunes + self.seed_prunes + self.bound_prunes != self.pruned_nodes:
            raise ValueError("Prune breakdown must equal pruned_nodes.")
        if self.complete_solutions_evaluated + self.pruned_nodes > self.nodes_visited:
            raise ValueError("Evaluated and pruned nodes cannot exceed visited nodes.")
        if finite_real(self.elapsed_seconds, "elapsed_seconds") < 0:
            raise ValueError("elapsed_seconds must be nonnegative.")
        for name in ("optimality_proven", "stopped_by_limit"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a boolean.")
        limits = ("NODE_LIMIT", "EVALUATION_LIMIT", "TIME_LIMIT")
        if self.stop_reason not in (*limits, "SEARCH_EXHAUSTED", "PROOF_NOT_COMPLETED"):
            raise ValueError("Unknown GLOBAL stop_reason.")
        if self.optimality_proven and self.stopped_by_limit:
            raise ValueError("Budget termination cannot prove optimality.")
        if self.stopped_by_limit != (self.stop_reason in limits):
            raise ValueError("stop_reason must agree with stopped_by_limit.")
        if self.stop_reason == "PROOF_NOT_COMPLETED" and self.optimality_proven:
            raise ValueError("PROOF_NOT_COMPLETED cannot prove optimality.")
        finite_real(self.score, "score")
        if self.initial_incumbent_score is not None:
            finite_real(self.initial_incumbent_score, "initial_incumbent_score")
        if self.proof_certificate is not None:
            if type(self.proof_certificate) is not GlobalProofCertificate:
                raise TypeError("proof_certificate must be a GlobalProofCertificate.")
            if self.proof_certificate.search_exhausted == self.stopped_by_limit:
                raise ValueError("Certificate exhaustion must agree with operational termination.")
            if self.optimality_proven != self.proof_certificate.optimality_proven:
                raise ValueError("optimality_proven must agree with its certificate.")
        elif self.optimality_proven:
            raise ValueError("Optimality requires a proof certificate, not a stop label.")
        if self.optimality_proven and (self.stopped_by_limit or not self.search_exhausted):
            raise ValueError("Budget termination cannot prove optimality.")
        object.__setattr__(
            self,
            "teams",
            tuple(self.teams),
        )

    @property
    def search_exhausted(self) -> bool:
        if self.proof_certificate is not None:
            return self.proof_certificate.search_exhausted
        return self.stop_reason in ("SEARCH_EXHAUSTED", "PROOF_NOT_COMPLETED")

    @property
    def incumbent_improved(
        self,
    ) -> bool:
        return (
            self.initial_incumbent_score is not None
            and self.score
            > self.initial_incumbent_score
        )

    @property
    def improvement(
        self,
    ) -> float | None:
        if self.initial_incumbent_score is None:
            return None
        return (
            self.score
            - self.initial_incumbent_score
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "score": self.score,
            "search_exhausted": self.search_exhausted,
            "proof_certificate": self.proof_certificate.as_dict() if self.proof_certificate is not None else None,
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
