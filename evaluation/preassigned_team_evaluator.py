from __future__ import annotations

from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

from application.results.evaluation_result import (
    EvaluationResult,
)
from models.team import Team
from objective.objective_engine import ObjectiveEngine


class PreassignedTeamEvaluator:
    """
    Evalúa una composición de equipos predeterminada.

    Flujo:

        Team[]
            ↓
        ObjectiveEngine.evaluate()
            ↓
        ObjectiveResult
            ↓
        EvaluationResult

    Esta clase:

        - No genera equipos.
        - No intercambia jugadores.
        - No ejecuta LocalOptimizer.
        - No modifica la composición recibida.
        - Realiza una única evaluación objetiva.
        - Mide el tiempo empleado por ObjectiveEngine.

    Está pensada para el modo:

        CSV con columna Team
            ↓
        PreassignedTeamGenerator
            ↓
        PreassignedTeamEvaluator
            ↓
        EvaluationResult
            ↓
        Informe HTML / API / consola
    """

    def __init__(
        self,
        objective_engine: ObjectiveEngine,
        title: str = "Evaluación de equipos predeterminados",
    ) -> None:
        if objective_engine is None:
            raise ValueError(
                "objective_engine cannot be None."
            )

        if not isinstance(
            objective_engine,
            ObjectiveEngine,
        ):
            raise TypeError(
                "objective_engine must be an ObjectiveEngine instance."
            )

        self._objective_engine = objective_engine

        self._title = self._validate_required_text(
            value=title,
            field_name="title",
        )

    # ========================================================
    # Evaluación principal
    # ========================================================

    def evaluate(
        self,
        teams: Sequence[Team],
        metadata: Mapping[str, Any] | None = None,
        title: str | None = None,
    ) -> EvaluationResult:
        """
        Evalúa los equipos y devuelve un EvaluationResult.

        Args:
            teams:
                Composición de equipos que debe analizarse.

            metadata:
                Información opcional del evento.

                Ejemplo:

                    {
                        "event_name": "LAN Sevilla 2026",
                        "number_of_teams": 4,
                        "team_size": 5,
                        "source": "CSV",
                    }

            title:
                Título opcional que sustituye temporalmente al
                configurado en el evaluador.

        Returns:
            EvaluationResult con:

                - equipos originales;
                - puntuación;
                - penalizaciones;
                - restricciones;
                - clasificación del equilibrio;
                - tiempo de evaluación;
                - metadatos del evento.
        """
        team_list = self._validate_teams(
            teams
        )

        resolved_metadata = self._validate_metadata(
            metadata
        )

        resolved_title = (
            self._validate_required_text(
                value=title,
                field_name="title",
            )
            if title is not None
            else self._title
        )

        snapshot_before = self._snapshot_team_players(
            team_list
        )

        started_at = perf_counter()

        objective_result = self._objective_engine.evaluate(
            team_list
        )

        elapsed_ms = (
            perf_counter()
            - started_at
        ) * 1000.0

        snapshot_after = self._snapshot_team_players(
            team_list
        )

        self._validate_teams_unchanged(
            before=snapshot_before,
            after=snapshot_after,
        )

        self._complete_metadata(
            metadata=resolved_metadata,
            teams=team_list,
        )

        return EvaluationResult.from_objective_result(
            teams=team_list,
            objective_result=objective_result,
            elapsed_ms=elapsed_ms,
            title=resolved_title,
            metadata=resolved_metadata,
        )

    def score(
        self,
        teams: Sequence[Team],
    ) -> float:
        """
        Devuelve únicamente la puntuación global.

        También comprueba que ObjectiveEngine no modifique la
        composición recibida.
        """
        team_list = self._validate_teams(
            teams
        )

        snapshot_before = self._snapshot_team_players(
            team_list
        )

        score = float(
            self._objective_engine.score(
                team_list
            )
        )

        snapshot_after = self._snapshot_team_players(
            team_list
        )

        self._validate_teams_unchanged(
            before=snapshot_before,
            after=snapshot_after,
        )

        return score

    # ========================================================
    # Evaluación con configuración de evento
    # ========================================================

    def evaluate_with_event_data(
        self,
        teams: Sequence[Team],
        event_name: str,
        number_of_teams: int,
        team_size: int,
        source: str = "CSV",
    ) -> EvaluationResult:
        """
        Evalúa una composición y añade los metadatos habituales
        del evento.

        También valida que el número y tamaño de los equipos coincidan
        con la configuración indicada.
        """
        event_name = self._validate_required_text(
            value=event_name,
            field_name="event_name",
        )

        number_of_teams = self._validate_positive_integer(
            value=number_of_teams,
            field_name="number_of_teams",
        )

        team_size = self._validate_positive_integer(
            value=team_size,
            field_name="team_size",
        )

        source = self._validate_required_text(
            value=source,
            field_name="source",
        )

        team_list = self._validate_teams(
            teams
        )

        if len(team_list) != number_of_teams:
            raise ValueError(
                "The number of teams does not match the event "
                "configuration. "
                f"Expected: {number_of_teams}. "
                f"Received: {len(team_list)}."
            )

        invalid_teams: list[dict[str, Any]] = []

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            actual_size = len(
                team.players
            )

            if actual_size != team_size:
                invalid_teams.append(
                    {
                        "team": self._team_name(
                            team=team,
                            fallback_index=index,
                        ),
                        "actual_size": actual_size,
                        "expected_size": team_size,
                    }
                )

        if invalid_teams:
            raise ValueError(
                "The predefined teams do not match the configured "
                f"team size. Invalid teams: {invalid_teams}."
            )

        return self.evaluate(
            teams=team_list,
            title=(
                f"Evaluación — {event_name}"
            ),
            metadata={
                "event_name": event_name,
                "number_of_teams": number_of_teams,
                "team_size": team_size,
                "source": source,
            },
        )

    # ========================================================
    # Metadatos
    # ========================================================

    @classmethod
    def _complete_metadata(
        cls,
        metadata: dict[str, Any],
        teams: Sequence[Team],
    ) -> None:
        """
        Completa los metadatos comunes de la evaluación sin
        sobrescribir valores proporcionados por el usuario.
        """
        metadata.setdefault(
            "evaluation_mode",
            "preassigned",
        )

        metadata.setdefault(
            "optimized",
            False,
        )

        metadata.setdefault(
            "composition_preserved",
            True,
        )

        metadata.setdefault(
            "team_count",
            len(teams),
        )

        metadata.setdefault(
            "player_count",
            sum(
                len(team.players)
                for team in teams
            ),
        )

        metadata.setdefault(
            "team_sizes",
            {
                cls._team_name(
                    team=team,
                    fallback_index=index,
                ): len(team.players)
                for index, team in enumerate(
                    teams,
                    start=1,
                )
            },
        )

    # ========================================================
    # Validación de equipos
    # ========================================================

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        try:
            team_list = list(
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
                    f"Team {index} is a duplicated Team instance."
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

        PreassignedTeamEvaluator._validate_unique_players_across_teams(
            team_list
        )

        return team_list

    @staticmethod
    def _validate_unique_players_across_teams(
        teams: Sequence[Team],
    ) -> None:
        """
        Comprueba que ningún jugador aparezca en más de un equipo.

        La comprobación utiliza:

            - Identidad de la instancia.
            - Player.identity.
            - Steam ID.
            - Nick como fallback.
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
                PreassignedTeamEvaluator._team_name(
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
                    PreassignedTeamEvaluator._player_identity(
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

    # ========================================================
    # Protección contra mutaciones
    # ========================================================

    @staticmethod
    def _snapshot_team_players(
        teams: Sequence[Team],
    ) -> tuple[
        tuple[
            int,
            Any,
            str,
            tuple[int, ...],
            tuple[str, ...],
        ],
        ...,
    ]:
        """
        Crea una fotografía estructural de los equipos.

        Incluye:

            - identidad del objeto Team;
            - id del equipo;
            - nombre del equipo;
            - orden e identidad de las instancias Player;
            - identidades lógicas de los jugadores.

        Se utiliza para garantizar que ObjectiveEngine no altere
        accidentalmente la composición evaluada.
        """
        return tuple(
            (
                id(team),
                getattr(
                    team,
                    "id",
                    None,
                ),
                PreassignedTeamEvaluator._team_name(
                    team=team,
                    fallback_index=index,
                ),
                tuple(
                    id(player)
                    for player in team.players
                ),
                tuple(
                    PreassignedTeamEvaluator._player_identity(
                        player
                    )
                    for player in team.players
                ),
            )
            for index, team in enumerate(
                teams,
                start=1,
            )
        )

    @staticmethod
    def _validate_teams_unchanged(
        before: tuple,
        after: tuple,
    ) -> None:
        if before == after:
            return

        raise RuntimeError(
            "ObjectiveEngine modified the predefined teams during "
            "evaluation. Preassigned evaluation must be read-only."
        )

    # ========================================================
    # Validaciones auxiliares
    # ========================================================

    @staticmethod
    def _validate_metadata(
        metadata: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if metadata is None:
            return {}

        if not isinstance(
            metadata,
            Mapping,
        ):
            raise TypeError(
                "metadata must be a mapping or None."
            )

        return dict(
            metadata
        )

    @staticmethod
    def _validate_required_text(
        value: Any,
        field_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _validate_positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return value

    # ========================================================
    # Identidades
    # ========================================================

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

        if nickname is None:
            return (
                "object:"
                f"{id(player)}"
            )

        return (
            "nick:"
            f"{str(nickname).strip().casefold()}"
        )

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

    # ========================================================
    # Propiedades
    # ========================================================

    @property
    def objective_engine(
        self,
    ) -> ObjectiveEngine:
        return self._objective_engine

    @property
    def title(
        self,
    ) -> str:
        return self._title

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"title={self._title!r}, "
            f"objective_engine="
            f"{self._objective_engine.__class__.__name__})"
        )
