from __future__ import annotations

from numbers import Real

from optimizer.normalization.normalizer import Normalizer


class LinearNormalizer(Normalizer):
    """
    Normalizador lineal inverso.

    Está pensado para métricas donde un valor pequeño es mejor,
    como una desviación estándar o una diferencia entre equipos.

    Comportamiento:

        value <= min_value
            devuelve 100

        value >= max_value
            devuelve 0

        min_value < value < max_value
            interpola linealmente entre 100 y 0

    Ejemplo:

        min_value = 0.0
        max_value = 0.35

        value = 0.0   -> 100
        value = 0.175 -> 50
        value = 0.35  -> 0
    """

    def __init__(
        self,
        min_value: float,
        max_value: float,
    ) -> None:
        if (
            isinstance(min_value, bool)
            or not isinstance(min_value, Real)
        ):
            raise TypeError(
                "min_value must be numeric."
            )

        if (
            isinstance(max_value, bool)
            or not isinstance(max_value, Real)
        ):
            raise TypeError(
                "max_value must be numeric."
            )

        min_value = float(min_value)
        max_value = float(max_value)

        if max_value <= min_value:
            raise ValueError(
                "max_value must be greater than min_value."
            )

        self._min_value = min_value
        self._max_value = max_value

    def normalize(
        self,
        value: float,
    ) -> float:
        """
        Convierte un valor al intervalo 0-100.

        Los valores bajos obtienen mayor puntuación.
        """
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
        ):
            raise TypeError(
                "value must be numeric."
            )

        value = float(value)

        if value <= self._min_value:
            return 100.0

        if value >= self._max_value:
            return 0.0

        relative_position = (
            value - self._min_value
        ) / (
            self._max_value - self._min_value
        )

        score = (
            100.0
            - relative_position * 100.0
        )

        return float(
            self.clamp(score)
        )

    @property
    def min_value(
        self,
    ) -> float:
        return self._min_value

    @property
    def max_value(
        self,
    ) -> float:
        return self._max_value

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"min_value={self._min_value:.4f}, "
            f"max_value={self._max_value:.4f})"
        )
