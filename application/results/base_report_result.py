from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from application.results.report_mode import ReportMode
from models.team import Team
from objective.objective_result import ObjectiveResult
from objective.restriction_result import RestrictionResult


@dataclass(slots=True)
class BaseReportResult(ABC):
    """
    Clase base común para todos los resultados que pueden mostrarse
    mediante informes, consola, API o exportadores.

    Centraliza:

        - Equipos resultantes.
        - Resultado del ObjectiveEngine.
        - Puntuación y penalizaciones.
        - Restricciones.
        - Metadatos.
        - Clasificación del equilibrio.
        - Serialización común.
        - Navegación por equipos y restricciones.

    Las subclases deben definir únicamente los datos específicos del
    proceso que generó el resultado.

    Ejemplos:

        OptimizationResult:
            Contiene historial, iteraciones y puntuación inicial.

        EvaluationResult:
            No contiene movimientos y su puntuación inicial coincide
            con la final.

        SimulationResult:
            Podrá incorporar simulaciones, probabilidades o escenarios
            sin obligar a modificar los exportadores existentes.
    """

    teams: Sequence[Team]

    objective_result: ObjectiveResult

    title: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        self.teams = self._validate_teams(
            self.teams
        )

        if not isinstance(
            self.objective_result,
            ObjectiveResult,
        ):
            raise TypeError(
                "objective_result must be an ObjectiveResult instance."
            )

        self.title = self._validate_optional_text(
            self.title
        )

        self.metadata = self._validate_metadata(
            self.metadata
        )

    # ========================================================
    # Contrato que deben implementar las subclases
    # ========================================================

    @property
    @abstractmethod
    def mode(
        self,
    ) -> ReportMode:
        """
        Modo mediante el cual se ha generado el resultado.
        """

    @property
    @abstractmethod
    def initial_score(
        self,
    ) -> float:
        """
        Puntuación anterior al proceso específico de la subclase.
        """

    @property
    @abstractmethod
    def iterations(
        self,
    ) -> int:
        """
        Número de iteraciones o movimientos aceptados.
        """

    @property
    @abstractmethod
    def total_evaluations(
        self,
    ) -> int:
        """
        Número de soluciones o movimientos evaluados.
        """

    @property
    @abstractmethod
    def elapsed_ms(
        self,
    ) -> float:
        """
        Tiempo total consumido por el proceso, en milisegundos.
        """

    @property
    @abstractmethod
    def history(
        self,
    ) -> Any:
        """
        Historial asociado al resultado.

        Una evaluación simple puede devolver una colección vacía.
        """

    # ========================================================
    # Información del modo
    # ========================================================

    @property
    def optimized(
        self,
    ) -> bool:
        """
        Indica si el resultado procede de una optimización.
        """
        return self.mode.optimized

    @property
    def evaluation_only(
        self,
    ) -> bool:
        """
        Indica si los equipos únicamente fueron evaluados.
        """
        return self.mode.evaluation_only

    @property
    def mode_label(
        self,
    ) -> str:
        return self.mode.label

    @property
    def mode_short_label(
        self,
    ) -> str:
        return self.mode.short_label

    @property
    def mode_description(
        self,
    ) -> str:
        return self.mode.description

    # ========================================================
    # Resultado objetivo
    # ========================================================

    @property
    def score(
        self,
    ) -> float:
        """
        Puntuación final del resultado.
        """
        return float(
            self.objective_result.score
        )

    @property
    def final_score(
        self,
    ) -> float:
        return self.score

    @property
    def improvement(
        self,
    ) -> float:
        """
        Diferencia entre la puntuación final y la inicial.
        """
        return (
            self.final_score
            - self.initial_score
        )

    @property
    def penalty(
        self,
    ) -> float:
        """
        Penalización estructural total.
        """
        return float(
            self.objective_result.penalty
        )

    @property
    def restrictions(
        self,
    ) -> dict[str, RestrictionResult]:
        """
        Resultados de las restricciones evaluadas.
        """
        return self.objective_result.restrictions

    @property
    def is_valid(
        self,
    ) -> bool:
        """
        Un resultado es válido cuando no contiene penalizaciones
        estructurales.
        """
        return self.objective_result.is_valid

    @property
    def elapsed(
        self,
    ) -> float:
        """
        Tiempo total consumido, en segundos.
        """
        return (
            self.elapsed_ms
            / 1000.0
        )

    # ========================================================
    # Datos derivados de equipos y jugadores
    # ========================================================

    @property
    def team_count(
        self,
    ) -> int:
        return len(
            self.teams
        )

    @property
    def player_count(
        self,
    ) -> int:
        return sum(
            len(team.players)
            for team in self.teams
        )

    @property
    def team_sizes(
        self,
    ) -> dict[str, int]:
        return {
            self._team_name(
                team=team,
                fallback_index=index,
            ): len(team.players)
            for index, team in enumerate(
                self.teams,
                start=1,
            )
        }

    @property
    def players(
        self,
    ) -> tuple[Any, ...]:
        """
        Devuelve todos los jugadores en el orden de los equipos.
        """
        return tuple(
            player
            for team in self.teams
            for player in team.players
        )

    @property
    def seeded_players(
        self,
    ) -> tuple[Any, ...]:
        return tuple(
            player
            for player in self.players
            if getattr(
                player,
                "seed",
                None,
            )
            is not None
        )

    @property
    def preassigned_players(
        self,
    ) -> tuple[Any, ...]:
        return tuple(
            player
            for player in self.players
            if getattr(
                player,
                "team_number",
                None,
            )
            is not None
        )

    # ========================================================
    # Análisis de restricciones
    # ========================================================

    @property
    def failed_restrictions(
        self,
    ) -> tuple[RestrictionResult, ...]:
        """
        Restricciones que aplican una penalización estructural.
        """
        return tuple(
            restriction
            for restriction
            in self.restrictions.values()
            if restriction.penalty > 0.0
        )

    @property
    def lowest_scoring_restriction(
        self,
    ) -> RestrictionResult | None:
        """
        Restricción con menor puntuación.

        En caso de empate, prioriza la que tenga mayor penalización.
        """
        restriction_values = tuple(
            self.restrictions.values()
        )

        if not restriction_values:
            return None

        return min(
            restriction_values,
            key=lambda restriction: (
                restriction.score,
                -restriction.penalty,
            ),
        )

    @property
    def highest_scoring_restriction(
        self,
    ) -> RestrictionResult | None:
        restriction_values = tuple(
            self.restrictions.values()
        )

        if not restriction_values:
            return None

        return max(
            restriction_values,
            key=lambda restriction: (
                restriction.score,
                -restriction.penalty,
            ),
        )

    # ========================================================
    # Clasificación del equilibrio
    # ========================================================

    @property
    def balance_label(
        self,
    ) -> str:
        """
        Clasificación legible de la calidad del equilibrio.

        Las penalizaciones estructurales tienen prioridad sobre la
        puntuación numérica.
        """
        if not self.is_valid:
            return "Composición inválida"

        if self.final_score >= 95.0:
            return "Muy equilibrados"

        if self.final_score >= 85.0:
            return "Bien equilibrados"

        if self.final_score >= 70.0:
            return "Aceptablemente equilibrados"

        if self.final_score >= 50.0:
            return "Desequilibrados"

        return "Muy desequilibrados"

    @property
    def balance_level(
        self,
    ) -> str:
        """
        Identificador estable para CSS, API o persistencia.
        """
        if not self.is_valid:
            return "invalid"

        if self.final_score >= 95.0:
            return "excellent"

        if self.final_score >= 85.0:
            return "good"

        if self.final_score >= 70.0:
            return "acceptable"

        if self.final_score >= 50.0:
            return "poor"

        return "critical"

    # ========================================================
    # Acceso a equipos
    # ========================================================

    def get_team(
        self,
        team_id: Any,
    ) -> Team | None:
        """
        Busca un equipo mediante su atributo `id`.
        """
        for team in self.teams:
            if getattr(
                team,
                "id",
                None,
            ) == team_id:
                return team

        return None

    def require_team(
        self,
        team_id: Any,
    ) -> Team:
        """
        Obtiene un equipo o genera KeyError cuando no existe.
        """
        team = self.get_team(
            team_id
        )

        if team is None:
            raise KeyError(
                f"Team {team_id!r} was not found."
            )

        return team

    # ========================================================
    # Acceso a restricciones
    # ========================================================

    def get_restriction(
        self,
        name: str,
    ) -> RestrictionResult | None:
        """
        Obtiene una restricción ignorando mayúsculas y minúsculas.
        """
        return self.objective_result.get(
            name
        )

    def require_restriction(
        self,
        name: str,
    ) -> RestrictionResult:
        """
        Obtiene una restricción o genera KeyError.
        """
        restriction = self.get_restriction(
            name
        )

        if restriction is None:
            raise KeyError(
                f"Restriction '{name}' was not found."
            )

        return restriction

    # ========================================================
    # Serialización
    # ========================================================

    def summary(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve un resumen compacto del resultado.
        """
        return {
            "mode": self.mode.value,
            "mode_label": self.mode_label,

            "score": self.final_score,
            "penalty": self.penalty,
            "is_valid": self.is_valid,

            "balance_label": self.balance_label,
            "balance_level": self.balance_level,

            "team_count": self.team_count,
            "player_count": self.player_count,
            "team_sizes": self.team_sizes,

            "iterations": self.iterations,
            "total_evaluations": (
                self.total_evaluations
            ),
            "elapsed_ms": self.elapsed_ms,

            "restriction_scores": (
                self.objective_result.summary()
            ),
        }

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve la parte común serializable del resultado.

        Las subclases pueden extender esta estructura llamando a:

            data = super().as_dict()
            data["history"] = ...
            return data
        """
        return {
            "mode": self.mode.value,
            "mode_information": (
                self.mode.as_dict()
            ),

            "title": self.title,
            "metadata": dict(
                self.metadata
            ),

            "score": self.score,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "improvement": self.improvement,

            "penalty": self.penalty,
            "is_valid": self.is_valid,

            "optimized": self.optimized,
            "evaluation_only": (
                self.evaluation_only
            ),

            "balance_label": self.balance_label,
            "balance_level": self.balance_level,

            "iterations": self.iterations,
            "total_evaluations": (
                self.total_evaluations
            ),

            "elapsed": self.elapsed,
            "elapsed_ms": self.elapsed_ms,

            "team_count": self.team_count,
            "player_count": self.player_count,
            "team_sizes": self.team_sizes,

            "teams": [
                self._team_as_dict(
                    team
                )
                for team in self.teams
            ],

            "objective": (
                self.objective_result.as_dict()
            ),

            "failed_restrictions": [
                restriction.as_dict()
                for restriction
                in self.failed_restrictions
            ],
        }

    @classmethod
    def _team_as_dict(
        cls,
        team: Team,
    ) -> dict[str, Any]:
        """
        Convierte un equipo sin depender de una implementación concreta
        de Team o Player.
        """
        team_id = getattr(
            team,
            "id",
            None,
        )

        team_name = getattr(
            team,
            "name",
            None,
        )

        players = [
            cls._player_as_dict(
                player
            )
            for player in getattr(
                team,
                "players",
                (),
            )
        ]

        return {
            "id": team_id,
            "name": (
                str(team_name)
                if team_name
                else (
                    f"Team {team_id}"
                    if team_id is not None
                    else None
                )
            ),
            "size": len(
                players
            ),
            "players": players,
        }

    @classmethod
    def _player_as_dict(
        cls,
        player: Any,
    ) -> dict[str, Any]:
        nickname = getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                str(player),
            ),
        )

        return {
            "id": getattr(
                player,
                "steam_id",
                getattr(
                    player,
                    "id",
                    None,
                ),
            ),
            "nickname": str(
                nickname
            ),
            "role": cls._role_value(
                getattr(
                    player,
                    "role",
                    None,
                )
            ),
            "seed": getattr(
                player,
                "seed",
                None,
            ),
            "team_number": getattr(
                player,
                "team_number",
                None,
            ),
        }

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> tuple[Team, ...]:
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        try:
            team_list = tuple(
                teams
            )

        except TypeError as error:
            raise TypeError(
                "teams must be a sequence of Team instances."
            ) from error

        if not team_list:
            raise ValueError(
                "At least one team is required."
            )

        seen_team_objects: set[int] = set()
        seen_team_ids: set[Any] = set()

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            if team is None:
                raise ValueError(
                    f"Team {index} cannot be None."
                )

            if not isinstance(
                team,
                Team,
            ):
                raise TypeError(
                    f"Team {index} must be a Team instance."
                )

            team_object_id = id(
                team
            )

            if team_object_id in seen_team_objects:
                raise ValueError(
                    "teams cannot contain duplicated Team instances."
                )

            seen_team_objects.add(
                team_object_id
            )

            team_id = getattr(
                team,
                "id",
                None,
            )

            if team_id is not None:
                if team_id in seen_team_ids:
                    raise ValueError(
                        f"Duplicated team id: {team_id!r}."
                    )

                seen_team_ids.add(
                    team_id
                )

            players = getattr(
                team,
                "players",
                None,
            )

            if players is None:
                raise ValueError(
                    f"Team {index} does not expose players."
                )

            try:
                tuple(
                    players
                )

            except TypeError as error:
                raise TypeError(
                    f"Team {index}.players must be iterable."
                ) from error

        BaseReportResult._validate_unique_players_across_teams(
            team_list
        )

        return team_list

    @staticmethod
    def _validate_unique_players_across_teams(
        teams: Sequence[Team],
    ) -> None:
        """
        Evita que una misma instancia o identidad aparezca en varios
        equipos dentro del resultado.
        """
        object_locations: dict[
            int,
            list[str],
        ] = {}

        identity_locations: dict[
            str,
            list[str],
        ] = {}

        for team_index, team in enumerate(
            teams,
            start=1,
        ):
            team_name = (
                BaseReportResult._team_name(
                    team=team,
                    fallback_index=team_index,
                )
            )

            for player_index, player in enumerate(
                team.players,
                start=1,
            ):
                location = (
                    f"{team_name}[{player_index}]"
                )

                object_locations.setdefault(
                    id(player),
                    [],
                ).append(
                    location
                )

                identity = (
                    BaseReportResult._player_identity(
                        player
                    )
                )

                identity_locations.setdefault(
                    identity,
                    [],
                ).append(
                    location
                )

        duplicated_objects = {
            object_id: locations
            for object_id, locations
            in object_locations.items()
            if len(locations) > 1
        }

        duplicated_identities = {
            identity: locations
            for identity, locations
            in identity_locations.items()
            if len(locations) > 1
        }

        if duplicated_objects:
            raise ValueError(
                "Duplicated Player instances were found across "
                f"teams: {duplicated_objects}."
            )

        if duplicated_identities:
            raise ValueError(
                "Duplicated player identities were found across "
                f"teams: {duplicated_identities}."
            )

    @staticmethod
    def _validate_optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None

    @staticmethod
    def _validate_metadata(
        value: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if value is None:
            return {}

        if not isinstance(
            value,
            Mapping,
        ):
            raise TypeError(
                "metadata must be a mapping."
            )

        return dict(
            value
        )

    # ========================================================
    # Utilidades
    # ========================================================

    @staticmethod
    def _team_name(
        team: Team,
        fallback_index: int,
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
            fallback_index,
        )

        return f"Team {team_id}"

    @staticmethod
    def _player_identity(
        player: Any,
    ) -> str:
        identity = getattr(
            player,
            "identity",
            None,
        )

        if identity:
            return (
                str(identity)
                .strip()
                .casefold()
            )

        steam_id = getattr(
            player,
            "steam_id",
            None,
        )

        if steam_id:
            return (
                "steam:"
                f"{str(steam_id).strip().casefold()}"
            )

        nickname = getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                None,
            ),
        )

        if nickname:
            return (
                "nick:"
                f"{str(nickname).strip().casefold()}"
            )

        return (
            "object:"
            f"{id(player)}"
        )

    @staticmethod
    def _role_value(
        role: Any,
    ) -> Any:
        if role is None:
            return None

        return getattr(
            role,
            "value",
            role,
        )

    # ========================================================
    # Métodos especiales
    # ========================================================

    def __iter__(
        self,
    ):
        return iter(
            self.teams
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self.teams
        )

    def __getitem__(
        self,
        index: int,
    ) -> Team:
        return self.teams[
            index
        ]

    def __contains__(
        self,
        restriction_name: object,
    ) -> bool:
        if not isinstance(
            restriction_name,
            str,
        ):
            return False

        return (
            restriction_name
            in self.objective_result
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"mode={self.mode.value!r}, "
            f"teams={self.team_count}, "
            f"players={self.player_count}, "
            f"score={self.final_score:.2f}, "
            f"improvement={self.improvement:+.2f}, "
            f"iterations={self.iterations}, "
            f"evaluations={self.total_evaluations})"
        )
