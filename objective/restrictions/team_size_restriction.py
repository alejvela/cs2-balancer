from __future__ import annotations

from collections.abc import Sequence
from numbers import Real

from models.team import Team
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult


class TeamSizeRestriction(Restriction):
    """
    Comprueba que todos los equipos tengan exactamente el tamaño esperado.

    Es una restricción estructural:

        - Si todos los equipos tienen el tamaño correcto:
            penalty = 0

        - Si existen equipos con un tamaño incorrecto:
            se aplica una penalización proporcional al número de
            posiciones incorrectas.

    La puntuación base permanece en 100 para evitar castigar dos veces:

        1. reduciendo la media ponderada;
        2. restando además una penalización.

    La información sobre el grado de cumplimiento se expone mediante:

        details["compliance_score"]
    """

    DEFAULT_PENALTY_PER_POSITION = 25.0
    MAXIMUM_PENALTY = 100.0

    def __init__(
        self,
        expected_size: int,
        weight: float = 1.0,
        penalty_per_position: float = DEFAULT_PENALTY_PER_POSITION,
    ) -> None:
        if (
            isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
        ):
            raise TypeError(
                "expected_size must be an integer."
            )

        if expected_size <= 0:
            raise ValueError(
                "expected_size must be greater than zero."
            )

        if (
            isinstance(penalty_per_position, bool)
            or not isinstance(penalty_per_position, Real)
        ):
            raise TypeError(
                "penalty_per_position must be numeric."
            )

        penalty_per_position = float(
            penalty_per_position
        )

        if penalty_per_position <= 0.0:
            raise ValueError(
                "penalty_per_position must be greater than zero."
            )

        super().__init__(
            weight=weight
        )

        self._expected_size = expected_size
        self._penalty_per_position = penalty_per_position

    @property
    def name(self) -> str:
        return "Team Size"

    @property
    def expected_size(self) -> int:
        return self._expected_size

    @property
    def penalty_per_position(self) -> float:
        return self._penalty_per_position

    def evaluate(
        self,
        teams: Sequence[Team],
    ) -> RestrictionResult:
        """
        Evalúa el tamaño de todos los equipos.

        La penalización se calcula usando el número total de posiciones
        incorrectas.

        Ejemplo:

            esperado: [5, 5, 5, 5]
            actual:   [5, 5, 6, 4]

            diferencias absolutas: [0, 0, 1, 1]
            posiciones incorrectas: 2
        """
        team_list = self._validate_teams(
            teams
        )

        team_sizes: dict[str, int] = {}
        invalid_teams: list[dict[str, int | str]] = []

        total_absolute_difference = 0

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            team_name = self._team_name(
                team=team,
                fallback_index=index,
            )

            players = team.players

            actual_size = len(
                players
            )

            difference = (
                actual_size
                - self._expected_size
            )

            absolute_difference = abs(
                difference
            )

            team_sizes[team_name] = actual_size

            total_absolute_difference += (
                absolute_difference
            )

            if difference != 0:
                invalid_teams.append(
                    {
                        "team": team_name,
                        "actual_size": actual_size,
                        "expected_size": self._expected_size,
                        "difference": difference,
                        "absolute_difference": (
                            absolute_difference
                        ),
                    }
                )

        valid = not invalid_teams

        penalty = self._calculate_penalty(
            total_absolute_difference
        )

        compliance_score = self._calculate_compliance_score(
            total_absolute_difference=total_absolute_difference,
            team_count=len(team_list),
        )

        result = RestrictionResult(
            name=self.name,

            # La restricción contribuye de manera neutra a la media.
            # El incumplimiento se representa exclusivamente mediante
            # penalty, evitando un castigo duplicado.
            score=100.0,

            penalty=penalty,
            weight=self.weight,
        )

        result.add_detail(
            "structural_restriction",
            True,
        )

        result.add_detail(
            "expected_size",
            self._expected_size,
        )

        result.add_detail(
            "team_count",
            len(team_list),
        )

        result.add_detail(
            "expected_player_count",
            (
                len(team_list)
                * self._expected_size
            ),
        )

        result.add_detail(
            "actual_player_count",
            sum(team_sizes.values()),
        )

        result.add_detail(
            "team_sizes",
            team_sizes,
        )

        result.add_detail(
            "invalid_teams",
            invalid_teams,
        )

        result.add_detail(
            "invalid_team_count",
            len(invalid_teams),
        )

        result.add_detail(
            "total_absolute_difference",
            total_absolute_difference,
        )

        result.add_detail(
            "compliance_score",
            compliance_score,
        )

        result.add_detail(
            "penalty_per_position",
            self._penalty_per_position,
        )

        result.add_detail(
            "valid",
            valid,
        )

        return result

    def _calculate_penalty(
        self,
        total_absolute_difference: int,
    ) -> float:
        """
        Calcula una penalización proporcional al número de posiciones
        incorrectas y la limita a 100 puntos.
        """
        if total_absolute_difference <= 0:
            return 0.0

        penalty = (
            total_absolute_difference
            * self._penalty_per_position
        )

        return min(
            self.MAXIMUM_PENALTY,
            penalty,
        )

    def _calculate_compliance_score(
        self,
        total_absolute_difference: int,
        team_count: int,
    ) -> float:
        """
        Calcula un indicador informativo de cumplimiento entre 0 y 100.

        Este valor no participa directamente en ObjectiveResult porque
        el incumplimiento ya se representa mediante penalty.
        """
        expected_player_count = (
            team_count
            * self._expected_size
        )

        if expected_player_count <= 0:
            return 0.0

        error_ratio = (
            total_absolute_difference
            / expected_player_count
        )

        compliance_score = (
            100.0
            * (1.0 - error_ratio)
        )

        return max(
            0.0,
            min(
                100.0,
                compliance_score,
            ),
        )

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        """
        Valida la colección de equipos.

        Una colección vacía se considera un error de entrada y no una
        distribución evaluable.
        """
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

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"expected_size={self._expected_size}, "
            f"weight={self.weight:.2f}, "
            f"penalty_per_position="
            f"{self._penalty_per_position:.2f})"
        )
