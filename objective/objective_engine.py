from __future__ import annotations

from collections.abc import Iterable, Sequence

from models.team import Team
from objective.objective_result import ObjectiveResult
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult


class ObjectiveEngine:
    """
    Coordina la evaluación de todas las restricciones del motor.

    Cada restricción devuelve un RestrictionResult con:

        - score entre 0 y 100;
        - weight;
        - penalty;
        - detalles opcionales.

    ObjectiveEngine no calcula directamente la puntuación final.
    Esa responsabilidad pertenece a ObjectiveResult.
    """

    def __init__(
        self,
        restrictions: Iterable[Restriction],
    ) -> None:
        self._restrictions = self._validate_restrictions(
            restrictions
        )

    def evaluate(
        self,
        teams: Sequence[Team],
    ) -> ObjectiveResult:
        """
        Evalúa todas las restricciones sobre la distribución recibida.

        Returns:
            ObjectiveResult ya calculado.
        """
        team_list = self._validate_teams(
            teams
        )

        result = ObjectiveResult()

        for restriction in self._restrictions:
            restriction_result = restriction.evaluate(
                team_list
            )

            if not isinstance(
                restriction_result,
                RestrictionResult,
            ):
                raise TypeError(
                    f"Restriction '{restriction.name}' must return "
                    "a RestrictionResult instance."
                )

            result.add_result(
                restriction_result
            )

        result.compute()

        return result

    def score(
        self,
        teams: Sequence[Team],
    ) -> float:
        """
        Devuelve únicamente la puntuación final.
        """
        return float(
            self.evaluate(teams).score
        )

    @staticmethod
    def _validate_restrictions(
        restrictions: Iterable[Restriction],
    ) -> tuple[Restriction, ...]:
        if restrictions is None:
            raise ValueError(
                "restrictions cannot be None."
            )

        restriction_list = tuple(
            restrictions
        )

        if not restriction_list:
            raise ValueError(
                "At least one restriction is required."
            )

        names: set[str] = set()

        for index, restriction in enumerate(
            restriction_list,
            start=1,
        ):
            if restriction is None:
                raise ValueError(
                    f"Restriction {index} cannot be None."
                )

            if not isinstance(
                restriction,
                Restriction,
            ):
                raise TypeError(
                    f"Restriction {index} must be a "
                    "Restriction instance."
                )

            name = restriction.name

            if not isinstance(name, str):
                raise TypeError(
                    f"Restriction {index} must expose "
                    "a string name."
                )

            normalized_name = (
                name
                .strip()
                .casefold()
            )

            if not normalized_name:
                raise ValueError(
                    f"Restriction {index} has an empty name."
                )

            if normalized_name in names:
                raise ValueError(
                    f"Duplicated restriction name '{name}'."
                )

            names.add(
                normalized_name
            )

        return restriction_list

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

    @property
    def restrictions(
        self,
    ) -> tuple[Restriction, ...]:
        """
        Devuelve las restricciones como colección inmutable.
        """
        return self._restrictions

    def get_restriction(
        self,
        name: str,
    ) -> Restriction:
        """
        Obtiene una restricción por nombre ignorando mayúsculas.
        """
        if not isinstance(name, str):
            raise TypeError(
                "name must be a string."
            )

        normalized_name = (
            name
            .strip()
            .casefold()
        )

        if not normalized_name:
            raise ValueError(
                "name cannot be empty."
            )

        for restriction in self._restrictions:
            if (
                restriction.name
                .strip()
                .casefold()
                == normalized_name
            ):
                return restriction

        raise KeyError(
            f"Restriction '{name}' was not found."
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self._restrictions
        )

    def __iter__(
        self,
    ):
        return iter(
            self._restrictions
        )

    def __repr__(
        self,
    ) -> str:
        names = ", ".join(
            restriction.name
            for restriction in self._restrictions
        )

        return (
            f"{self.__class__.__name__}("
            f"restrictions=[{names}])"
        )
