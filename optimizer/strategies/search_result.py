from __future__ import annotations

from dataclasses import dataclass

from optimizer.moves.move import Move


@dataclass(slots=True)
class SearchResult:
    """
    Resultado producido por una estrategia de búsqueda.

    Contiene el movimiento seleccionado, la puntuación antes y después
    de aplicarlo y algunas métricas sobre el proceso de búsqueda.

    Si no se encuentra ningún movimiento aceptable:

        move = None
        score_after = score_before
    """

    move: Move | None

    score_before: float

    score_after: float

    evaluations: int = 0

    elapsed: float = 0.0

    @property
    def improved(self) -> bool:
        """
        Indica si la estrategia encontró un movimiento que mejora
        la puntuación actual.
        """
        return (
            self.move is not None
            and self.score_after > self.score_before
        )

    @property
    def has_move(self) -> bool:
        """
        Indica si la estrategia seleccionó algún movimiento.

        Es distinto de `improved`, porque determinadas estrategias,
        como Simulated Annealing, pueden aceptar temporalmente un
        movimiento que empeore la puntuación.
        """
        return self.move is not None

    @property
    def improvement(self) -> float:
        """
        Diferencia entre la puntuación posterior y la anterior.

        Puede ser negativa cuando una estrategia admite movimientos
        peores para escapar de un óptimo local.
        """
        return self.score_after - self.score_before

    @property
    def elapsed_ms(self) -> float:
        """
        Tiempo de búsqueda expresado en milisegundos.
        """
        return self.elapsed * 1000.0

    @classmethod
    def no_move(
        cls,
        current_score: float,
        evaluations: int = 0,
        elapsed: float = 0.0,
    ) -> SearchResult:
        """
        Construye un resultado sin movimiento seleccionado.
        """
        return cls(
            move=None,
            score_before=current_score,
            score_after=current_score,
            evaluations=evaluations,
            elapsed=elapsed,
        )

    @classmethod
    def from_move(
        cls,
        move: Move,
        score_before: float,
        score_after: float,
        evaluations: int = 0,
        elapsed: float = 0.0,
    ) -> SearchResult:
        """
        Construye un resultado asociado a un movimiento.
        """
        if move is None:
            raise ValueError(
                "move cannot be None. Use SearchResult.no_move() instead."
            )

        return cls(
            move=move,
            score_before=score_before,
            score_after=score_after,
            evaluations=evaluations,
            elapsed=elapsed,
        )

    def as_dict(self) -> dict:
        """
        Devuelve una representación serializable del resultado.
        """
        return {
            "move": repr(self.move) if self.move is not None else None,
            "score_before": self.score_before,
            "score_after": self.score_after,
            "improvement": self.improvement,
            "improved": self.improved,
            "has_move": self.has_move,
            "evaluations": self.evaluations,
            "elapsed": self.elapsed,
            "elapsed_ms": self.elapsed_ms,
        }

    def __repr__(self) -> str:
        move_description = (
            repr(self.move)
            if self.move is not None
            else "None"
        )

        return (
            "SearchResult("
            f"move={move_description}, "
            f"score={self.score_before:.2f}"
            f"->{self.score_after:.2f}, "
            f"improvement={self.improvement:+.2f}, "
            f"evaluations={self.evaluations}, "
            f"elapsed_ms={self.elapsed_ms:.2f}"
            ")"
        )
