from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from models.player import Player
from models.team import Team


@dataclass(
    frozen=True,
    slots=True,
    order=True,
)
class SolutionSignature:
    """
    Firma canónica de una distribución de equipos.

    Su objetivo es representar una solución de forma:

        - Determinista.
        - Comparable.
        - Independiente del orden de los jugadores.
        - Independiente del orden de los equipos.
        - Estable entre distintas ejecuciones.

    Esto permite que dos composiciones lógicamente equivalentes
    produzcan exactamente la misma firma.

    Ejemplo:

        Solución A:

            Equipo 1:
                snkr
                futu
                neko
                zaki
                hotta

            Equipo 2:
                robert
                zek
                domink
                rustu
                jotanei

        y otra solución con:

            - los mismos jugadores;
            - dentro de los mismos grupos;
            - pero con diferente orden interno;
            - o con los equipos numerados al revés;

        producen la misma SolutionSignature.

    La firma se utiliza para:

        1. Detectar soluciones repetidas.
        2. Contar soluciones únicas.
        3. Resolver empates de puntuación.
        4. Garantizar reproducibilidad.
        5. Evitar que la numeración arbitraria de equipos afecte
           al resultado final.

    La identidad del jugador se resuelve con esta prioridad:

        1. player.identity
        2. player.steam_id
        3. player.nickname / player.nick

    Cuando no existe ninguna identidad útil, se genera una identidad
    basada en los datos básicos del jugador.

    El uso de id(player) se evita deliberadamente porque cambia entre
    ejecuciones y rompería la reproducibilidad.
    """

    teams: tuple[
        tuple[str, ...],
        ...,
    ]

    # ========================================================
    # Construcción
    # ========================================================

    @classmethod
    def from_teams(
        cls,
        teams: Sequence[Team],
    ) -> SolutionSignature:
        """
        Construye una firma canónica a partir de una colección
        de equipos.

        El proceso es:

            1. Obtener la identidad estable de cada jugador.
            2. Ordenar las identidades dentro de cada equipo.
            3. Convertir cada equipo en una tupla.
            4. Ordenar los equipos por su propia firma.
            5. Construir la firma global.

        El número o nombre del equipo NO forma parte de la firma.

        Esto es deliberado:

            Equipo 1 = A,B,C,D,E
            Equipo 2 = F,G,H,I,J

        es lógicamente equivalente a:

            Equipo 1 = F,G,H,I,J
            Equipo 2 = A,B,C,D,E

        para un problema de balanceo donde los nombres de los equipos
        son simplemente etiquetas.
        """
        team_list = cls._validate_teams(
            teams
        )

        canonical_teams: list[
            tuple[str, ...]
        ] = []

        global_players: list[
            str
        ] = []

        for team in team_list:
            players = cls._team_players(
                team
            )

            identities = tuple(
                sorted(
                    cls.player_identity(
                        player
                    )
                    for player in players
                )
            )

            canonical_teams.append(
                identities
            )

            global_players.extend(
                identities
            )

        cls._validate_unique_identities(
            global_players
        )

        ordered_teams = tuple(
            sorted(
                canonical_teams
            )
        )

        return cls(
            teams=ordered_teams
        )

    # ========================================================
    # Identidad del jugador
    # ========================================================

    @classmethod
    def player_identity(
        cls,
        player: Player,
    ) -> str:
        """
        Devuelve una identidad determinista para un jugador.

        Prioridad:

            identity
                ↓
            steam_id
                ↓
            nickname
                ↓
            fallback estructural

        La identidad se normaliza con casefold().
        """
        if player is None:
            raise ValueError(
                "player cannot be None."
            )

        explicit_identity = getattr(
            player,
            "identity",
            None,
        )

        normalized_identity = (
            cls._normalize_text(
                explicit_identity
            )
        )

        if normalized_identity:
            return (
                "identity:"
                f"{normalized_identity}"
            )

        steam_id = (
            cls._normalize_text(
                getattr(
                    player,
                    "steam_id",
                    None,
                )
            )
        )

        if steam_id:
            return (
                "steam:"
                f"{steam_id}"
            )

        nickname = cls._normalize_text(
            getattr(
                player,
                "nickname",
                getattr(
                    player,
                    "nick",
                    None,
                ),
            )
        )

        if nickname:
            return (
                "nick:"
                f"{nickname}"
            )

        return (
            cls._fallback_player_identity(
                player
            )
        )

    @classmethod
    def _fallback_player_identity(
        cls,
        player: Player,
    ) -> str:
        """
        Último recurso para jugadores sin identidad explícita.

        Se evita utilizar id(player) porque no es estable entre
        ejecuciones.

        Esta identidad no debería utilizarse normalmente si el modelo
        Player está correctamente construido.
        """
        attributes = (
            "elo",
            "level",
            "kd",
            "rating",
            "adr",
            "kpr",
            "dpr",
            "hs",
            "kast",
            "winrate",
            "clutch",
            "matches",
            "seed",
        )

        values: list[str] = []

        for attribute in attributes:
            value = getattr(
                player,
                attribute,
                None,
            )

            values.append(

                    f"{attribute}="
                    f"{cls._stable_value(value)}"

            )

        return (
            "anonymous:"
            + "|".join(
                values
            )
        )

    # ========================================================
    # Información derivada
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
            len(team)
            for team in self.teams
        )

    @property
    def team_sizes(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            len(team)
            for team in self.teams
        )

    @property
    def players(
        self,
    ) -> tuple[str, ...]:
        """
        Jugadores de la solución ordenados globalmente.
        """
        return tuple(
            sorted(
                identity
                for team in self.teams
                for identity in team
            )
        )

    # ========================================================
    # Representación textual
    # ========================================================

    @property
    def compact(
        self,
    ) -> str:
        """
        Representación compacta y completamente determinista.

        Ejemplo:

            nick:a,nick:b,nick:c|
            nick:d,nick:e,nick:f
        """
        return "|".join(
            ",".join(
                team
            )
            for team in self.teams
        )

    @property
    def pretty(
        self,
    ) -> str:
        """
        Representación más legible para depuración.
        """
        lines: list[str] = []

        for index, team in enumerate(
            self.teams,
            start=1,
        ):
            lines.append(

                    f"Team {index}: "
                    + ", ".join(
                        team
                    )

            )

        return "\n".join(
            lines
        )

    # ========================================================
    # Hash estable
    # ========================================================

    @property
    def stable_hash(
        self,
    ) -> str:
        """
        Devuelve un identificador hexadecimal estable.

        No utiliza hash() de Python porque éste puede variar entre
        procesos debido a hash randomization.

        Se utiliza FNV-1a de 64 bits, suficiente para identificar
        soluciones durante la optimización sin introducir una
        dependencia adicional.
        """
        data = self.compact.encode(
            "utf-8"
        )

        value = (
            14695981039346656037
        )

        prime = (
            1099511628211
        )

        mask = (
            0xFFFFFFFFFFFFFFFF
        )

        for byte in data:
            value ^= byte

            value = (
                value
                * prime
            ) & mask

        return (
            f"{value:016x}"
        )

    # ========================================================
    # Comparaciones
    # ========================================================

    def equivalent_to(
        self,
        other: SolutionSignature,
    ) -> bool:
        """
        Indica si dos firmas representan exactamente la misma
        distribución lógica.
        """
        if not isinstance(
            other,
            SolutionSignature,
        ):
            return False

        return (
            self.teams
            == other.teams
        )

    def same_player_pool(
        self,
        other: SolutionSignature,
    ) -> bool:
        """
        Indica si ambas soluciones contienen exactamente los mismos
        jugadores, independientemente de cómo estén distribuidos.
        """
        if not isinstance(
            other,
            SolutionSignature,
        ):
            return False

        return (
            self.players
            == other.players
        )

    # ========================================================
    # Diferencias entre soluciones
    # ========================================================

    def player_team_map(
        self,
    ) -> dict[str, int]:
        """
        Mapa:

            identidad jugador
                ↓
            índice canónico del equipo

        Útil para medir diferencias entre soluciones.
        """
        mapping: dict[
            str,
            int,
        ] = {}

        for team_index, team in enumerate(
            self.teams
        ):
            for player_identity in team:
                mapping[
                    player_identity
                ] = team_index

        return mapping

    def difference_count(
        self,
        other: SolutionSignature,
    ) -> int:
        """
        Devuelve una medida simple del número de jugadores cuya
        agrupación canónica difiere entre ambas soluciones.

        Solo es válida cuando ambas soluciones contienen exactamente
        el mismo pool de jugadores.
        """
        if not isinstance(
            other,
            SolutionSignature,
        ):
            raise TypeError(
                "other must be a SolutionSignature instance."
            )

        if not self.same_player_pool(
            other
        ):
            raise ValueError(
                "Solutions must contain the same player pool."
            )

        first_mapping = (
            self.player_team_map()
        )

        second_mapping = (
            other.player_team_map()
        )

        return sum(
            1
            for player
            in self.players
            if (
                first_mapping[player]
                != second_mapping[player]
            )
        )

    # ========================================================
    # Serialización
    # ========================================================

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "hash": (
                self.stable_hash
            ),

            "team_count": (
                self.team_count
            ),

            "player_count": (
                self.player_count
            ),

            "team_sizes": list(
                self.team_sizes
            ),

            "teams": [
                list(
                    team
                )
                for team in self.teams
            ],

            "compact": (
                self.compact
            ),
        }

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
                "teams must be an iterable of Team instances."
            ) from error

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

            if not isinstance(
                team,
                Team,
            ):
                raise TypeError(
                    f"Team {index} must be a Team instance."
                )

        return team_list

    @staticmethod
    def _team_players(
        team: Team,
    ) -> tuple[Player, ...]:
        players = getattr(
            team,
            "players",
            None,
        )

        if players is None:
            raise ValueError(
                "Team does not provide players."
            )

        try:
            player_list = tuple(
                players
            )

        except TypeError as error:
            raise TypeError(
                "team.players must be iterable."
            ) from error

        for index, player in enumerate(
            player_list,
            start=1,
        ):
            if player is None:
                raise ValueError(
                    f"Team contains None at position {index}."
                )

            if not isinstance(
                player,
                Player,
            ):
                raise TypeError(
                    "All team members must be Player instances."
                )

        return player_list

    @staticmethod
    def _validate_unique_identities(
        identities: Iterable[str],
    ) -> None:
        values = list(
            identities
        )

        seen: set[str] = set()

        duplicates: set[str] = set()

        for identity in values:
            if identity in seen:
                duplicates.add(
                    identity
                )

            seen.add(
                identity
            )

        if duplicates:
            raise ValueError(
                "The solution contains duplicated player identities: "
                + ", ".join(
                    sorted(
                        duplicates
                    )
                )
            )

    # ========================================================
    # Normalización
    # ========================================================

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = (
            str(value)
            .strip()
            .casefold()
        )

        if not normalized:
            return None

        return normalized

    @staticmethod
    def _stable_value(
        value: Any,
    ) -> str:
        """
        Convierte valores simples a una representación estable.
        """
        if value is None:
            return "none"

        if isinstance(
            value,
            bool,
        ):
            return (
                "true"
                if value
                else "false"
            )

        if isinstance(
            value,
            float,
        ):
            return (
                f"{value:.12g}"
            )

        return (
            str(value)
            .strip()
            .casefold()
        )

    # ========================================================
    # Métodos especiales
    # ========================================================

    def __str__(
        self,
    ) -> str:
        return self.compact

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"hash={self.stable_hash!r}, "
            f"teams={self.team_count}, "
            f"players={self.player_count})"
        )
