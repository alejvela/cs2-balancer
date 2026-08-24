from __future__ import annotations

import math
from numbers import Real

from optimizer.normalization.normalizer import Normalizer


class ExponentialNormalizer(Normalizer):
    """
    Normalizador exponencial decreciente.

    Fórmula:

        score = 100 * exp(-decay * value)

    Cuanto menor sea el valor, mayor será la puntuación.

    Ejemplo:

        value = 0      -> 100
        value = 100    -> 60.65
        value = 300    -> 22.31
    """

    def __init__(
        self,
        decay: float = 0.005,
    ) -> None:

        if (
            isinstance(decay, bool)
            or not isinstance(decay, Real)
        ):
            raise TypeError(
                "decay must be numeric."
            )

        decay = float(decay)

        if decay <= 0:
            raise ValueError(
                "decay must be greater than zero."
            )

        self._decay = decay

    def normalize(
        self,
        value: float,
    ) -> float:

        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
        ):
            raise TypeError(
                "value must be numeric."
            )

        value = float(value)

        if value < 0:
            raise ValueError(
                "value cannot be negative."
            )

        score = (
            100.0
            * math.exp(
                -self._decay * value
            )
        )

        return float(
            self.clamp(score)
        )

    @property
    def decay(self) -> float:
        return self._decay

    def __repr__(self):

        return (
            f"{self.__class__.__name__}("
            f"decay={self._decay:.6f})"
        )
