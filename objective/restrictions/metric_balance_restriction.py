from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from numbers import Real

from models.team import Team
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult
from optimizer.normalization.normalizer import Normalizer
from optimizer.statistics.statistics_utils import StatisticsUtils
from scoring.scoring_model import ScoringModel


class MetricBalanceRestriction(Restriction):
    """
    Clase base para restricciones blandas que equilibran una métrica
    numérica entre varios equipos.

    El proceso de evaluación es:

        1. Extraer el valor agregado de cada equipo.
        2. Calcular la desviación estándar entre esos valores.
        3. Normalizar la desviación a una puntuación entre 0 y 100.
        4. Construir un RestrictionResult sin penalización estructural.

    Interpretación:

        score = 100
            Los equipos están perfectamente equilibrados para la métrica.

        score cercano a 0
            Existe una diferencia grande entre los equipos.

    Esta clase representa una restricción blanda. Por tanto:

        penalty = 0.0

    Las clases derivadas deben implementar:

        - name
        - extract_metric(team)

    Ejemplos:

        - EloBalanceRestriction
        - KdBalanceRestriction
        - AdrBalanceRestriction
        - RatingBalanceRestriction
    """

    def __init__(
        self,
        normalizer: Normalizer,
        weight: float = 1.0,
        scoring_model: ScoringModel | None = None,
    ) -> None:
        if normalizer is None:
            raise ValueError(
                "normalizer cannot be None."
            )

        normalize_method = getattr(
            normalizer,
            "normalize",
            None,
        )

        if not callable(normalize_method):
            raise TypeError(
                "normalizer must provide a normalize() method."
            )

        super().__init__(
            weight=weight,
            scoring_model=scoring_model,
        )

        self._normalizer = normalizer

    @abstractmethod
    def extract_metric(
        self,
        team: Team,
    ) -> float:
        """
        Devuelve el valor agregado de la métrica para un equipo.

        Ejemplo:

            return team.statistics.average(Stat.ELO)
        """
        ...

    def evaluate(
        self,
        teams: Sequence[Team],
    ) -> RestrictionResult:
        """
        Evalúa el equilibrio de la métrica entre los equipos.

        Una desviación pequeña genera una puntuación próxima a 100.
        Una desviación grande genera una puntuación más baja.
        """
        team_list = self._validate_teams(
            teams
        )

        team_values = [
            self._extract_and_validate(
                team=team,
                fallback_index=index,
            )
            for index, team in enumerate(
                team_list,
                start=1,
            )
        ]

        values = [
            value
            for _, value in team_values
        ]

        average = StatisticsUtils.mean(
            values
        )

        minimum = StatisticsUtils.minimum(
            values
        )

        maximum = StatisticsUtils.maximum(
            values
        )

        value_range = StatisticsUtils.value_range(
            values
        )

        standard_deviation = (
            StatisticsUtils.standard_deviation(
                values
            )
        )

        coefficient_of_variation = (
            StatisticsUtils.coefficient_of_variation(
                values
            )
        )

        score = self._normalize_score(
            standard_deviation
        )

        result = RestrictionResult(
            name=self.name,
            score=score,
            penalty=0.0,
            weight=self.weight,
        )

        result.add_detail(
            "metric",
            self.name,
        )

        result.add_detail(
            "values",
            values,
        )

        result.add_detail(
            "team_values",
            {
                team_name: value
                for team_name, value in team_values
            },
        )

        result.add_detail(
            "average",
            average,
        )

        result.add_detail(
            "minimum",
            minimum,
        )

        result.add_detail(
            "maximum",
            maximum,
        )

        result.add_detail(
            "range",
            value_range,
        )

        result.add_detail(
            "standard_deviation",
            standard_deviation,
        )

        result.add_detail(
            "coefficient_of_variation",
            coefficient_of_variation,
        )

        result.add_detail(
            "normalized_score",
            score,
        )

        result.add_detail(
            "soft_restriction",
            True,
        )

        return result

    def _extract_and_validate(
        self,
        team: Team,
        fallback_index: int,
    ) -> tuple[str, float]:
        """
        Extrae la métrica y verifica que sea numérica.

        Devuelve:

            (nombre del equipo, valor de la métrica)
        """
        team_name = self._team_name(
            team=team,
            fallback_index=fallback_index,
        )

        value = self.extract_metric(
            team
        )

        if value is None:
            raise ValueError(
                f"{self.name} returned None for "
                f"'{team_name}'."
            )

        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                f"{self.name} must return a numeric value "
                f"for '{team_name}', but returned "
                f"{type(value).__name__}."
            )

        return (
            team_name,
            float(value),
        )

    def _normalize_score(
        self,
        deviation: float,
    ) -> float:
        """
        Convierte la desviación estándar en una puntuación 0-100.
        """
        if isinstance(deviation, bool) or not isinstance(
            deviation,
            Real,
        ):
            raise TypeError(
                "deviation must be numeric."
            )

        deviation = float(
            deviation
        )

        if deviation < 0.0:
            raise ValueError(
                "deviation cannot be negative."
            )

        normalized = self._normalizer.normalize(
            deviation
        )

        if isinstance(normalized, bool) or not isinstance(
            normalized,
            Real,
        ):
            raise TypeError(
                "normalizer.normalize() must return "
                "a numeric value."
            )

        return self._clamp_score(
            float(normalized)
        )

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        """
        Valida la colección de equipos.

        Se necesitan al menos dos equipos para medir equilibrio.
        """
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        team_list = list(
            teams
        )

        if len(team_list) < 2:
            raise ValueError(
                "MetricBalanceRestriction requires "
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
                    f"Team {index} does not expose "
                    "a players collection."
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
        """
        Obtiene un nombre legible para el equipo.
        """
        name = getattr(
            team,
            "name",
            None,
        )

        if name:
            return str(
                name
            )

        team_id = getattr(
            team,
            "id",
            None,
        )

        if team_id is not None:
            return f"Team {team_id}"

        if fallback_index is not None:
            return f"Team {fallback_index}"

        return f"Team-{id(team)}"

    @staticmethod
    def _clamp_score(
        value: float,
    ) -> float:
        """
        Limita una puntuación al intervalo 0-100.
        """
        return max(
            0.0,
            min(
                100.0,
                value,
            ),
        )

    @property
    def normalizer(
        self,
    ) -> Normalizer:
        return self._normalizer

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"weight={self.weight}, "
            f"normalizer="
            f"{self._normalizer.__class__.__name__})"
        )
