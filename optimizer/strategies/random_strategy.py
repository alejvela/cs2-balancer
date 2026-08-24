from __future__ import annotations

import random
from collections.abc import Sequence

from models.team import Team
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.strategies.search_result import SearchResult
from optimizer.strategies.search_strategy import SearchStrategy


class RandomStrategy(SearchStrategy):
    """
    Evalúa únicamente un subconjunto aleatorio de movimientos.

    Es especialmente útil cuando el vecindario contiene miles de
    movimientos y no resulta rentable evaluarlos todos.
    """

    def __init__(
        self,
        sample_size: int = 100,
        minimum_improvement: float = 0.0,
    ) -> None:

        if sample_size <= 0:
            raise ValueError(
                "sample_size must be greater than zero."
            )

        if minimum_improvement < 0:
            raise ValueError(
                "minimum_improvement cannot be negative."
            )

        self.sample_size = sample_size
        self.minimum_improvement = minimum_improvement

    @property
    def name(self) -> str:
        return "Random"

    def search(
        self,
        neighborhood: Neighborhood,
        teams: Sequence[Team],
        evaluator: MoveEvaluator,
        current_score: float,
    ) -> SearchResult:

        team_list = self._validate_inputs(
            neighborhood=neighborhood,
            teams=teams,
            evaluator=evaluator,
        )

        start_time = self._start_timer()

        current_score = float(current_score)

        evaluations = 0

        best_move = None
        best_score = current_score

        #
        # Tomamos una muestra del vecindario.
        #
        # Actualmente sample() devuelve los primeros k movimientos.
        # Más adelante implementaremos el muestreo aleatorio real.
        #
        moves = list(
            neighborhood.sample(
                team_list,
                self.sample_size,
            )
        )

        random.shuffle(moves)

        for move in moves:

            evaluation = self._evaluate(
                evaluator=evaluator,
                move=move,
                teams=team_list,
            )

            evaluations += 1

            candidate_score = float(
                evaluation.score
            )

            improvement = (
                candidate_score
                - current_score
            )

            if improvement < self.minimum_improvement:
                continue

            if candidate_score > best_score:

                best_move = move
                best_score = candidate_score

        return self._build_result(
            move=best_move,
            score_before=current_score,
            score_after=best_score,
            evaluations=evaluations,
            start_time=start_time,
        )

    def __repr__(self):

        return (
            f"{self.__class__.__name__}("
            f"sample_size={self.sample_size}, "
            f"minimum_improvement={self.minimum_improvement})"
        )
