from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator

from optimizer.optimization_iteration import OptimizationIteration


class OptimizationHistory:
    """
    Almacena el historial completo de movimientos aceptados durante
    una optimización.

    Permite consultar:

    - Número total de iteraciones.
    - Puntuación inicial y final.
    - Mejora total.
    - Evaluaciones realizadas.
    - Tiempo total de búsqueda.
    - Iteraciones agrupadas por fase, estrategia o vecindario.
    """

    def __init__(
        self,
        iterations: Iterable[OptimizationIteration] | None = None,
    ) -> None:
        self._iterations: list[OptimizationIteration] = []

        if iterations is not None:
            for iteration in iterations:
                self.add(iteration)

    def add(
        self,
        iteration: OptimizationIteration,
    ) -> None:
        """
        Añade una iteración al historial.
        """
        if iteration is None:
            raise ValueError(
                "iteration cannot be None."
            )

        if not isinstance(iteration, OptimizationIteration):
            raise TypeError(
                "iteration must be an OptimizationIteration instance."
            )

        self._iterations.append(iteration)

    def extend(
        self,
        iterations: Iterable[OptimizationIteration],
    ) -> None:
        """
        Añade varias iteraciones al historial.
        """
        if iterations is None:
            raise ValueError(
                "iterations cannot be None."
            )

        for iteration in iterations:
            self.add(iteration)

    def clear(self) -> None:
        """
        Elimina todo el historial.
        """
        self._iterations.clear()

    @property
    def iterations(self) -> tuple[OptimizationIteration, ...]:
        """
        Devuelve una vista inmutable de las iteraciones.
        """
        return tuple(self._iterations)

    @property
    def count(self) -> int:
        """
        Número total de movimientos aceptados.
        """
        return len(self._iterations)

    @property
    def is_empty(self) -> bool:
        return not self._iterations

    @property
    def initial_score(self) -> float | None:
        """
        Puntuación existente antes de la primera iteración.

        Devuelve None cuando el historial está vacío.
        """
        if self.is_empty:
            return None

        return self._iterations[0].score_before

    @property
    def final_score(self) -> float | None:
        """
        Puntuación obtenida después de la última iteración.

        Devuelve None cuando el historial está vacío.
        """
        if self.is_empty:
            return None

        return self._iterations[-1].score_after

    @property
    def total_improvement(self) -> float:
        """
        Diferencia entre la puntuación final y la inicial.
        """
        if self.is_empty:
            return 0.0

        return float(self.final_score - self.initial_score)

    @property
    def positive_improvement(self) -> float:
        """
        Suma de todas las mejoras positivas realizadas.
        """
        return sum(
            iteration.improvement
            for iteration in self._iterations
            if iteration.improvement > 0
        )

    @property
    def negative_improvement(self) -> float:
        """
        Suma de todos los movimientos que empeoraron temporalmente
        la solución.

        El resultado será cero o negativo.
        """
        return sum(
            iteration.improvement
            for iteration in self._iterations
            if iteration.improvement < 0
        )

    @property
    def improved_iterations(self) -> int:
        """
        Número de iteraciones que mejoraron la puntuación.
        """
        return sum(
            1
            for iteration in self._iterations
            if iteration.improved
        )

    @property
    def non_improving_iterations(self) -> int:
        """
        Número de movimientos aceptados que no mejoraron la puntuación.

        Suele utilizarse con estrategias como Simulated Annealing.
        """
        return self.count - self.improved_iterations

    @property
    def total_evaluations(self) -> int:
        """
        Número total de movimientos evaluados durante la optimización.
        """
        return sum(
            iteration.evaluations
            for iteration in self._iterations
        )

    @property
    def total_elapsed(self) -> float:
        """
        Tiempo total empleado por las estrategias, en segundos.
        """
        return sum(
            iteration.elapsed
            for iteration in self._iterations
        )

    @property
    def total_elapsed_ms(self) -> float:
        """
        Tiempo total empleado, en milisegundos.
        """
        return self.total_elapsed * 1000.0

    @property
    def average_improvement(self) -> float:
        """
        Mejora media por movimiento aceptado.
        """
        if self.is_empty:
            return 0.0

        return self.total_improvement / self.count

    @property
    def average_evaluations(self) -> float:
        """
        Número medio de evaluaciones por iteración aceptada.
        """
        if self.is_empty:
            return 0.0

        return self.total_evaluations / self.count

    @property
    def average_elapsed_ms(self) -> float:
        """
        Tiempo medio por iteración aceptada, en milisegundos.
        """
        if self.is_empty:
            return 0.0

        return self.total_elapsed_ms / self.count

    @property
    def best_iteration(self) -> OptimizationIteration | None:
        """
        Devuelve la iteración con mayor mejora positiva.
        """
        if self.is_empty:
            return None

        return max(
            self._iterations,
            key=lambda iteration: iteration.improvement,
        )

    @property
    def worst_iteration(self) -> OptimizationIteration | None:
        """
        Devuelve la iteración con menor mejora.

        Puede ser especialmente útil para analizar movimientos aceptados
        por Simulated Annealing.
        """
        if self.is_empty:
            return None

        return min(
            self._iterations,
            key=lambda iteration: iteration.improvement,
        )

    def by_phase(
        self,
        phase_name: str,
    ) -> tuple[OptimizationIteration, ...]:
        """
        Devuelve las iteraciones pertenecientes a una fase.
        """
        normalized_name = self._normalize_name(
            phase_name,
            "phase_name",
        )

        return tuple(
            iteration
            for iteration in self._iterations
            if iteration.phase.casefold() == normalized_name
        )

    def by_strategy(
        self,
        strategy_name: str,
    ) -> tuple[OptimizationIteration, ...]:
        """
        Devuelve las iteraciones ejecutadas por una estrategia.
        """
        normalized_name = self._normalize_name(
            strategy_name,
            "strategy_name",
        )

        return tuple(
            iteration
            for iteration in self._iterations
            if iteration.strategy.casefold() == normalized_name
        )

    def by_neighborhood(
        self,
        neighborhood_name: str,
    ) -> tuple[OptimizationIteration, ...]:
        """
        Devuelve las iteraciones asociadas a un vecindario.
        """
        normalized_name = self._normalize_name(
            neighborhood_name,
            "neighborhood_name",
        )

        return tuple(
            iteration
            for iteration in self._iterations
            if iteration.neighborhood.casefold() == normalized_name
        )

    def phase_summary(self) -> dict[str, dict]:
        """
        Devuelve métricas agregadas por fase.
        """
        grouped: dict[str, list[OptimizationIteration]] = defaultdict(list)

        for iteration in self._iterations:
            grouped[iteration.phase].append(iteration)

        return {
            phase: self._summarize_group(iterations)
            for phase, iterations in grouped.items()
        }

    def strategy_summary(self) -> dict[str, dict]:
        """
        Devuelve métricas agregadas por estrategia.
        """
        grouped: dict[str, list[OptimizationIteration]] = defaultdict(list)

        for iteration in self._iterations:
            grouped[iteration.strategy].append(iteration)

        return {
            strategy: self._summarize_group(iterations)
            for strategy, iterations in grouped.items()
        }

    def neighborhood_summary(self) -> dict[str, dict]:
        """
        Devuelve métricas agregadas por vecindario.
        """
        grouped: dict[str, list[OptimizationIteration]] = defaultdict(list)

        for iteration in self._iterations:
            grouped[iteration.neighborhood].append(iteration)

        return {
            neighborhood: self._summarize_group(iterations)
            for neighborhood, iterations in grouped.items()
        }

    def counts_by_phase(self) -> dict[str, int]:
        return dict(
            Counter(
                iteration.phase
                for iteration in self._iterations
            )
        )

    def counts_by_strategy(self) -> dict[str, int]:
        return dict(
            Counter(
                iteration.strategy
                for iteration in self._iterations
            )
        )

    def counts_by_neighborhood(self) -> dict[str, int]:
        return dict(
            Counter(
                iteration.neighborhood
                for iteration in self._iterations
            )
        )

    def as_dict(self) -> dict:
        """
        Devuelve una representación serializable del historial.
        """
        return {
            "count": self.count,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "total_improvement": self.total_improvement,
            "positive_improvement": self.positive_improvement,
            "negative_improvement": self.negative_improvement,
            "improved_iterations": self.improved_iterations,
            "non_improving_iterations": self.non_improving_iterations,
            "total_evaluations": self.total_evaluations,
            "total_elapsed": self.total_elapsed,
            "total_elapsed_ms": self.total_elapsed_ms,
            "average_improvement": self.average_improvement,
            "average_evaluations": self.average_evaluations,
            "average_elapsed_ms": self.average_elapsed_ms,
            "counts_by_phase": self.counts_by_phase(),
            "counts_by_strategy": self.counts_by_strategy(),
            "counts_by_neighborhood": self.counts_by_neighborhood(),
            "phase_summary": self.phase_summary(),
            "strategy_summary": self.strategy_summary(),
            "neighborhood_summary": self.neighborhood_summary(),
            "iterations": [
                iteration.as_dict()
                for iteration in self._iterations
            ],
        }

    @staticmethod
    def _summarize_group(
        iterations: list[OptimizationIteration],
    ) -> dict:
        """
        Construye el resumen de un grupo de iteraciones.
        """
        if not iterations:
            return {
                "iterations": 0,
                "improved_iterations": 0,
                "evaluations": 0,
                "elapsed": 0.0,
                "elapsed_ms": 0.0,
                "improvement": 0.0,
            }

        elapsed = sum(
            iteration.elapsed
            for iteration in iterations
        )

        return {
            "iterations": len(iterations),
            "improved_iterations": sum(
                1
                for iteration in iterations
                if iteration.improved
            ),
            "evaluations": sum(
                iteration.evaluations
                for iteration in iterations
            ),
            "elapsed": elapsed,
            "elapsed_ms": elapsed * 1000.0,
            "improvement": sum(
                iteration.improvement
                for iteration in iterations
            ),
            "score_before": iterations[0].score_before,
            "score_after": iterations[-1].score_after,
        }

    @staticmethod
    def _normalize_name(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized.casefold()

    def __iter__(self) -> Iterator[OptimizationIteration]:
        return iter(self._iterations)

    def __len__(self) -> int:
        return len(self._iterations)

    def __getitem__(
        self,
        index: int,
    ) -> OptimizationIteration:
        return self._iterations[index]

    def __repr__(self) -> str:
        initial = (
            f"{self.initial_score:.2f}"
            if self.initial_score is not None
            else "None"
        )

        final = (
            f"{self.final_score:.2f}"
            if self.final_score is not None
            else "None"
        )

        return (
            f"{self.__class__.__name__}("
            f"iterations={self.count}, "
            f"score={initial}->{final}, "
            f"improvement={self.total_improvement:+.2f}, "
            f"evaluations={self.total_evaluations}, "
            f"elapsed_ms={self.total_elapsed_ms:.2f})"
        )
