"""GLOBAL search adapted to the existing public report contract."""

from __future__ import annotations

from typing import Any

from application.results.base_report_result import BaseReportResult
from application.results.report_mode import ReportMode
from models.numeric import finite_real
from optimizer.global_search.global_optimization_result import GlobalOptimizationResult
from optimizer.global_search.global_proof_certificate import GlobalProofCertificate


class GlobalReportResult(BaseReportResult):
    """
    Adapta GlobalOptimizationResult al contrato BaseReportResult.

    Esto permite que HtmlExporterV2 y el resto de la capa de informe
    trabajen directamente con la solución GLOBAL sin depender de un
    OptimizationHistory basado en movimientos locales.
    """

    __slots__ = (
        "_initial_score",
        "_global_result",
    )

    def __init__(
        self,
        teams,
        objective_result,
        initial_score: float | None,
        global_result: GlobalOptimizationResult,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if type(global_result) is not GlobalOptimizationResult:
            raise TypeError("global_result must be a GlobalOptimizationResult.")
        teams = tuple(teams)
        if len(teams) != len(global_result.teams) or any(
            left is not right for left, right in zip(teams, global_result.teams, strict=True)
        ):
            raise ValueError("Report teams must match the exact GLOBAL teams.")
        if finite_real(objective_result.score, "objective score") != global_result.score:
            raise ValueError("Report score must match the GLOBAL score.")
        self._initial_score = (
            finite_real(initial_score, "initial_score") if initial_score is not None else None
        )

        if self._initial_score != global_result.initial_incumbent_score:
            raise ValueError("Report initial_score must match the GLOBAL initial incumbent.")

        self._global_result = global_result

        super().__init__(
            teams=teams,
            objective_result=objective_result,
            title=title,
            metadata=(dict(metadata) if metadata is not None else {}),
        )

    @property
    def mode(self) -> ReportMode:
        return ReportMode.OPTIMIZED

    @property
    def initial_score(self) -> float | None:
        return self._initial_score

    @property
    def final_score(self) -> float:
        return float(self.objective_result.score)

    @property
    def score(self) -> float:
        return self.final_score

    @property
    def improvement(self) -> float | None:
        if self.initial_score is None:
            return None
        return self.final_score - self.initial_score

    @property
    def iterations(self) -> int:
        # GLOBAL no acepta movimientos locales.
        return 0

    @property
    def total_evaluations(self) -> int:
        return int(self._global_result.complete_solutions_evaluated)

    @property
    def elapsed_ms(self) -> float:
        return float(self._global_result.elapsed_seconds) * 1000.0

    @property
    def optimized(self) -> bool:
        return True

    @property
    def evaluation_only(self) -> bool:
        return False

    @property
    def history(self) -> tuple:
        # No existe historial de SwapMove en Branch & Bound.
        return tuple()

    @property
    def optimization_engine(self) -> str:
        return "GLOBAL"

    @property
    def optimality_proven(self) -> bool:
        return bool(self._global_result.optimality_proven)

    @property
    def nodes_visited(self) -> int:
        return int(self._global_result.nodes_visited)

    @property
    def complete_solutions_evaluated(self) -> int:
        return int(self._global_result.complete_solutions_evaluated)

    @property
    def pruned_nodes(self) -> int:
        return int(self._global_result.pruned_nodes)

    @property
    def bound_prunes(self) -> int:
        return int(self._global_result.bound_prunes)

    @property
    def global_stop_reason(self) -> str:
        return str(self._global_result.stop_reason)

    @property
    def search_exhausted(self) -> bool:
        return self._global_result.search_exhausted

    @property
    def proof_certificate(self) -> GlobalProofCertificate | None:
        return self._global_result.proof_certificate

    @property
    def initial_incumbent_score(self) -> float | None:
        return self._global_result.initial_incumbent_score

    @property
    def capacity_prunes(self) -> int:
        return int(self._global_result.capacity_prunes)

    @property
    def seed_prunes(self) -> int:
        return int(self._global_result.seed_prunes)

    @property
    def stopped_by_limit(self) -> bool:
        return bool(self._global_result.stopped_by_limit)

    @property
    def elapsed_seconds(self) -> float:
        return float(self._global_result.elapsed_seconds)

    @property
    def stop_reason(self) -> str:
        return self.global_stop_reason

    def __repr__(self) -> str:
        if self.initial_score is not None:
            return super().__repr__()
        return (
            f"{self.__class__.__name__}(score={self.final_score:.2f}, "
            f"initial_score={self.initial_score!r}, improvement={self.improvement!r})"
        )
