from __future__ import annotations

from collections.abc import Iterable
from math import sqrt
from statistics import median as calculate_median


class StatisticsUtils:
    """
    Operaciones estadísticas genéricas utilizadas por el motor
    de optimización.

    La clase no mantiene estado. Todos sus métodos son estáticos
    y aceptan cualquier iterable numérico.
    """

    @staticmethod
    def _to_list(values: Iterable[float]) -> list[float]:
        """
        Convierte el iterable recibido en una lista de valores float.

        Permite reutilizar generadores sin consumirlos varias veces.
        """
        return [float(value) for value in values]

    @staticmethod
    def mean(values: Iterable[float]) -> float:
        """
        Devuelve la media aritmética.

        Si no existen valores, devuelve 0.0.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        return sum(items) / len(items)

    @staticmethod
    def median(values: Iterable[float]) -> float:
        """
        Devuelve la mediana.

        Si no existen valores, devuelve 0.0.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        return float(calculate_median(items))

    @staticmethod
    def minimum(values: Iterable[float]) -> float:
        """
        Devuelve el valor mínimo.

        Si no existen valores, devuelve 0.0.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        return min(items)

    @staticmethod
    def maximum(values: Iterable[float]) -> float:
        """
        Devuelve el valor máximo.

        Si no existen valores, devuelve 0.0.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        return max(items)

    @staticmethod
    def value_range(values: Iterable[float]) -> float:
        """
        Devuelve la diferencia entre el valor máximo y el mínimo.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        return max(items) - min(items)

    @staticmethod
    def variance(values: Iterable[float]) -> float:
        """
        Devuelve la varianza poblacional.

        Si hay menos de dos valores, devuelve 0.0.
        """
        items = StatisticsUtils._to_list(values)

        if len(items) <= 1:
            return 0.0

        average = sum(items) / len(items)

        return sum(
            (value - average) ** 2
            for value in items
        ) / len(items)

    @staticmethod
    def standard_deviation(values: Iterable[float]) -> float:
        """
        Devuelve la desviación estándar poblacional.
        """
        return sqrt(
            StatisticsUtils.variance(values)
        )

    @staticmethod
    def mean_absolute_deviation(
        values: Iterable[float]
    ) -> float:
        """
        Devuelve la desviación absoluta media respecto a la media.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        average = sum(items) / len(items)

        return sum(
            abs(value - average)
            for value in items
        ) / len(items)

    @staticmethod
    def coefficient_of_variation(
        values: Iterable[float]
    ) -> float:
        """
        Devuelve el coeficiente de variación:

            desviación estándar / media

        Si la media es cero, devuelve 0.0.
        """
        items = StatisticsUtils._to_list(values)

        if not items:
            return 0.0

        average = sum(items) / len(items)

        if average == 0:
            return 0.0

        return (
            StatisticsUtils.standard_deviation(items)
            / abs(average)
        )

    @staticmethod
    def normalize(
        value: float,
        minimum: float,
        maximum: float
    ) -> float:
        """
        Normaliza un valor al intervalo 0–1.

        Los valores inferiores al mínimo devuelven 0 y los superiores
        al máximo devuelven 1.
        """
        if maximum <= minimum:
            raise ValueError(
                "maximum must be greater than minimum."
            )

        normalized = (
            float(value) - float(minimum)
        ) / (
            float(maximum) - float(minimum)
        )

        return max(0.0, min(1.0, normalized))
