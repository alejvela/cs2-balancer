from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from optimizer.normalization.exponential_normalizer import (
    ExponentialNormalizer,
)
from optimizer.normalization.linear_normalizer import (
    LinearNormalizer,
)
from optimizer.normalization.logistic_normalizer import (
    LogisticNormalizer,
)
from optimizer.normalization.normalizer import Normalizer
from optimizer.normalization.piecewise_normalizer import (
    PiecewiseNormalizer,
)


class NormalizerFactory:
    """
    Fábrica de normalizadores.

    Centraliza la construcción de las distintas estrategias de
    normalización utilizadas por el motor.

    La validación específica de cada algoritmo sigue perteneciendo
    al normalizador concreto.
    """

    @staticmethod
    def linear(
        min_value: float,
        max_value: float,
    ) -> LinearNormalizer:
        """
        Construye un normalizador lineal inverso.

        Está pensado para métricas donde un valor pequeño es mejor,
        por ejemplo una desviación estándar.

        Resultado:

            value <= min_value -> 100
            value >= max_value -> 0
        """
        return LinearNormalizer(
            min_value=min_value,
            max_value=max_value,
        )

    @staticmethod
    def logistic(
        midpoint: float,
        steepness: float = 0.03,
    ) -> LogisticNormalizer:
        """
        Construye un normalizador logístico.

        Dirección:

            steepness > 0
                Los valores pequeños obtienen mayor puntuación.

            steepness < 0
                Los valores grandes obtienen mayor puntuación.
        """
        return LogisticNormalizer(
            midpoint=midpoint,
            steepness=steepness,
        )

    @staticmethod
    def exponential(
        decay: float,
    ) -> ExponentialNormalizer:
        """
        Construye un normalizador exponencial decreciente.
        """
        return ExponentialNormalizer(
            decay=decay,
        )

    @staticmethod
    def piecewise(
        points: Iterable[tuple[float, float]],
    ) -> PiecewiseNormalizer:
        """
        Construye un normalizador definido por puntos.

        Cada punto debe tener la forma:

            (valor_entrada, puntuacion_salida)

        Ejemplo:

            [
                (0.0, 100.0),
                (100.0, 80.0),
                (200.0, 40.0),
                (300.0, 0.0),
            ]
        """
        return PiecewiseNormalizer(
            points=points,
        )

    @staticmethod
    def create(
        normalizer_type: str,
        **parameters: Any,
    ) -> Normalizer:
        """
        Construye un normalizador mediante un nombre dinámico.

        Ejemplos:

            NormalizerFactory.create(
                "linear",
                min_value=0.0,
                max_value=0.35,
            )

            NormalizerFactory.create(
                "logistic",
                midpoint=1800.0,
                steepness=-0.003,
            )

        Este método será útil cuando la configuración se mueva a JSON,
        YAML o variables externas.
        """
        if not isinstance(normalizer_type, str):
            raise TypeError(
                "normalizer_type must be a string."
            )

        normalized_type = (
            normalizer_type
            .strip()
            .casefold()
        )

        if not normalized_type:
            raise ValueError(
                "normalizer_type cannot be empty."
            )

        factories = {
            "linear": NormalizerFactory.linear,
            "logistic": NormalizerFactory.logistic,
            "exponential": NormalizerFactory.exponential,
            "piecewise": NormalizerFactory.piecewise,
        }

        factory = factories.get(
            normalized_type
        )

        if factory is None:
            supported = ", ".join(
                sorted(factories)
            )

            raise ValueError(
                f"Unknown normalizer type "
                f"'{normalizer_type}'. "
                f"Supported types: {supported}."
            )

        try:
            normalizer = factory(
                **parameters
            )

        except TypeError as error:
            raise TypeError(
                f"Invalid parameters for normalizer "
                f"'{normalized_type}': {error}"
            ) from error

        if not isinstance(
            normalizer,
            Normalizer,
        ):
            raise TypeError(
                f"The factory for '{normalized_type}' "
                "did not return a Normalizer."
            )

        return normalizer

    def __new__(
        cls,
        *args,
        **kwargs,
    ):
        """
        Evita instanciar una clase que solo contiene métodos estáticos.
        """
        raise TypeError(
            "NormalizerFactory cannot be instantiated."
        )
