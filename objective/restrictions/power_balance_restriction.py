from __future__ import annotations

from collections.abc import Sequence
from statistics import mean
from typing import Any

from models.team import Team
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult
from scoring.scoring_model import ScoringModel


class PowerBalanceRestriction(Restriction):
    """
    Evalúa el equilibrio del Power Score entre los equipos.

    Para cada equipo calcula:

        power medio = suma del power de sus jugadores / jugadores

    Después compara el equipo con mayor power medio con el equipo
    de menor power medio.

    El resultado está comprendido entre 0 y 100:

        100 -> todos los equipos tienen exactamente el mismo power.
        0   -> existe una diferencia extrema entre los equipos.

    Esta es una restricción blanda, por lo que no genera penalización.
    """

    def __init__(
        self,
        scoring_model: ScoringModel,
        weight: float = 40.0,
    ) -> None:
        if scoring_model is None:
            raise ValueError(
                "scoring_model cannot be None."
            )

        if isinstance(weight, bool) or not isinstance(
            weight,
            (int, float),
        ):
            raise TypeError(
                "weight must be numeric."
            )

        if weight <= 0:
            raise ValueError(
                "weight must be greater than zero."
            )

        self._scoring_model = scoring_model
        self._weight = float(weight)

    @property
    def name(self) -> str:
        return "Power Balance"

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def scoring_model(self) -> ScoringModel:
        return self._scoring_model

    def evaluate(
        self,
        teams: Sequence[Team],
    ) -> RestrictionResult:
        """
        Calcula el equilibrio de Power Score entre los equipos.
        """
        team_list = self._validate_teams(
            teams
        )

        team_values = [
            self._calculate_team_power(team)
            for team in team_list
        ]

        power_values = [
            item["average_power"]
            for item in team_values
        ]

        global_average = mean(
            power_values
        )

        minimum_power = min(
            power_values
        )

        maximum_power = max(
            power_values
        )

        spread = (
            maximum_power
            - minimum_power
        )

        score = self._calculate_score(
            spread=spread,
            global_average=global_average,
        )

        return RestrictionResult(
            name=self.name,
            score=score,
            penalty=0.0,
            weight=self.weight,
            details={
                "global_average_power": round(
                    global_average,
                    4,
                ),
                "minimum_team_power": round(
                    minimum_power,
                    4,
                ),
                "maximum_team_power": round(
                    maximum_power,
                    4,
                ),
                "power_spread": round(
                    spread,
                    4,
                ),
                "relative_spread_percentage": round(
                    (
                        spread / global_average * 100.0
                        if global_average > 0
                        else 0.0
                    ),
                    4,
                ),
                "teams": {
                    item["team_name"]: {
                        "average_power": round(
                            item["average_power"],
                            4,
                        ),
                        "total_power": round(
                            item["total_power"],
                            4,
                        ),
                        "players": item["player_count"],
                    }
                    for item in team_values
                },
            },
        )

    def _calculate_team_power(
        self,
        team: Team,
    ) -> dict[str, Any]:
        """
        Calcula el Power Score medio y total de un equipo.
        """
        players = list(
            getattr(team, "players", [])
        )

        if not players:
            return {
                "team_name": self._team_name(team),
                "average_power": 0.0,
                "total_power": 0.0,
                "player_count": 0,
            }

        player_powers = [
            float(
                self._scoring_model.power(player)
            )
            for player in players
        ]

        total_power = sum(
            player_powers
        )

        average_power = (
            total_power / len(player_powers)
        )

        return {
            "team_name": self._team_name(team),
            "average_power": average_power,
            "total_power": total_power,
            "player_count": len(players),
        }

    @staticmethod
    def _calculate_score(
        spread: float,
        global_average: float,
    ) -> float:
        """
        Convierte la diferencia entre equipos a una puntuación 0-100.

        Ejemplo:

            media global = 50
            diferencia máxima = 5

            diferencia relativa = 5 / 50 = 10 %
            score = 90
        """
        if global_average <= 0:
            return (
                100.0
                if spread <= 0
                else 0.0
            )

        relative_spread = (
            spread / global_average
        )

        score = (
            100.0
            * (1.0 - relative_spread)
        )

        return max(
            0.0,
            min(100.0, score),
        )

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
                "PowerBalanceRestriction requires "
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
            return f"Team {team_id}"

        return f"Team-{id(team)}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"weight={self.weight}, "
            f"scoring_model="
            f"{self.scoring_model.__class__.__name__})"
        )
