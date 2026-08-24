from __future__ import annotations

from collections import Counter
from statistics import mean, median, pstdev, pvariance
from typing import Any

from models.stat import Stat


class TeamStatistics:
    """
    Calcula estadísticas agregadas de un equipo.

    Todas las operaciones utilizan caché.
    La caché se invalida automáticamente cuando cambia la composición
    del equipo.
    """

    def __init__(self, team):

        self._team = team

        self.invalidate()

    # ==========================================================
    # Cache
    # ==========================================================

    def invalidate(self):

        self._cache: dict[tuple, Any] = {}

    # ==========================================================
    # Helpers
    # ==========================================================

    def _attribute(self, stat: Stat | str) -> str:

        if isinstance(stat, Stat):
            return stat.value

        return stat

    def values(self, stat: Stat | str) -> list:

        attribute = self._attribute(stat)

        key = ("values", attribute)

        if key in self._cache:
            return self._cache[key]

        values = []

        for player in self._team.players:

            value = getattr(player, attribute, None)

            if value is not None:

                values.append(value)

        self._cache[key] = values

        return values

    # ==========================================================
    # Agregaciones
    # ==========================================================

    def average(self, stat: Stat | str) -> float:

        attribute = self._attribute(stat)

        key = ("avg", attribute)

        if key in self._cache:
            return self._cache[key]

        values = self.values(attribute)

        result = mean(values) if values else 0.0

        self._cache[key] = result

        return result

    def minimum(self, stat: Stat | str):

        values = self.values(stat)

        return min(values) if values else 0

    def maximum(self, stat: Stat | str):

        values = self.values(stat)

        return max(values) if values else 0

    def total(self, stat: Stat | str):

        values = self.values(stat)

        return sum(values)

    def median(self, stat: Stat | str):

        values = self.values(stat)

        return median(values) if values else 0

    def deviation(self, stat: Stat | str):

        attribute = self._attribute(stat)

        key = ("std", attribute)

        if key in self._cache:
            return self._cache[key]

        values = self.values(attribute)

        result = pstdev(values) if len(values) > 1 else 0

        self._cache[key] = result

        return result

    def variance(self, stat: Stat | str):

        attribute = self._attribute(stat)

        key = ("var", attribute)

        if key in self._cache:
            return self._cache[key]

        values = self.values(attribute)

        result = pvariance(values) if len(values) > 1 else 0

        self._cache[key] = result

        return result

    # ==========================================================
    # Distribuciones
    # ==========================================================

    def distribution(self, stat: Stat | str) -> Counter:

        attribute = self._attribute(stat)

        key = ("dist", attribute)

        if key in self._cache:
            return self._cache[key]

        distribution = Counter()

        for player in self._team.players:

            value = getattr(player, attribute, None)

            if value is not None:

                distribution[value] += 1

        self._cache[key] = distribution

        return distribution

    # ==========================================================
    # Utilidades
    # ==========================================================

    def contains(self, stat: Stat | str) -> bool:

        return len(self.values(stat)) > 0

    @property
    def count(self):

        return len(self._team.players)

    def clear(self):

        self.invalidate()

    def __len__(self):

        return self.count
