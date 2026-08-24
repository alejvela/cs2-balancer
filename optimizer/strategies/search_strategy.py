from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from time import perf_counter

from evaluation.evaluation_result import EvaluationResult
from models.team import Team
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.moves.move import Move
from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.strategies.search_result import SearchResult


class SearchStrategy(ABC):
    """
    Clase base para todas las estrategias de búsqueda.

    Una estrategia recibe:

        - Un Neighborhood que genera movimientos.
        - La distribución actual de equipos.
        - Un MoveEvaluator para evaluar cada movimiento.
        - La puntuación actual de la solución.

    Y devuelve siempre un SearchResult.

    Las clases derivadas deciden:

        - Qué movimientos evaluar.
        - En qué orden evaluarlos.
        - Cuándo detener la búsqueda.
        - Qué movimiento seleccionar.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre legible de la estrategia.
        """
        ...

    @abstractmethod
    def search(
        self,
        neighborhood: Neighborhood,
        teams: Sequence[Team],
        evaluator: MoveEvaluator,
        current_score: float,
    ) -> SearchResult:
        """
        Busca un movimiento utilizando el Neighborhood recibido.

        Debe devolver un SearchResult incluso cuando no encuentre
        ningún movimiento válido.
        """
        ...

    @staticmethod
    def _start_timer() -> float:
        """
        Inicia la medición de tiempo de la búsqueda.
        """
        return perf_counter()

    @staticmethod
    def _elapsed(start_time: float) -> float:
        """
        Devuelve el tiempo transcurrido en segundos.
        """
        return perf_counter() - start_time

    @staticmethod
    def _evaluate(
        evaluator: MoveEvaluator,
        move: Move,
        teams: Sequence[Team],
    ) -> EvaluationResult:
        """
        Evalúa temporalmente un movimiento.

        La aplicación y reversión del movimiento son responsabilidad
        de MoveEvaluator.
        """
        return evaluator.evaluate(
            move=move,
            teams=teams,
        )

    def _build_result(
        self,
        move: Move | None,
        score_before: float,
        score_after: float,
        evaluations: int,
        start_time: float,
    ) -> SearchResult:
        """
        Construye el SearchResult final de la búsqueda.
        """
        elapsed = self._elapsed(start_time)

        if move is None:
            return SearchResult.no_move(
                current_score=score_before,
                evaluations=evaluations,
                elapsed=elapsed,
            )

        return SearchResult.from_move(
            move=move,
            score_before=score_before,
            score_after=score_after,
            evaluations=evaluations,
            elapsed=elapsed,
        )

    def _no_move_result(
        self,
        current_score: float,
        evaluations: int,
        start_time: float,
    ) -> SearchResult:
        """
        Atajo para construir un resultado sin movimiento.
        """
        return SearchResult.no_move(
            current_score=current_score,
            evaluations=evaluations,
            elapsed=self._elapsed(start_time),
        )

    @staticmethod
    def _validate_inputs(
        neighborhood: Neighborhood,
        teams: Sequence[Team],
        evaluator: MoveEvaluator,
    ) -> list[Team]:
        """
        Valida los argumentos comunes de todas las estrategias.

        Devuelve los equipos convertidos a lista para que puedan
        recorrerse varias veces durante la búsqueda.
        """
        if neighborhood is None:
            raise ValueError(
                "neighborhood cannot be None."
            )

        if evaluator is None:
            raise ValueError(
                "evaluator cannot be None."
            )

        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        team_list = list(teams)

        if not team_list:
            raise ValueError(
                "At least one team is required."
            )

        return team_list

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(name='{self.name}')"
        )
