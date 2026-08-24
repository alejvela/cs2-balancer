from __future__ import annotations

from collections.abc import Sequence
from numbers import Real
from typing import Any

from models.team import Team
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult


class SeedSeparationRestriction(Restriction):
    """
    Evita que varios cabezas de serie del mismo nivel coincidan
    en un mismo equipo.

    Regla predeterminada:

        máximo un jugador con seed=1 por equipo.

    Es una restricción estructural:

        - Tiene un peso positivo mínimo para ser compatible con
          la clase base Restriction.
        - Mantiene score=100.
        - Aplica una penalización elevada cuando se incumple la regla.
    """

    DEFAULT_SEED_LEVEL = 1
    DEFAULT_MAXIMUM_PER_TEAM = 1
    DEFAULT_PENALTY_PER_EXCESS_PLAYER = 100.0
    DEFAULT_MAXIMUM_PENALTY = 100.0
    DEFAULT_WEIGHT = 1.0

    def __init__(
        self,
        seed_level: int = DEFAULT_SEED_LEVEL,
        maximum_per_team: int = DEFAULT_MAXIMUM_PER_TEAM,
        penalty_per_excess_player: float = (
            DEFAULT_PENALTY_PER_EXCESS_PLAYER
        ),
        maximum_penalty: float = DEFAULT_MAXIMUM_PENALTY,
        weight: float = DEFAULT_WEIGHT,
    ) -> None:
        if (
            isinstance(seed_level, bool)
            or not isinstance(seed_level, int)
        ):
            raise TypeError(
                "seed_level must be an integer."
            )

        if seed_level <= 0:
            raise ValueError(
                "seed_level must be greater than zero."
            )

        if (
            isinstance(maximum_per_team, bool)
            or not isinstance(maximum_per_team, int)
        ):
            raise TypeError(
                "maximum_per_team must be an integer."
            )

        if maximum_per_team < 0:
            raise ValueError(
                "maximum_per_team cannot be negative."
            )

        self._validate_positive_number(
            value=penalty_per_excess_player,
            field_name="penalty_per_excess_player",
        )

        self._validate_positive_number(
            value=maximum_penalty,
            field_name="maximum_penalty",
        )

        self._validate_positive_number(
            value=weight,
            field_name="weight",
        )

        super().__init__(
            weight=float(weight),
        )

        self._seed_level = seed_level
        self._maximum_per_team = maximum_per_team
        self._penalty_per_excess_player = float(
            penalty_per_excess_player
        )
        self._maximum_penalty = float(
            maximum_penalty
        )

    @property
    def name(self) -> str:
        return (
            f"Seed {self._seed_level} Separation"
        )

    @property
    def seed_level(self) -> int:
        return self._seed_level

    @property
    def maximum_per_team(self) -> int:
        return self._maximum_per_team

    @property
    def penalty_per_excess_player(self) -> float:
        return self._penalty_per_excess_player

    @property
    def maximum_penalty(self) -> float:
        return self._maximum_penalty

    def evaluate(
        self,
        teams: Sequence[Team],
    ) -> RestrictionResult:
        """
        Evalúa la distribución de cabezas de serie.

        La penalización se calcula según el número total de jugadores
        que superan el máximo permitido por equipo.
        """
        team_list = self._validate_teams(
            teams
        )

        violations: list[dict[str, Any]] = []
        team_seed_counts: dict[str, int] = {}
        team_seed_players: dict[str, list[str]] = {}

        total_seeded_players = 0
        total_excess = 0

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            team_name = self._team_name(
                team=team,
                fallback_index=index,
            )

            seeded_players = [
                player
                for player in team.players
                if getattr(
                    player,
                    "seed",
                    None,
                ) == self._seed_level
            ]

            seeded_player_names = [
                self._player_name(player)
                for player in seeded_players
            ]

            seed_count = len(
                seeded_players
            )

            excess = max(
                0,
                seed_count - self._maximum_per_team,
            )

            total_seeded_players += seed_count
            total_excess += excess

            team_seed_counts[
                team_name
            ] = seed_count

            team_seed_players[
                team_name
            ] = seeded_player_names

            if excess > 0:
                violations.append(
                    {
                        "team": team_name,
                        "seed_level": self._seed_level,
                        "seed_count": seed_count,
                        "maximum_allowed": (
                            self._maximum_per_team
                        ),
                        "excess": excess,
                        "players": seeded_player_names,
                    }
                )

        penalty = self._calculate_penalty(
            total_excess
        )

        valid = (
            total_excess == 0
        )

        result = RestrictionResult(
            name=self.name,

            # La restricción siempre aporta una puntuación base perfecta.
            # El incumplimiento se representa únicamente con penalty.
            score=100.0,

            penalty=penalty,
            weight=self.weight,
        )

        result.add_detail(
            "structural_restriction",
            True,
        )

        result.add_detail(
            "seed_level",
            self._seed_level,
        )

        result.add_detail(
            "maximum_per_team",
            self._maximum_per_team,
        )

        result.add_detail(
            "team_seed_counts",
            team_seed_counts,
        )

        result.add_detail(
            "team_seed_players",
            team_seed_players,
        )

        result.add_detail(
            "total_seeded_players",
            total_seeded_players,
        )

        result.add_detail(
            "violations",
            violations,
        )

        result.add_detail(
            "violation_count",
            len(violations),
        )

        result.add_detail(
            "total_excess",
            total_excess,
        )

        result.add_detail(
            "penalty_per_excess_player",
            self._penalty_per_excess_player,
        )

        result.add_detail(
            "maximum_penalty",
            self._maximum_penalty,
        )

        result.add_detail(
            "valid",
            valid,
        )

        return result

    def _calculate_penalty(
        self,
        total_excess: int,
    ) -> float:
        if total_excess <= 0:
            return 0.0

        penalty = (
            total_excess
            * self._penalty_per_excess_player
        )

        return min(
            self._maximum_penalty,
            penalty,
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

        if not team_list:
            raise ValueError(
                "At least one team is required."
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
    def _player_name(
        player,
    ) -> str:
        return str(
            getattr(
                player,
                "nickname",
                getattr(
                    player,
                    "nick",
                    "Unknown",
                ),
            )
        )

    @staticmethod
    def _validate_positive_number(
        value: float,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
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
            f"seed_level={self._seed_level}, "
            f"maximum_per_team={self._maximum_per_team}, "
            f"penalty_per_excess_player="
            f"{self._penalty_per_excess_player:.2f}, "
            f"maximum_penalty="
            f"{self._maximum_penalty:.2f}, "
            f"weight={self.weight:.2f})"
        )
