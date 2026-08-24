from __future__ import annotations

import math
from numbers import Real

from optimizer.normalization.normalizer import Normalizer


class LogisticNormalizer(Normalizer):
    """
    Normalizador basado en una curva logística.

    Fórmula:

        score =
            100 / (
                1 + exp(
                    steepness * (value - midpoint)
                )
            )

    Interpretación:

        value == midpoint
            devuelve 50.

        steepness > 0
            los valores pequeños son mejores.
            La puntuación disminuye al aumentar `value`.

        steepness < 0
            los valores grandes son mejores.
            La puntuación aumenta al aumentar `value`.

    Ejemplos:

        Desviación de ELO:
            midpoint=120
            steepness=0.03

        ELO individual:
            midpoint=1800
            steepness=-0.003
    """

    def __init__(
        self,
        midpoint: float,
        steepness: float = 0.03,
    ) -> None:
        if (
            isinstance(midpoint, bool)
            or not isinstance(midpoint, Real)
        ):
            raise TypeError(
                "midpoint must be numeric."
            )

        if (
            isinstance(steepness, bool)
            or not isinstance(steepness, Real)
        ):
            raise TypeError(
                "steepness must be numeric."
            )

        midpoint = float(midpoint)
        steepness = float(steepness)

        if not math.isfinite(midpoint):
            raise ValueError(
                "midpoint must be finite."
            )

        if not math.isfinite(steepness):
            raise ValueError(
                "steepness must be finite."
            )

        if steepness == 0.0:
            raise ValueError(
                "steepness cannot be zero."
            )

        self._midpoint = midpoint
        self._steepness = steepness

    def normalize(
        self,
        value: float,
    ) -> float:
        """
        Normaliza el valor al intervalo 0-100.
        """
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
        ):
            raise TypeError(
                "value must be numeric."
            )

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(
                "value must be finite."
            )

        exponent = (
            self._steepness
            * (value - self._midpoint)
        )

        # Evita OverflowError en math.exp().
        if exponent >= 700.0:
            return 0.0

        if exponent <= -700.0:
            return 100.0

        score = (
            100.0
            / (
                1.0
                + math.exp(exponent)
            )
        )

        return float(
            self.clamp(score)
        )

    @property
    def midpoint(
        self,
    ) -> float:
        return self._midpoint

    @property
    def steepness(
        self,
    ) -> float:
        return self._steepness

    @property
    def increasing(
        self,
    ) -> bool:
        """
        Indica si la puntuación aumenta al aumentar el valor.
        """
        return self._steepness < 0.0

    @property
    def decreasing(
        self,
    ) -> bool:
        """
        Indica si la puntuación disminuye al aumentar el valor.
        """
        return self._steepness > 0.0

    def __repr__(
        self,
    ) -> str:
        direction = (
            "increasing"
            if self.increasing
            else "decreasing"
        )

        return (
            f"{self.__class__.__name__}("
            f"midpoint={self._midpoint:.4f}, "
            f"steepness={self._steepness:.6f}, "
            f"direction='{direction}')"
        )
