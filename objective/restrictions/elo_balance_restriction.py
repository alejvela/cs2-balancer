from __future__ import annotations

from numbers import Real

from models.stat import Stat
from models.team import Team
from objective.restrictions.metric_balance_restriction import (
    MetricBalanceRestriction,
)
from optimizer.normalization.factory import (
    NormalizerFactory,
)


class EloBalanceRestriction(
    MetricBalanceRestriction
):
    """
    Evalúa el equilibrio del ELO medio entre los equipos.

    La métrica base utilizada por MetricBalanceRestriction es la
    dispersión de los valores extraídos de cada equipo.

    Para esta restricción:

        valor por equipo
            =
        ELO medio del equipo

    y posteriormente se mide cuánto difieren esos valores entre sí.

    ----------------------------------------------------------------
    Filosofía
    ----------------------------------------------------------------

    El ELO sigue siendo una señal importante de fuerza competitiva,
    pero NO debe dominar el Objective Engine porque ya participa
    indirectamente en Power.

    Por tanto, esta curva está diseñada para ser:

        - exigente cuando existen diferencias extremas;
        - tolerante con pequeñas diferencias inevitables;
        - progresiva;
        - sin convertir diferencias moderadas en scores cercanos a 0.

    Valores orientativos de la curva por defecto:

        desviación ELO       score aproximado

             0                  ~95
            40                  ~88
            70                  ~78
           100                  ~62
           120                   50
           140                  ~38
           180                  ~18
           220                   ~8

    El midpoint representa el punto donde la restricción obtiene
    aproximadamente 50 puntos.

    Una desviación estándar de 120 ELO entre medias de equipo se
    considera, por tanto, claramente mejorable pero no catastrófica.

    Esta restricción es blanda:

        penalty = 0

    Su efecto debe producirse únicamente mediante el score ponderado.
    """

    DEFAULT_WEIGHT = 10.0

    DEFAULT_MIDPOINT = 120.0

    DEFAULT_STEEPNESS = 0.025

    def __init__(
        self,
        weight: float = DEFAULT_WEIGHT,
        midpoint: float = DEFAULT_MIDPOINT,
        steepness: float = DEFAULT_STEEPNESS,
    ) -> None:
        self._validate_positive_number(
            weight,
            "weight",
        )

        self._validate_positive_number(
            midpoint,
            "midpoint",
        )

        self._validate_positive_number(
            steepness,
            "steepness",
        )

        self._midpoint = float(
            midpoint
        )

        self._steepness = float(
            steepness
        )

        super().__init__(
            weight=float(
                weight
            ),

            normalizer=(
                NormalizerFactory.logistic(
                    midpoint=(
                        self._midpoint
                    ),

                    steepness=(
                        self._steepness
                    ),
                )
            ),
        )

    # ========================================================
    # Identidad
    # ========================================================

    @property
    def name(
        self,
    ) -> str:
        return "ELO Balance"

    # ========================================================
    # Configuración
    # ========================================================

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

    # ========================================================
    # Métrica
    # ========================================================

    def extract_metric(
        self,
        team: Team,
    ) -> float:
        """
        Obtiene el ELO medio del equipo.

        MetricBalanceRestriction utilizará posteriormente los valores
        extraídos de todos los equipos para calcular su dispersión.
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
            Stat.ELO
        )

        if value is None:
            raise ValueError(
                "Could not calculate the average ELO "
                f"for {self._team_name(team)}."
            )

        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                Real,
            )
        ):
            raise TypeError(
                "Average ELO must be numeric."
            )

        numeric_value = float(
            value
        )

        if numeric_value < 0.0:
            raise ValueError(
                "Average ELO cannot be negative."
            )

        return numeric_value

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_positive_number(
        value: float,
        field_name: str,
    ) -> None:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                Real,
            )
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        if float(
            value
        ) <= 0.0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    # ========================================================
    # Serialización auxiliar
    # ========================================================

    def as_config_dict(
        self,
    ) -> dict[str, float | str]:
        """
        Configuración útil para diagnóstico, metadata o futuras APIs.
        """
        return {
            "name": self.name,

            "weight": self.weight,

            "midpoint": (
                self._midpoint
            ),

            "steepness": (
                self._steepness
            ),
        }

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"weight={self.weight:.2f}, "
            f"midpoint={self._midpoint:.2f}, "
            f"steepness={self._steepness:.4f})"
        )
