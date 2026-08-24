from __future__ import annotations

import math
import random
from collections.abc import Sequence

from models.team import Team
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.strategies.search_result import SearchResult
from optimizer.strategies.search_strategy import SearchStrategy


class SimulatedAnnealingStrategy(SearchStrategy):
    """
    Estrategia de recocido simulado.

    Puede aceptar temporalmente movimientos que empeoran la puntuación,
    con el objetivo de escapar de óptimos locales.

    La probabilidad de aceptar un movimiento peor disminuye conforme
    baja la temperatura.

    Fórmula de aceptación:

        probability = exp(delta / temperature)

    donde:

        delta = candidate_score - current_score

    Si delta es positivo, el movimiento mejora y se acepta siempre.
    Si delta es negativo, puede aceptarse según la temperatura.
    """

    def __init__(
        self,
        initial_temperature: float = 5.0,
        cooling_rate: float = 0.95,
        minimum_temperature: float = 0.01,
        sample_size: int = 100,
        seed: int | None = None,
    ) -> None:
        if initial_temperature <= 0:
            raise ValueError(
                "initial_temperature must be greater than zero."
            )

        if not 0.0 < cooling_rate < 1.0:
            raise ValueError(
                "cooling_rate must be between 0 and 1."
            )

        if minimum_temperature <= 0:
            raise ValueError(
                "minimum_temperature must be greater than zero."
            )

        if minimum_temperature > initial_temperature:
            raise ValueError(
                "minimum_temperature cannot be greater "
                "than initial_temperature."
            )

        if sample_size <= 0:
            raise ValueError(
                "sample_size must be greater than zero."
            )

        self.initial_temperature = float(initial_temperature)
        self.cooling_rate = float(cooling_rate)
        self.minimum_temperature = float(minimum_temperature)
        self.sample_size = sample_size

        self._temperature = self.initial_temperature
        self._random = random.Random(seed)

    @property
    def name(self) -> str:
        return "Simulated Annealing"

    @property
    def temperature(self) -> float:
        """
        Temperatura actual de la estrategia.
        """
        return self._temperature

    @property
    def is_frozen(self) -> bool:
        """
        Indica si la temperatura ha alcanzado el mínimo configurado.
        """
        return self._temperature <= self.minimum_temperature

    def search(
        self,
        neighborhood: Neighborhood,
        teams: Sequence[Team],
        evaluator: MoveEvaluator,
        current_score: float,
    ) -> SearchResult:
        """
        Busca un movimiento dentro de una muestra del vecindario.

        Prioridad:

        1. Devuelve inmediatamente el primer movimiento que mejora.
        2. Si no encuentra una mejora, puede aceptar un movimiento peor
           según la temperatura y la probabilidad de aceptación.
        3. Si ningún movimiento es aceptado, devuelve un resultado vacío.
        """
        team_list = self._validate_inputs(
            neighborhood=neighborhood,
            teams=teams,
            evaluator=evaluator,
        )

        start_time = self._start_timer()

        current_score = float(current_score)
        evaluations = 0

        accepted_move = None
        accepted_score = current_score

        candidate_moves = list(
            neighborhood.sample(
                team_list,
                self.sample_size,
            )
        )

        self._random.shuffle(candidate_moves)

        for move in candidate_moves:
            evaluation = self._evaluate(
                evaluator=evaluator,
                move=move,
                teams=team_list,
            )

            evaluations += 1

            candidate_score = float(evaluation.score)
            delta = candidate_score - current_score

            # Las mejoras se aceptan siempre.
            if delta > 0:
                accepted_move = move
                accepted_score = candidate_score
                break

            # Un movimiento igual no aporta nada.
            if delta == 0:
                continue

            if self._accept_worse_move(delta):
                accepted_move = move
                accepted_score = candidate_score
                break

        self._cool_down()

        return self._build_result(
            move=accepted_move,
            score_before=current_score,
            score_after=accepted_score,
            evaluations=evaluations,
            start_time=start_time,
        )

    def _accept_worse_move(
        self,
        delta: float,
    ) -> bool:
        """
        Decide si se acepta un movimiento que empeora la puntuación.

        `delta` debe ser negativo.
        """
        if delta >= 0:
            return True

        if self._temperature <= 0:
            return False

        probability = math.exp(
            delta / self._temperature
        )

        return self._random.random() < probability

    def _cool_down(self) -> None:
        """
        Reduce la temperatura después de cada búsqueda.
        """
        self._temperature = max(
            self.minimum_temperature,
            self._temperature * self.cooling_rate,
        )

    def reset(self) -> None:
        """
        Restaura la temperatura inicial.

        Debe utilizarse antes de comenzar una nueva optimización si se
        reutiliza la misma instancia de la estrategia.
        """
        self._temperature = self.initial_temperature

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"temperature={self._temperature:.4f}, "
            f"initial_temperature={self.initial_temperature}, "
            f"cooling_rate={self.cooling_rate}, "
            f"minimum_temperature={self.minimum_temperature}, "
            f"sample_size={self.sample_size})"
        )
