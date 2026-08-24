from __future__ import annotations

from numbers import Real

from models.stat import Stat
from models.team import Team
from objective.restrictions.metric_balance_restriction import (
    MetricBalanceRestriction,
)
from optimizer.normalization.factory import NormalizerFactory


class KdBalanceRestriction(MetricBalanceRestriction):
    """
    Evalúa el equilibrio del KD medio entre los equipos.

    Para cada equipo se calcula:

        KD medio = suma de KD / número de jugadores

    Después se obtiene la desviación estándar entre los KD medios.

    Interpretación aproximada con la configuración predeterminada:

        desviación 0.00
            Equilibrio perfecto.

        desviación 0.10
            Diferencia pequeña.

        desviación 0.20
            Diferencia apreciable.

        desviación >= 0.35
            Desequilibrio elevado.

    Esta es una restricción blanda:

        penalty = 0.0
    """

    DEFAULT_WEIGHT = 15.0
    DEFAULT_MAX_DEVIATION = 0.35

    def __init__(
        self,
        weight: float = DEFAULT_WEIGHT,
        max_deviation: float = DEFAULT_MAX_DEVIATION,
    ) -> None:
        self._validate_positive_number(
            value=weight,
            field_name="weight",
        )

        self._validate_positive_number(
            value=max_deviation,
            field_name="max_deviation",
        )

        self._max_deviation = float(
            max_deviation
        )

        super().__init__(
            weight=float(weight),
            normalizer=NormalizerFactory.linear(
                min_value=0.0,
                max_value=self._max_deviation,
            ),
        )

    @property
    def name(self) -> str:
        return "KD Balance"

    @property
    def max_deviation(self) -> float:
        return self._max_deviation

    def extract_metric(
        self,
        team: Team,
    ) -> float:
        """
        Devuelve el KD medio del equipo.
        """
        if team is None:
            raise ValueError(
                "team cannot be None."
            )

        statistics = getattr(
            team,
            "statistics",
            None,
        )

        if statistics is None:
            raise AttributeError(
                "team does not expose statistics."
            )

        value = statistics.average(
            Stat.KD
        )

        if value is None:
            raise ValueError(
                "Could not calculate the average KD "
                f"for {self._team_name(team)}."
            )

        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                "Average KD must be numeric."
            )

        return float(value)

    @staticmethod
    def _validate_positive_number(
        value: float,
        field_name: str,
    ) -> None:
        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        if float(value) <= 0.0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"weight={self.weight:.2f}, "
            f"max_deviation={self._max_deviation:.3f})"
        )
