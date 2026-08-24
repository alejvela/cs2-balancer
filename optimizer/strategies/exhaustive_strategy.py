from __future__ import annotations

from collections.abc import Sequence

from models.team import Team
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.moves.move import Move
from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.strategies.search_result import SearchResult
from optimizer.strategies.search_strategy import SearchStrategy


class ExhaustiveStrategy(SearchStrategy):
    """
    Evalúa todos los movimientos generados por un Neighborhood
    y devuelve el que produce la mejor puntuación global.

    Esta estrategia garantiza encontrar el mejor movimiento disponible
    dentro del vecindario explorado, aunque puede ser más costosa que
    estrategias como FirstImprovementStrategy o RandomStrategy.
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
        return "Exhaustive"

    def search(
        self,
        neighborhood: Neighborhood,
        teams: Sequence[Team],
        evaluator: MoveEvaluator,
        current_score: float,
    ) -> SearchResult:
        """
        Recorre todos los movimientos del vecindario y selecciona
        el que obtiene la puntuación más alta.

        Solo devuelve un movimiento si la mejora respecto al estado
        actual es superior o igual a `minimum_improvement`.
        """
        team_list = self._validate_inputs(
            neighborhood=neighborhood,
            teams=teams,
            evaluator=evaluator,
        )

        start_time = self._start_timer()

        best_move: Move | None = None
        best_score = float(current_score)
        evaluations = 0

        for move in neighborhood.iterate(team_list):
            evaluation = self._evaluate(
                evaluator=evaluator,
                move=move,
                teams=team_list,
            )

            evaluations += 1

            candidate_score = float(evaluation.score)
            improvement = candidate_score - float(current_score)

            if improvement < self.minimum_improvement:
                continue

            if candidate_score > best_score:
                best_move = move
                best_score = candidate_score

        return self._build_result(
            move=best_move,
            score_before=float(current_score),
            score_after=best_score,
            evaluations=evaluations,
            start_time=start_time,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"minimum_improvement={self.minimum_improvement})"
        )
