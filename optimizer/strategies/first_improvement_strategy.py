from __future__ import annotations

from collections.abc import Sequence

from models.team import Team
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.strategies.search_result import SearchResult
from optimizer.strategies.search_strategy import SearchStrategy


class FirstImprovementStrategy(SearchStrategy):
    """
    Recorre los movimientos generados por un Neighborhood y devuelve
    el primero que mejora la puntuación actual.

    Es más rápida que ExhaustiveStrategy porque no evalúa necesariamente
    todos los movimientos. A cambio, no garantiza encontrar el mejor
    movimiento disponible.
    """

    def __init__(
        self,
        minimum_improvement: float = 0.0,
    ) -> None:
        if minimum_improvement < 0:
            raise ValueError(
                "minimum_improvement cannot be negative."
            )

        self.minimum_improvement = minimum_improvement

    @property
    def name(self) -> str:
        return "First Improvement"

    def search(
        self,
        neighborhood: Neighborhood,
        teams: Sequence[Team],
        evaluator: MoveEvaluator,
        current_score: float,
    ) -> SearchResult:
        """
        Devuelve el primer movimiento cuya mejora sea igual o superior
        al umbral configurado.
        """
        team_list = self._validate_inputs(
            neighborhood=neighborhood,
            teams=teams,
            evaluator=evaluator,
        )

        start_time = self._start_timer()

        evaluations = 0
        current_score = float(current_score)

        for move in neighborhood.iterate(team_list):
            evaluation = self._evaluate(
                evaluator=evaluator,
                move=move,
                teams=team_list,
            )

            evaluations += 1

            candidate_score = float(evaluation.score)
            improvement = candidate_score - current_score

            if improvement < self.minimum_improvement:
                continue

            if candidate_score > current_score:
                return self._build_result(
                    move=move,
                    score_before=current_score,
                    score_after=candidate_score,
                    evaluations=evaluations,
                    start_time=start_time,
                )

        return self._no_move_result(
            current_score=current_score,
            evaluations=evaluations,
            start_time=start_time,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"minimum_improvement={self.minimum_improvement})"
        )
