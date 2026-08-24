from __future__ import annotations

from collections.abc import Sequence
from numbers import Real

from models.stat import Stat
from models.team import Team
from objective.restriction import Restriction
from objective.restriction_result import (
    RestrictionResult,
)


class EloSpreadRestriction(Restriction):
    """
    Controla la diferencia entre el equipo con mayor ELO medio
    y el equipo con menor ELO medio.

    Esta restricción NO pretende medir el equilibrio general del ELO.
    Esa responsabilidad pertenece a EloBalanceRestriction.

    Su función es distinta:

        detectar y penalizar equipos extremos.

    Por ejemplo, aunque tres equipos tengan ELO medio parecido,
    esta restricción detectará si el cuarto está claramente por
    encima o por debajo.

    ============================================================
    Filosofía
    ============================================================

    Una diferencia pequeña entre el mejor y peor equipo es excelente,
    pero en un torneo formado por jugadores con niveles FACEIT muy
    diferentes no debemos exigir spreads artificialmente pequeños.

    La puntuación se calcula mediante una curva lineal por tramos:

        spread <= ideal_spread
            → 100

        ideal_spread < spread <= good_spread
            → 100 .. 85

        good_spread < spread <= acceptable_spread
            → 85 .. 60

        acceptable_spread < spread <= poor_spread
            → 60 .. 25

        poor_spread < spread < maximum_spread
            → 25 .. 0

        spread >= maximum_spread
            → 0

    Con los valores predeterminados:

          0 - 100 ELO   → excelente
            150 ELO     → ~85
            200 ELO     → ~60
            250 ELO     → ~43
            300 ELO     → ~25
            400 ELO     → 0

    Esto convierte ELO Spread en una salvaguarda frente a extremos,
    no en una segunda versión de ELO Balance.

    Es una restricción blanda:

        penalty = 0.0
    """

    DEFAULT_WEIGHT = 5.0

    DEFAULT_IDEAL_SPREAD = 100.0

    DEFAULT_GOOD_SPREAD = 150.0

    DEFAULT_ACCEPTABLE_SPREAD = 200.0

    DEFAULT_POOR_SPREAD = 300.0

    DEFAULT_MAXIMUM_SPREAD = 400.0

    SCORE_EXCELLENT = 100.0
    SCORE_GOOD = 85.0
    SCORE_ACCEPTABLE = 60.0
    SCORE_POOR = 25.0
    SCORE_MINIMUM = 0.0

    def __init__(
        self,
        weight: float = DEFAULT_WEIGHT,
        ideal_spread: float = DEFAULT_IDEAL_SPREAD,
        good_spread: float = DEFAULT_GOOD_SPREAD,
        acceptable_spread: float = DEFAULT_ACCEPTABLE_SPREAD,
        poor_spread: float = DEFAULT_POOR_SPREAD,
        maximum_spread: float = DEFAULT_MAXIMUM_SPREAD,
    ) -> None:
        self._validate_positive_number(
            value=weight,
            field_name="weight",
        )

        self._validate_non_negative_number(
            value=ideal_spread,
            field_name="ideal_spread",
        )

        self._validate_positive_number(
            value=good_spread,
            field_name="good_spread",
        )

        self._validate_positive_number(
            value=acceptable_spread,
            field_name="acceptable_spread",
        )

        self._validate_positive_number(
            value=poor_spread,
            field_name="poor_spread",
        )

        self._validate_positive_number(
            value=maximum_spread,
            field_name="maximum_spread",
        )

        ideal_spread = float(
            ideal_spread
        )

        good_spread = float(
            good_spread
        )

        acceptable_spread = float(
            acceptable_spread
        )

        poor_spread = float(
            poor_spread
        )

        maximum_spread = float(
            maximum_spread
        )

        thresholds = (
            ideal_spread,
            good_spread,
            acceptable_spread,
            poor_spread,
            maximum_spread,
        )

        if thresholds != tuple(
            sorted(thresholds)
        ):
            raise ValueError(
                "ELO spread thresholds must be "
                "configured in ascending order."
            )

        if len(
            set(thresholds)
        ) != len(
            thresholds
        ):
            raise ValueError(
                "ELO spread thresholds must be unique."
            )

        super().__init__(
            weight=float(weight),
        )

        self._ideal_spread = (
            ideal_spread
        )

        self._good_spread = (
            good_spread
        )

        self._acceptable_spread = (
            acceptable_spread
        )

        self._poor_spread = (
            poor_spread
        )

        self._maximum_spread = (
            maximum_spread
        )

    # ========================================================
    # Identidad
    # ========================================================

    @property
    def name(
        self,
    ) -> str:
        return "ELO Spread"

    # ========================================================
    # Configuración
    # ========================================================

    @property
    def ideal_spread(
        self,
    ) -> float:
        return self._ideal_spread

    @property
    def good_spread(
        self,
    ) -> float:
        return self._good_spread

    @property
    def acceptable_spread(
        self,
    ) -> float:
        return self._acceptable_spread

    @property
    def poor_spread(
        self,
    ) -> float:
        return self._poor_spread

    @property
    def maximum_spread(
        self,
    ) -> float:
        return self._maximum_spread

    # ========================================================
    # Evaluación
    # ========================================================

    def evaluate(
        self,
        teams: Sequence[Team],
    ) -> RestrictionResult:
        """
        Evalúa la diferencia entre el mayor y menor ELO medio.
        """
        team_list = self._validate_teams(
            teams
        )

        team_values: dict[
            str,
            float,
        ] = {}

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            team_name = self._team_name(
                team=team,
                fallback_index=index,
            )

            team_values[
                team_name
            ] = (
                self._extract_average_elo(
                    team
                )
            )

        minimum_team_name = min(
            team_values,
            key=team_values.get,
        )

        maximum_team_name = max(
            team_values,
            key=team_values.get,
        )

        minimum_elo = team_values[
            minimum_team_name
        ]

        maximum_elo = team_values[
            maximum_team_name
        ]

        elo_spread = (
            maximum_elo
            - minimum_elo
        )

        score = self._score_spread(
            elo_spread
        )

        result = RestrictionResult(
            name=self.name,
            score=score,
            penalty=0.0,
            weight=self.weight,
        )

        # ----------------------------------------------------
        # Diagnóstico
        # ----------------------------------------------------

        result.add_detail(
            "team_values",
            team_values,
        )

        result.add_detail(
            "minimum_team",
            minimum_team_name,
        )

        result.add_detail(
            "minimum_team_elo",
            minimum_elo,
        )

        result.add_detail(
            "maximum_team",
            maximum_team_name,
        )

        result.add_detail(
            "maximum_team_elo",
            maximum_elo,
        )

        result.add_detail(
            "elo_spread",
            elo_spread,
        )

        result.add_detail(
            "spread_category",
            self._spread_category(
                elo_spread
            ),
        )

        result.add_detail(
            "ideal_spread",
            self._ideal_spread,
        )

        result.add_detail(
            "good_spread",
            self._good_spread,
        )

        result.add_detail(
            "acceptable_spread",
            self._acceptable_spread,
        )

        result.add_detail(
            "poor_spread",
            self._poor_spread,
        )

        result.add_detail(
            "maximum_spread",
            self._maximum_spread,
        )

        result.add_detail(
            "within_ideal_spread",
            (
                elo_spread
                <= self._ideal_spread
            ),
        )

        result.add_detail(
            "soft_restriction",
            True,
        )

        return result

    # ========================================================
    # Scoring
    # ========================================================

    def _score_spread(
        self,
        spread: float,
    ) -> float:
        """
        Convierte el spread de ELO en una puntuación 0-100 mediante
        interpolación lineal por tramos.
        """
        if spread <= self._ideal_spread:
            return self.SCORE_EXCELLENT

        if spread <= self._good_spread:
            return self._interpolate(
                value=spread,
                x1=self._ideal_spread,
                y1=self.SCORE_EXCELLENT,
                x2=self._good_spread,
                y2=self.SCORE_GOOD,
            )

        if spread <= self._acceptable_spread:
            return self._interpolate(
                value=spread,
                x1=self._good_spread,
                y1=self.SCORE_GOOD,
                x2=self._acceptable_spread,
                y2=self.SCORE_ACCEPTABLE,
            )

        if spread <= self._poor_spread:
            return self._interpolate(
                value=spread,
                x1=self._acceptable_spread,
                y1=self.SCORE_ACCEPTABLE,
                x2=self._poor_spread,
                y2=self.SCORE_POOR,
            )

        if spread < self._maximum_spread:
            return self._interpolate(
                value=spread,
                x1=self._poor_spread,
                y1=self.SCORE_POOR,
                x2=self._maximum_spread,
                y2=self.SCORE_MINIMUM,
            )

        return self.SCORE_MINIMUM

    @staticmethod
    def _interpolate(
        value: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:
        """
        Interpolación lineal entre dos puntos.
        """
        if x2 <= x1:
            raise ValueError(
                "x2 must be greater than x1."
            )

        ratio = (
            (value - x1)
            / (x2 - x1)
        )

        score = (
            y1
            + ratio
            * (y2 - y1)
        )

        return max(
            0.0,
            min(
                100.0,
                float(score),
            ),
        )

    def _spread_category(
        self,
        spread: float,
    ) -> str:
        if spread <= self._ideal_spread:
            return "excellent"

        if spread <= self._good_spread:
            return "good"

        if spread <= self._acceptable_spread:
            return "acceptable"

        if spread <= self._poor_spread:
            return "poor"

        if spread < self._maximum_spread:
            return "very_poor"

        return "extreme"

    # ========================================================
    # ELO
    # ========================================================

    @staticmethod
    def _extract_average_elo(
        team: Team,
    ) -> float:
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
                "for one of the teams."
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
    # Validación
    # ========================================================

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        team_list = list(
            teams
        )

        if len(team_list) < 2:
            raise ValueError(
                "EloSpreadRestriction requires "
                "at least two teams."
            )

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            if team is None:
                raise ValueError(
                    f"Team {index} cannot be None."
                )

            players = getattr(
                team,
                "players",
                None,
            )

            if players is None:
                raise AttributeError(
                    f"Team {index} does not expose players."
                )

            if not players:
                raise ValueError(
                    f"Team {index} cannot be empty."
                )

        return team_list

    @staticmethod
    def _team_name(
        team: Team,
        fallback_index: int | None = None,
    ) -> str:
        name = getattr(
            team,
            "name",
            None,
        )

        if name:
            return str(name)

        team_id = getattr(
            team,
            "id",
            None,
        )

        if team_id is not None:
            return (
                f"Team {team_id}"
            )

        if fallback_index is not None:
            return (
                f"Team {fallback_index}"
            )

        return (
            f"Team-{id(team)}"
        )

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

        if float(value) <= 0.0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    @staticmethod
    def _validate_non_negative_number(
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

        if float(value) < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

    # ========================================================
    # Configuración serializable
    # ========================================================

    def as_config_dict(
        self,
    ) -> dict[str, float | str]:
        return {
            "name": self.name,
            "weight": self.weight,
            "ideal_spread": self._ideal_spread,
            "good_spread": self._good_spread,
            "acceptable_spread": (
                self._acceptable_spread
            ),
            "poor_spread": self._poor_spread,
            "maximum_spread": (
                self._maximum_spread
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
            f"ideal_spread={self._ideal_spread:.2f}, "
            f"good_spread={self._good_spread:.2f}, "
            f"acceptable_spread="
            f"{self._acceptable_spread:.2f}, "
            f"poor_spread={self._poor_spread:.2f}, "
            f"maximum_spread={self._maximum_spread:.2f})"
        )
