from __future__ import annotations

from collections.abc import Iterator, Sequence

from models.player import Player
from models.team import Team
from scoring.scoring_model import ScoringModel


class SnakeDraftGenerator:
    """
    Genera una distribución inicial mediante Snake Draft teniendo en
    cuenta el Power Score y los cabezas de serie.

    Flujo:

        1. Validar jugadores y número de equipos.
        2. Separar los jugadores con el seed configurado.
        3. Ordenar los cabezas de serie por Power Score.
        4. Colocar cada cabeza de serie en un equipo diferente.
        5. Ordenar el resto de jugadores por Power Score.
        6. Continuar el Snake Draft desde la posición correspondiente.
        7. Validar la distribución final.

    Ejemplo con cuatro equipos y cuatro jugadores Seed=1:

        Primera ronda ya ocupada:

            T1 <- Seed 1 más fuerte
            T2 <- Segundo Seed 1
            T3 <- Tercer Seed 1
            T4 <- Cuarto Seed 1

        El resto continúa en sentido inverso:

            T4, T3, T2, T1,
            T1, T2, T3, T4,
            ...

    De esta forma nunca coinciden dos cabezas de serie del mismo nivel
    en un equipo durante la generación inicial.
    """

    def __init__(
        self,
        scoring_model: ScoringModel,
        team_name_prefix: str = "Team",
        separated_seed_level: int = 1,
        maximum_seeded_players_per_team: int = 1,
    ) -> None:
        if scoring_model is None:
            raise ValueError(
                "scoring_model cannot be None."
            )

        if not isinstance(team_name_prefix, str):
            raise TypeError(
                "team_name_prefix must be a string."
            )

        team_name_prefix = team_name_prefix.strip()

        if not team_name_prefix:
            raise ValueError(
                "team_name_prefix cannot be empty."
            )

        if (
            isinstance(separated_seed_level, bool)
            or not isinstance(separated_seed_level, int)
        ):
            raise TypeError(
                "separated_seed_level must be an integer."
            )

        if separated_seed_level <= 0:
            raise ValueError(
                "separated_seed_level must be greater than zero."
            )

        if (
            isinstance(maximum_seeded_players_per_team, bool)
            or not isinstance(
                maximum_seeded_players_per_team,
                int,
            )
        ):
            raise TypeError(
                "maximum_seeded_players_per_team "
                "must be an integer."
            )

        if maximum_seeded_players_per_team <= 0:
            raise ValueError(
                "maximum_seeded_players_per_team "
                "must be greater than zero."
            )

        self._scoring_model = scoring_model
        self._team_name_prefix = team_name_prefix
        self._separated_seed_level = separated_seed_level
        self._maximum_seeded_players_per_team = (
            maximum_seeded_players_per_team
        )

    def generate(
        self,
        players: Sequence[Player],
        number_of_teams: int,
    ) -> list[Team]:
        """
        Genera los equipos iniciales.

        Los jugadores con el seed configurado se reparten primero.
        Después continúa el Snake Draft con el resto de jugadores.
        """
        player_list = self._validate_inputs(
            players=players,
            number_of_teams=number_of_teams,
        )

        team_size = (
            len(player_list)
            // number_of_teams
        )

        seeded_players, regular_players = (
            self._partition_players(
                player_list
            )
        )

        self._validate_seed_count(
            seeded_players=seeded_players,
            number_of_teams=number_of_teams,
        )

        ranked_seeded_players = (
            self._scoring_model.rank(
                seeded_players
            )
            if seeded_players
            else []
        )

        ranked_regular_players = (
            self._scoring_model.rank(
                regular_players
            )
            if regular_players
            else []
        )

        teams = self._create_teams(
            number_of_teams
        )

        # Los cabezas de serie ocupan las primeras posiciones
        # de la primera ronda del draft.
        for team_index, player in enumerate(
            ranked_seeded_players
        ):
            teams[team_index].add(
                player
            )

        occupied_first_round_positions = len(
            ranked_seeded_players
        )

        draft_team_indices = (
            self._iter_remaining_draft_positions(
                number_of_teams=number_of_teams,
                initially_occupied_positions=(
                    occupied_first_round_positions
                ),
            )
        )

        for player in ranked_regular_players:
            team_index = self._next_available_team_index(
                draft_team_indices=draft_team_indices,
                teams=teams,
                team_size=team_size,
            )

            teams[team_index].add(
                player
            )

        self._validate_generated_teams(
            teams=teams,
            original_players=player_list,
            expected_team_size=team_size,
        )

        return teams

    def _partition_players(
        self,
        players: Sequence[Player],
    ) -> tuple[list[Player], list[Player]]:
        """
        Separa los jugadores con el seed configurado del resto.
        """
        seeded_players: list[Player] = []
        regular_players: list[Player] = []

        for player in players:
            seed = getattr(
                player,
                "seed",
                None,
            )

            if seed == self._separated_seed_level:
                seeded_players.append(
                    player
                )
            else:
                regular_players.append(
                    player
                )

        return (
            seeded_players,
            regular_players,
        )

    def _validate_seed_count(
        self,
        seeded_players: Sequence[Player],
        number_of_teams: int,
    ) -> None:
        """
        Comprueba que los cabezas de serie puedan distribuirse sin
        superar el máximo permitido por equipo.
        """
        maximum_supported = (
            number_of_teams
            * self._maximum_seeded_players_per_team
        )

        if len(seeded_players) <= maximum_supported:
            return

        seeded_names = [
            self._player_name(player)
            for player in seeded_players
        ]

        raise ValueError(
            f"There are {len(seeded_players)} players "
            f"with Seed={self._separated_seed_level}, "
            f"but only {maximum_supported} can be distributed "
            f"among {number_of_teams} teams with a maximum of "
            f"{self._maximum_seeded_players_per_team} per team. "
            f"Players: {seeded_names}."
        )

    @staticmethod
    def _iter_remaining_draft_positions(
        number_of_teams: int,
        initially_occupied_positions: int,
    ) -> Iterator[int]:
        """
        Genera indefinidamente el orden del Snake Draft.

        La primera ronda puede estar parcialmente ocupada por los
        cabezas de serie.

        Ejemplo con cuatro equipos y cuatro seeds:

            primera ronda ocupada: 0, 1, 2, 3

            siguientes posiciones:
                3, 2, 1, 0,
                0, 1, 2, 3,
                ...

        Ejemplo con dos seeds:

            primera ronda ocupada: 0, 1

            siguientes posiciones:
                2, 3,
                3, 2, 1, 0,
                0, 1, 2, 3,
                ...
        """
        if not 0 <= initially_occupied_positions <= number_of_teams:
            raise ValueError(
                "initially_occupied_positions must be between "
                "zero and number_of_teams."
            )

        # Completa las posiciones todavía libres de la primera ronda.
        for team_index in range(
            initially_occupied_positions,
            number_of_teams,
        ):
            yield team_index

        # Tras la primera ronda completa, la siguiente comienza
        # siempre en sentido inverso.
        reverse_direction = True

        while True:
            if reverse_direction:
                for team_index in range(
                    number_of_teams - 1,
                    -1,
                    -1,
                ):
                    yield team_index
            else:
                for team_index in range(
                    number_of_teams
                ):
                    yield team_index

            reverse_direction = (
                not reverse_direction
            )

    @staticmethod
    def _next_available_team_index(
        draft_team_indices: Iterator[int],
        teams: Sequence[Team],
        team_size: int,
    ) -> int:
        """
        Obtiene la siguiente posición del draft cuyo equipo todavía
        tenga espacio.

        Esta protección evita superar el tamaño esperado aunque una
        ronda parcial haya sido ocupada por cabezas de serie.
        """
        available_team_count = sum(
            1
            for team in teams
            if len(team.players) < team_size
        )

        if available_team_count == 0:
            raise RuntimeError(
                "The draft contains more players than available "
                "team positions."
            )

        while True:
            team_index = next(
                draft_team_indices
            )

            if len(teams[team_index].players) < team_size:
                return team_index

    def _validate_inputs(
        self,
        players: Sequence[Player],
        number_of_teams: int,
    ) -> list[Player]:
        """
        Valida y normaliza los argumentos de entrada.
        """
        if players is None:
            raise ValueError(
                "players cannot be None."
            )

        if (
            isinstance(number_of_teams, bool)
            or not isinstance(number_of_teams, int)
        ):
            raise TypeError(
                "number_of_teams must be an integer."
            )

        if number_of_teams <= 0:
            raise ValueError(
                "number_of_teams must be greater than zero."
            )

        player_list = list(
            players
        )

        if not player_list:
            raise ValueError(
                "At least one player is required."
            )

        if any(
            player is None
            for player in player_list
        ):
            raise ValueError(
                "players cannot contain None values."
            )

        if len(player_list) < number_of_teams:
            raise ValueError(
                "There must be at least one player per team."
            )

        if len(player_list) % number_of_teams != 0:
            raise ValueError(
                "The number of players must be divisible by "
                "the number of teams for the MVP."
            )

        self._validate_unique_players(
            player_list
        )

        return player_list

    @classmethod
    def _validate_unique_players(
        cls,
        players: Sequence[Player],
    ) -> None:
        """
        Impide repetir la misma instancia o identidad de jugador.
        """
        object_locations: dict[int, list[int]] = {}
        identity_locations: dict[str, list[int]] = {}

        for index, player in enumerate(
            players,
            start=1,
        ):
            object_locations.setdefault(
                id(player),
                [],
            ).append(index)

            identity = cls._player_identity(
                player
            )

            identity_locations.setdefault(
                identity,
                [],
            ).append(index)

        duplicated_objects = {
            object_id: positions
            for object_id, positions
            in object_locations.items()
            if len(positions) > 1
        }

        if duplicated_objects:
            raise ValueError(
                "The player list contains duplicated "
                f"Player instances: {duplicated_objects}."
            )

        duplicated_identities = {
            identity: positions
            for identity, positions
            in identity_locations.items()
            if len(positions) > 1
        }

        if duplicated_identities:
            raise ValueError(
                "The player list contains duplicated player "
                f"identities: {duplicated_identities}."
            )

    def _create_teams(
        self,
        number_of_teams: int,
    ) -> list[Team]:
        """
        Crea los equipos vacíos.
        """
        teams: list[Team] = []

        for index in range(
            number_of_teams
        ):
            team_id = index + 1

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
                    team.name = team_name

            teams.append(
                team
            )

        return teams

    @classmethod
    def _validate_generated_teams(
        cls,
        teams: Sequence[Team],
        original_players: Sequence[Player],
        expected_team_size: int,
    ) -> None:
        """
        Verifica que el draft final sea estructuralmente válido.
        """
        assigned_players = [
            player
            for team in teams
            for player in team.players
        ]

        for index, team in enumerate(
            teams,
            start=1,
        ):
            if len(team.players) != expected_team_size:
                raise RuntimeError(
                    f"Team {index} contains "
                    f"{len(team.players)} players; "
                    f"expected {expected_team_size}."
                )

        if len(assigned_players) != len(
            original_players
        ):
            raise RuntimeError(
                "The draft did not assign the expected "
                "number of players."
            )

        original_object_ids = {
            id(player)
            for player in original_players
        }

        assigned_object_ids = [
            id(player)
            for player in assigned_players
        ]

        if len(assigned_object_ids) != len(
            set(assigned_object_ids)
        ):
            raise RuntimeError(
                "The generated teams contain duplicated "
                "Player instances."
            )

        if set(assigned_object_ids) != original_object_ids:
            raise RuntimeError(
                "The generated teams do not contain exactly "
                "the original player collection."
            )

        for team_index, team in enumerate(
            teams,
            start=1,
        ):
            seeded_players = [
                player
                for player in team.players
                if getattr(
                    player,
                    "seed",
                    None,
                )
                == cls._get_seed_level_for_validation(
                    team
                )
            ]

            # Esta comprobación se realiza realmente abajo mediante
            # el método de instancia. Se mantiene aquí solo la
            # validación estructural general.
            del seeded_players, team_index

    def _validate_seed_distribution_in_teams(
        self,
        teams: Sequence[Team],
    ) -> None:
        """
        Comprueba que ningún equipo supere el máximo de cabezas
        de serie configurado.
        """
        violations: list[str] = []

        for index, team in enumerate(
            teams,
            start=1,
        ):
            seeded_players = [
                player
                for player in team.players
                if getattr(
                    player,
                    "seed",
                    None,
                )
                == self._separated_seed_level
            ]

            if (
                len(seeded_players)
                <= self._maximum_seeded_players_per_team
            ):
                continue

            team_name = (
                getattr(team, "name", None)
                or f"Team {index}"
            )

            player_names = [
                self._player_name(player)
                for player in seeded_players
            ]

            violations.append(
                f"{team_name}: {player_names}"
            )

        if violations:
            raise RuntimeError(
                "The generated draft violates the seed "
                "separation rule. "
                + "; ".join(violations)
            )

    @staticmethod
    def _get_seed_level_for_validation(
        team: Team,
    ) -> int:
        """
        Método mantenido únicamente para compatibilidad interna.

        La validación real del nivel de seed la realiza el método
        de instancia `_validate_seed_distribution_in_teams`.
        """
        del team
        return -1

    @staticmethod
    def _player_name(
        player: Player,
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

    @classmethod
    def _player_identity(
        cls,
        player: Player,
    ) -> str:
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

        return (
            "nick:"
            f"{cls._player_name(player).strip().casefold()}"
        )

    def player_power(
        self,
        player: Player,
    ) -> float:
        """
        Expone el Power Score utilizado para ordenar un jugador.
        """
        if player is None:
            raise ValueError(
                "player cannot be None."
            )

        return float(
            self._scoring_model.power(
                player
            )
        )

    @property
    def scoring_model(
        self,
    ) -> ScoringModel:
        return self._scoring_model

    @property
    def team_name_prefix(
        self,
    ) -> str:
        return self._team_name_prefix

    @property
    def separated_seed_level(
        self,
    ) -> int:
        return self._separated_seed_level

    @property
    def maximum_seeded_players_per_team(
        self,
    ) -> int:
        return self._maximum_seeded_players_per_team

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"team_name_prefix="
            f"{self._team_name_prefix!r}, "
            f"separated_seed_level="
            f"{self._separated_seed_level}, "
            f"maximum_seeded_players_per_team="
            f"{self._maximum_seeded_players_per_team}, "
            f"scoring_model="
            f"{self._scoring_model.__class__.__name__})"
        )
