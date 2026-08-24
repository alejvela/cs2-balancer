from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from models.player import Player
from models.team import Team


class PreassignedTeamGenerator:
    """
    Construye equipos utilizando la asignación previa de cada jugador.

    Cada jugador debe contener un número de equipo en:

        player.team_number

    También se admite temporalmente como fallback:

        player.assigned_team_number

    Ejemplo:

        player.team_number = 1

    implica que ese jugador será colocado en:

        Equipo 1

    Esta clase no realiza ningún tipo de balanceo.

    Su responsabilidad es exclusivamente transformar:

        Player[]
            ↓
        Team[]

    respetando exactamente la asignación indicada en el CSV.

    Está pensada para el flujo:

        CSV con columna Team
            ↓
        CssStatsImporter
            ↓
        Player.team_number
            ↓
        PreassignedTeamGenerator
            ↓
        Team[]
            ↓
        PreassignedTeamEvaluator

    Validaciones principales:

        - Todos los jugadores deben tener Team.
        - Team debe ser un entero positivo.
        - Team debe estar entre 1 y number_of_teams.
        - No puede haber jugadores duplicados.
        - Opcionalmente todos los equipos deben existir.
        - Opcionalmente cada equipo debe tener un tamaño concreto.
        - Opcionalmente el número total de jugadores debe coincidir
          con el esperado.
    """

    def __init__(
        self,
        expected_team_size: int | None = None,
        expected_player_count: int | None = None,
        team_name_prefix: str = "Team",
        require_all_teams: bool = True,
    ) -> None:
        self._expected_team_size = (
            self._validate_optional_positive_integer(
                value=expected_team_size,
                field_name="expected_team_size",
            )
        )

        self._expected_player_count = (
            self._validate_optional_positive_integer(
                value=expected_player_count,
                field_name="expected_player_count",
            )
        )

        self._team_name_prefix = (
            self._validate_required_text(
                value=team_name_prefix,
                field_name="team_name_prefix",
            )
        )

        if not isinstance(
            require_all_teams,
            bool,
        ):
            raise TypeError(
                "require_all_teams must be a boolean."
            )

        self._require_all_teams = (
            require_all_teams
        )

    # ========================================================
    # Generación
    # ========================================================

    def generate(
        self,
        players: Sequence[Player],
        number_of_teams: int,
    ) -> list[Team]:
        """
        Genera los equipos respetando `player.team_number`.

        Args:
            players:
                Jugadores que deben distribuirse.

            number_of_teams:
                Número total de equipos disponibles.

        Returns:
            Lista de Team ordenada por id:

                Team 1
                Team 2
                ...
                Team N

        Raises:
            ValueError:
                Si la asignación Team es incompleta o inválida.

            TypeError:
                Si los argumentos tienen tipos incorrectos.
        """
        player_list = self._validate_players(
            players
        )

        validated_number_of_teams = (
            self._validate_number_of_teams(
                number_of_teams
            )
        )

        self._validate_expected_player_count(
            players=player_list,
        )

        teams = self._create_teams(
            validated_number_of_teams
        )

        for player in player_list:
            team_number = (
                self._get_team_number(
                    player
                )
            )

            self._validate_team_number_range(
                player=player,
                team_number=team_number,
                number_of_teams=(
                    validated_number_of_teams
                ),
            )

            team_index = (
                team_number - 1
            )

            teams[
                team_index
            ].add(
                player
            )

        self._validate_generated_teams(
            teams=teams,
            number_of_teams=(
                validated_number_of_teams
            ),
        )

        self._validate_assignment_preserved(
            teams
        )

        return teams

    # ========================================================
    # Creación de equipos
    # ========================================================

    def _create_teams(
        self,
        number_of_teams: int,
    ) -> list[Team]:
        """
        Crea todos los equipos vacíos.

        Mantiene compatibilidad con implementaciones de Team cuyo
        constructor acepte:

            Team(id=..., name=...)

        o únicamente:

            Team(id=...)
        """
        teams: list[Team] = []

        for index in range(
            number_of_teams
        ):
            team_id = (
                index + 1
            )

            team_name = (
                f"{self._team_name_prefix} "
                f"{team_id}"
            )

            try:
                team = Team(
                    id=team_id,
                    name=team_name,
                )

            except TypeError:
                team = Team(
                    id=team_id,
                )

                if hasattr(
                    team,
                    "name",
                ):
                    team.name = (
                        team_name
                    )

            teams.append(
                team
            )

        return teams

    # ========================================================
    # Team del jugador
    # ========================================================

    @classmethod
    def _get_team_number(
        cls,
        player: Player,
    ) -> int:
        """
        Obtiene y valida el Team asignado al jugador.

        Prioridad:

            1. player.team_number
            2. player.assigned_team_number

        No se permite None en este generador.
        """
        value = getattr(
            player,
            "team_number",
            None,
        )

        if value is None:
            value = getattr(
                player,
                "assigned_team_number",
                None,
            )

        nickname = cls._player_name(
            player
        )

        if value is None:
            raise ValueError(
                f"Player '{nickname}' does not have "
                "a preassigned team."
            )

        if isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"Team for player '{nickname}' "
                "must be an integer."
            )

        if isinstance(
            value,
            int,
        ):
            team_number = value

        elif isinstance(
            value,
            float,
        ):
            if not value.is_integer():
                raise ValueError(
                    f"Team for player '{nickname}' "
                    f"must be an integer. Received: "
                    f"{value!r}."
                )

            team_number = int(
                value
            )

        elif isinstance(
            value,
            str,
        ):
            normalized = (
                value.strip()
            )

            if not normalized:
                raise ValueError(
                    f"Player '{nickname}' does not have "
                    "a preassigned team."
                )

            try:
                numeric_value = float(
                    normalized
                )

            except ValueError as error:
                raise ValueError(
                    f"Team for player '{nickname}' "
                    f"must be an integer. Received: "
                    f"{value!r}."
                ) from error

            if not numeric_value.is_integer():
                raise ValueError(
                    f"Team for player '{nickname}' "
                    f"must be an integer. Received: "
                    f"{value!r}."
                )

            team_number = int(
                numeric_value
            )

        else:
            raise TypeError(
                f"Team for player '{nickname}' "
                "must be an integer."
            )

        if team_number <= 0:
            raise ValueError(
                f"Team for player '{nickname}' "
                "must be greater than zero."
            )

        return team_number

    @classmethod
    def _validate_team_number_range(
        cls,
        player: Player,
        team_number: int,
        number_of_teams: int,
    ) -> None:
        """
        Comprueba que el Team pertenezca al rango válido.

        Para cuatro equipos:

            1 <= Team <= 4
        """
        if (
            1
            <= team_number
            <= number_of_teams
        ):
            return

        raise ValueError(
            f"Player '{cls._player_name(player)}' "
            f"contains Team={team_number}, but valid "
            f"teams are between 1 and "
            f"{number_of_teams}."
        )

    # ========================================================
    # Validación de entrada
    # ========================================================

    @staticmethod
    def _validate_players(
        players: Sequence[Player],
    ) -> list[Player]:
        """
        Valida la colección de jugadores.
        """
        if players is None:
            raise ValueError(
                "players cannot be None."
            )

        try:
            player_list = list(
                players
            )

        except TypeError as error:
            raise TypeError(
                "players must be a sequence of Player instances."
            ) from error

        if not player_list:
            raise ValueError(
                "At least one player is required."
            )

        for index, player in enumerate(
            player_list,
            start=1,
        ):
            if player is None:
                raise ValueError(
                    f"Player {index} cannot be None."
                )

            if not isinstance(
                player,
                Player,
            ):
                raise TypeError(
                    f"Player {index} must be a Player instance."
                )

        PreassignedTeamGenerator._validate_unique_players(
            player_list
        )

        return player_list

    @staticmethod
    def _validate_unique_players(
        players: Sequence[Player],
    ) -> None:
        """
        Impide duplicados tanto por instancia como por identidad lógica.

        Prioridad para identidad lógica:

            1. player.identity
            2. steam_id
            3. nickname
        """
        object_locations: dict[
            int,
            list[int],
        ] = {}

        identity_locations: dict[
            str,
            list[int],
        ] = {}

        for index, player in enumerate(
            players,
            start=1,
        ):
            object_locations.setdefault(
                id(player),
                [],
            ).append(
                index
            )

            identity = (
                PreassignedTeamGenerator._player_identity(
                    player
                )
            )

            identity_locations.setdefault(
                identity,
                [],
            ).append(
                index
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
                "players contains duplicated Player "
                f"instances: {duplicated_objects}."
            )

        if duplicated_identities:
            raise ValueError(
                "players contains duplicated player "
                f"identities: {duplicated_identities}."
            )

    @staticmethod
    def _validate_number_of_teams(
        number_of_teams: int,
    ) -> int:
        if (
            isinstance(number_of_teams, bool)
            or not isinstance(
                number_of_teams,
                int,
            )
        ):
            raise TypeError(
                "number_of_teams must be an integer."
            )

        if number_of_teams <= 0:
            raise ValueError(
                "number_of_teams must be greater than zero."
            )

        return number_of_teams

    # ========================================================
    # Validaciones del resultado
    # ========================================================

    def _validate_generated_teams(
        self,
        teams: Sequence[Team],
        number_of_teams: int,
    ) -> None:
        """
        Comprueba la estructura final generada.
        """
        if (
            len(teams)
            != number_of_teams
        ):
            raise RuntimeError(
                "The generated number of teams does not match "
                "number_of_teams."
            )

        if self._require_all_teams:
            empty_teams = [
                self._team_name(
                    team=team,
                    fallback_index=index,
                )
                for index, team in enumerate(
                    teams,
                    start=1,
                )
                if not team.players
            ]

            if empty_teams:
                raise ValueError(
                    "Every configured team must contain at least "
                    "one player. Empty teams: "
                    f"{empty_teams}."
                )

        if (
            self._expected_team_size
            is not None
        ):
            invalid_teams: list[
                dict[str, Any]
            ] = []

            for index, team in enumerate(
                teams,
                start=1,
            ):
                actual_size = len(
                    team.players
                )

                if (
                    actual_size
                    != self._expected_team_size
                ):
                    invalid_teams.append(
                        {
                            "team": self._team_name(
                                team=team,
                                fallback_index=index,
                            ),
                            "expected_size": (
                                self._expected_team_size
                            ),
                            "actual_size": (
                                actual_size
                            ),
                        }
                    )

            if invalid_teams:
                raise ValueError(
                    "The predefined teams do not have the "
                    "expected size. "
                    f"Invalid teams: {invalid_teams}."
                )

    def _validate_expected_player_count(
        self,
        players: Sequence[Player],
    ) -> None:
        """
        Comprueba el total de jugadores cuando está configurado.
        """
        if (
            self._expected_player_count
            is None
        ):
            return

        actual_count = len(
            players
        )

        if (
            actual_count
            == self._expected_player_count
        ):
            return

        raise ValueError(
            "The number of players does not match the "
            "configured expected_player_count. "
            f"Expected: {self._expected_player_count}. "
            f"Received: {actual_count}."
        )

    @classmethod
    def _validate_assignment_preserved(
        cls,
        teams: Sequence[Team],
    ) -> None:
        """
        Segunda comprobación de seguridad.

        Después de generar los equipos se verifica que cada jugador
        se encuentre realmente en el Team indicado por su atributo.

        Esta validación permite detectar errores internos en futuras
        modificaciones del generador.
        """
        errors: list[str] = []

        for index, team in enumerate(
            teams,
            start=1,
        ):
            team_id = getattr(
                team,
                "id",
                index,
            )

            try:
                actual_team_number = int(
                    team_id
                )

            except (
                TypeError,
                ValueError,
            ):
                actual_team_number = (
                    index
                )

            for player in team.players:
                assigned_team_number = (
                    cls._get_team_number(
                        player
                    )
                )

                if (
                    assigned_team_number
                    == actual_team_number
                ):
                    continue

                errors.append(
                    f"{cls._player_name(player)}: "
                    f"assigned={assigned_team_number}, "
                    f"generated={actual_team_number}"
                )

        if errors:
            raise RuntimeError(
                "The predefined team assignment was not "
                "preserved: "
                + " | ".join(
                    errors
                )
            )

    # ========================================================
    # Identidad
    # ========================================================

    @staticmethod
    def _player_identity(
        player: Player,
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

        nickname = (
            PreassignedTeamGenerator._player_name(
                player
            )
        )

        return (
            "nick:"
            f"{nickname.casefold()}"
        )

    @staticmethod
    def _player_name(
        player: Player,
    ) -> str:
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
            return "Unknown player"

        normalized = str(
            nickname
        ).strip()

        return (
            normalized
            or "Unknown player"
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

        return (
            f"Team {team_id}"
        )

    # ========================================================
    # Validaciones de configuración
    # ========================================================

    @staticmethod
    def _validate_optional_positive_integer(
        value: Any,
        field_name: str,
    ) -> int | None:
        if value is None:
            return None

        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
        ):
            raise TypeError(
                f"{field_name} must be an integer or None."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return value

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

        normalized = (
            value.strip()
        )

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    # ========================================================
    # Propiedades
    # ========================================================

    @property
    def expected_team_size(
        self,
    ) -> int | None:
        return (
            self._expected_team_size
        )

    @property
    def expected_player_count(
        self,
    ) -> int | None:
        return (
            self._expected_player_count
        )

    @property
    def team_name_prefix(
        self,
    ) -> str:
        return (
            self._team_name_prefix
        )

    @property
    def require_all_teams(
        self,
    ) -> bool:
        return (
            self._require_all_teams
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"expected_team_size="
            f"{self._expected_team_size!r}, "
            f"expected_player_count="
            f"{self._expected_player_count!r}, "
            f"team_name_prefix="
            f"{self._team_name_prefix!r}, "
            f"require_all_teams="
            f"{self._require_all_teams})"
        )
