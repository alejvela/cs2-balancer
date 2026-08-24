from __future__ import annotations

from collections.abc import Sequence

from models.team import Team
from optimizer.moves.move import Move


class SwapMove(Move):
    """
    Intercambia un jugador entre dos equipos diferentes.

    El movimiento conserva los índices originales de ambos jugadores
    para que `undo()` restaure exactamente el estado anterior.

    La búsqueda de jugadores se realiza por identidad (`is`) y no por
    igualdad (`==`), evitando seleccionar una instancia incorrecta si
    Player implementa __eq__.
    """

    def __init__(
        self,
        team_a: Team,
        player_a,
        team_b: Team,
        player_b,
    ) -> None:
        if team_a is None:
            raise ValueError(
                "team_a cannot be None."
            )

        if team_b is None:
            raise ValueError(
                "team_b cannot be None."
            )

        if team_a is team_b:
            raise ValueError(
                "SwapMove requires two different teams."
            )

        if player_a is None:
            raise ValueError(
                "player_a cannot be None."
            )

        if player_b is None:
            raise ValueError(
                "player_b cannot be None."
            )

        if player_a is player_b:
            raise ValueError(
                "SwapMove requires two different player instances. "
                f"Received {self._describe_player(player_a)} twice."
            )

        self.team_a = team_a
        self.team_b = team_b

        self.player_a = player_a
        self.player_b = player_b

        self._index_a: int | None = None
        self._index_b: int | None = None

        self._applied = False

    def apply(
        self,
        teams: Sequence[Team] | None = None,
    ) -> None:
        """
        Aplica el intercambio.

        `teams` se mantiene en la firma por compatibilidad con Move,
        aunque el movimiento ya conserva las referencias de los equipos.
        """
        if self._applied:
            raise RuntimeError(
                "SwapMove has already been applied."
            )

        index_a = self._find_player_index(
            team=self.team_a,
            player=self.player_a,
        )

        index_b = self._find_player_index(
            team=self.team_b,
            player=self.player_b,
        )

        self._validate_destination_absence()

        self._index_a = index_a
        self._index_b = index_b

        try:
            self.team_a.players[index_a] = self.player_b
            self.team_b.players[index_b] = self.player_a

            self._invalidate_statistics()

            self._applied = True

        except Exception:
            # Restauración atómica si falla la segunda asignación
            # o la invalidación de estadísticas.
            self.team_a.players[index_a] = self.player_a
            self.team_b.players[index_b] = self.player_b

            self._index_a = None
            self._index_b = None
            self._applied = False

            self._invalidate_statistics_safely()

            raise

    def undo(
        self,
        teams: Sequence[Team] | None = None,
    ) -> None:
        """
        Restaura exactamente las posiciones originales.

        No vuelve a buscar los jugadores mediante list.index(), porque
        las listas ya han sido modificadas y la igualdad de Player podría
        localizar una instancia incorrecta.
        """
        if not self._applied:
            raise RuntimeError(
                "SwapMove has not been applied."
            )

        if self._index_a is None or self._index_b is None:
            raise RuntimeError(
                "SwapMove does not contain its original positions."
            )

        self._validate_applied_state()

        index_a = self._index_a
        index_b = self._index_b

        try:
            self.team_a.players[index_a] = self.player_a
            self.team_b.players[index_b] = self.player_b

            self._invalidate_statistics()

        except Exception:
            # Si la restauración falla, intentamos devolver el movimiento
            # al estado aplicado para no dejar una mezcla parcial.
            self.team_a.players[index_a] = self.player_b
            self.team_b.players[index_b] = self.player_a

            self._invalidate_statistics_safely()

            raise

        self._index_a = None
        self._index_b = None
        self._applied = False

    def _validate_destination_absence(
        self,
    ) -> None:
        """
        Evita introducir una instancia que ya se encuentre en el equipo
        de destino.

        En una distribución válida, player_b no debe existir previamente
        en team_a y player_a no debe existir previamente en team_b.
        """
        if self._contains_identity(
            self.team_a.players,
            self.player_b,
        ):
            raise ValueError(
                f"{self._describe_player(self.player_b)} already exists "
                f"in {self._describe_team(self.team_a)}."
            )

        if self._contains_identity(
            self.team_b.players,
            self.player_a,
        ):
            raise ValueError(
                f"{self._describe_player(self.player_a)} already exists "
                f"in {self._describe_team(self.team_b)}."
            )

    def _validate_applied_state(
        self,
    ) -> None:
        """
        Comprueba que las posiciones guardadas siguen conteniendo los
        jugadores esperados antes de ejecutar undo().
        """
        assert self._index_a is not None
        assert self._index_b is not None

        if self._index_a >= len(self.team_a.players):
            raise RuntimeError(
                "The size of team_a changed while SwapMove was applied."
            )

        if self._index_b >= len(self.team_b.players):
            raise RuntimeError(
                "The size of team_b changed while SwapMove was applied."
            )

        current_a = self.team_a.players[self._index_a]
        current_b = self.team_b.players[self._index_b]

        if current_a is not self.player_b:
            raise RuntimeError(
                "Cannot undo SwapMove because team_a no longer contains "
                "player_b at the expected position. "
                f"Expected {self._describe_player(self.player_b)}, "
                f"found {self._describe_player(current_a)}."
            )

        if current_b is not self.player_a:
            raise RuntimeError(
                "Cannot undo SwapMove because team_b no longer contains "
                "player_a at the expected position. "
                f"Expected {self._describe_player(self.player_a)}, "
                f"found {self._describe_player(current_b)}."
            )

    @staticmethod
    def _find_player_index(
        team: Team,
        player,
    ) -> int:
        """
        Busca la posición de una instancia concreta mediante `is`.
        """
        players = getattr(
            team,
            "players",
            None,
        )

        if players is None:
            raise AttributeError(
                f"{SwapMove._describe_team(team)} does not expose players."
            )

        matching_indices = [
            index
            for index, current_player in enumerate(players)
            if current_player is player
        ]

        if not matching_indices:
            raise ValueError(
                f"{SwapMove._describe_player(player)} is not present "
                f"in {SwapMove._describe_team(team)}."
            )

        if len(matching_indices) > 1:
            raise ValueError(
                f"{SwapMove._describe_player(player)} appears multiple "
                f"times in {SwapMove._describe_team(team)} at positions "
                f"{matching_indices}."
            )

        return matching_indices[0]

    @staticmethod
    def _contains_identity(
        players,
        target,
    ) -> bool:
        """
        Comprueba pertenencia por identidad, evitando `target in players`.
        """
        return any(
            player is target
            for player in players
        )

    def _invalidate_statistics(
        self,
    ) -> None:
        """
        Invalida las estadísticas de ambos equipos.
        """
        self._invalidate_team_statistics(
            self.team_a
        )

        self._invalidate_team_statistics(
            self.team_b
        )

    def _invalidate_statistics_safely(
        self,
    ) -> None:
        """
        Intenta invalidar las estadísticas sin ocultar la excepción
        original de apply() o undo().
        """
        for team in (
            self.team_a,
            self.team_b,
        ):
            try:
                self._invalidate_team_statistics(
                    team
                )
            except Exception:
                pass

    @staticmethod
    def _invalidate_team_statistics(
        team: Team,
    ) -> None:
        statistics = getattr(
            team,
            "statistics",
            None,
        )

        if statistics is None:
            return

        invalidate = getattr(
            statistics,
            "invalidate",
            None,
        )

        if callable(invalidate):
            invalidate()

    @property
    def is_applied(self) -> bool:
        """
        Indica si el movimiento está actualmente aplicado.
        """
        return self._applied

    @staticmethod
    def _describe_player(
        player,
    ) -> str:
        if player is None:
            return "None"

        nickname = getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                "Unknown",
            ),
        )

        steam_id = getattr(
            player,
            "steam_id",
            None,
        )

        return (
            f"Player("
            f"nickname={nickname!r}, "
            f"steam_id={steam_id!r}, "
            f"object_id={id(player)})"
        )

    @staticmethod
    def _describe_team(
        team: Team,
    ) -> str:
        name = getattr(
            team,
            "name",
            None,
        )

        team_id = getattr(
            team,
            "id",
            None,
        )

        if name:
            return (
                f"Team("
                f"name={name!r}, "
                f"id={team_id!r})"
            )

        return f"Team(id={team_id!r})"

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"{self._describe_player(self.player_a)} "
            f"from {self._describe_team(self.team_a)} "
            f"↔ "
            f"{self._describe_player(self.player_b)} "
            f"from {self._describe_team(self.team_b)}, "
            f"applied={self._applied})"
        )
