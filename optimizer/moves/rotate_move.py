from __future__ import annotations

from collections.abc import Sequence

from models.team import Team
from optimizer.moves.move import Move


class RotateMove(Move):
    """
    Realiza una rotación de tres jugadores entre tres equipos.

    Dirección:

        team_a.player_a
            ↓
        team_b

        team_b.player_b
            ↓
        team_c

        team_c.player_c
            ↓
        team_a

    Es decir:

        A:a
        B:b
        C:c

    se convierte en:

        A:c
        B:a
        C:b

    El movimiento:

        - conserva el tamaño de los equipos;
        - conserva exactamente las instancias Player;
        - almacena los índices originales;
        - puede deshacerse exactamente;
        - trabaja por identidad (`is`);
        - invalida las estadísticas de los tres equipos;
        - intenta mantener atomicidad en caso de error.
    """

    def __init__(
        self,
        team_a: Team,
        player_a,
        team_b: Team,
        player_b,
        team_c: Team,
        player_c,
    ) -> None:
        # ====================================================
        # Validación de equipos
        # ====================================================

        if team_a is None:
            raise ValueError(
                "team_a cannot be None."
            )

        if team_b is None:
            raise ValueError(
                "team_b cannot be None."
            )

        if team_c is None:
            raise ValueError(
                "team_c cannot be None."
            )

        if len(
            {
                id(team_a),
                id(team_b),
                id(team_c),
            }
        ) != 3:
            raise ValueError(
                "RotateMove requires three different teams."
            )

        # ====================================================
        # Validación de jugadores
        # ====================================================

        if player_a is None:
            raise ValueError(
                "player_a cannot be None."
            )

        if player_b is None:
            raise ValueError(
                "player_b cannot be None."
            )

        if player_c is None:
            raise ValueError(
                "player_c cannot be None."
            )

        if len(
            {
                id(player_a),
                id(player_b),
                id(player_c),
            }
        ) != 3:
            raise ValueError(
                "RotateMove requires three different "
                "player instances."
            )

        self.team_a = team_a
        self.team_b = team_b
        self.team_c = team_c

        self.player_a = player_a
        self.player_b = player_b
        self.player_c = player_c

        self._index_a: int | None = None
        self._index_b: int | None = None
        self._index_c: int | None = None

        self._applied = False

    # ========================================================
    # Apply
    # ========================================================

    def apply(
        self,
        teams: Sequence[Team] | None = None,
    ) -> None:
        """
        Aplica la rotación:

            A <- C
            B <- A
            C <- B
        """

        if self._applied:
            raise RuntimeError(
                "RotateMove has already been applied."
            )

        index_a = self._find_player_index(
            team=self.team_a,
            player=self.player_a,
        )

        index_b = self._find_player_index(
            team=self.team_b,
            player=self.player_b,
        )

        index_c = self._find_player_index(
            team=self.team_c,
            player=self.player_c,
        )

        self._validate_destination_absence()

        self._index_a = index_a
        self._index_b = index_b
        self._index_c = index_c

        try:
            # -----------------------------------------------
            # A recibe C
            # B recibe A
            # C recibe B
            # -----------------------------------------------

            self.team_a.players[
                index_a
            ] = self.player_c

            self.team_b.players[
                index_b
            ] = self.player_a

            self.team_c.players[
                index_c
            ] = self.player_b

            self._invalidate_statistics()

            self._applied = True

        except Exception:
            # -----------------------------------------------
            # Rollback completo al estado original.
            # -----------------------------------------------

            self.team_a.players[
                index_a
            ] = self.player_a

            self.team_b.players[
                index_b
            ] = self.player_b

            self.team_c.players[
                index_c
            ] = self.player_c

            self._index_a = None
            self._index_b = None
            self._index_c = None

            self._applied = False

            self._invalidate_statistics_safely()

            raise

    # ========================================================
    # Undo
    # ========================================================

    def undo(
        self,
        teams: Sequence[Team] | None = None,
    ) -> None:
        """
        Restaura exactamente:

            A:a
            B:b
            C:c
        """

        if not self._applied:
            raise RuntimeError(
                "RotateMove has not been applied."
            )

        if (
            self._index_a is None
            or self._index_b is None
            or self._index_c is None
        ):
            raise RuntimeError(
                "RotateMove does not contain "
                "its original positions."
            )

        self._validate_applied_state()

        index_a = self._index_a
        index_b = self._index_b
        index_c = self._index_c

        try:
            self.team_a.players[
                index_a
            ] = self.player_a

            self.team_b.players[
                index_b
            ] = self.player_b

            self.team_c.players[
                index_c
            ] = self.player_c

            self._invalidate_statistics()

        except Exception:
            # -----------------------------------------------
            # Si falla undo(), intentamos devolver el
            # movimiento al estado aplicado.
            # -----------------------------------------------

            self.team_a.players[
                index_a
            ] = self.player_c

            self.team_b.players[
                index_b
            ] = self.player_a

            self.team_c.players[
                index_c
            ] = self.player_b

            self._invalidate_statistics_safely()

            raise

        self._index_a = None
        self._index_b = None
        self._index_c = None

        self._applied = False

    # ========================================================
    # Validación del estado
    # ========================================================

    def _validate_destination_absence(
        self,
    ) -> None:
        """
        Comprueba que ningún jugador que va a entrar en un equipo
        exista ya previamente en él.
        """

        if self._contains_identity(
            self.team_a.players,
            self.player_c,
        ):
            raise ValueError(
                "player_c already exists in team_a."
            )

        if self._contains_identity(
            self.team_b.players,
            self.player_a,
        ):
            raise ValueError(
                "player_a already exists in team_b."
            )

        if self._contains_identity(
            self.team_c.players,
            self.player_b,
        ):
            raise ValueError(
                "player_b already exists in team_c."
            )

    def _validate_applied_state(
        self,
    ) -> None:
        """
        Comprueba que las posiciones originales todavía contienen
        los jugadores esperados antes de ejecutar undo().
        """

        assert self._index_a is not None
        assert self._index_b is not None
        assert self._index_c is not None

        if self._index_a >= len(
            self.team_a.players
        ):
            raise RuntimeError(
                "team_a size changed while "
                "RotateMove was applied."
            )

        if self._index_b >= len(
            self.team_b.players
        ):
            raise RuntimeError(
                "team_b size changed while "
                "RotateMove was applied."
            )

        if self._index_c >= len(
            self.team_c.players
        ):
            raise RuntimeError(
                "team_c size changed while "
                "RotateMove was applied."
            )

        current_a = self.team_a.players[
            self._index_a
        ]

        current_b = self.team_b.players[
            self._index_b
        ]

        current_c = self.team_c.players[
            self._index_c
        ]

        # Después de apply:
        #
        # A contiene C
        # B contiene A
        # C contiene B

        if current_a is not self.player_c:
            raise RuntimeError(
                "Cannot undo RotateMove because "
                "team_a no longer contains player_c "
                "at the expected position."
            )

        if current_b is not self.player_a:
            raise RuntimeError(
                "Cannot undo RotateMove because "
                "team_b no longer contains player_a "
                "at the expected position."
            )

        if current_c is not self.player_b:
            raise RuntimeError(
                "Cannot undo RotateMove because "
                "team_c no longer contains player_b "
                "at the expected position."
            )

    # ========================================================
    # Helpers de jugadores
    # ========================================================

    @staticmethod
    def _find_player_index(
        team: Team,
        player,
    ) -> int:
        """
        Busca la posición utilizando identidad de objeto (`is`).
        """

        players = getattr(
            team,
            "players",
            None,
        )

        if players is None:
            raise AttributeError(
                "team does not expose players."
            )

        matching_indices = [
            index
            for index, current_player
            in enumerate(players)
            if current_player is player
        ]

        if not matching_indices:
            raise ValueError(
                "Player is not present "
                "in the expected team."
            )

        if len(
            matching_indices
        ) > 1:
            raise ValueError(
                "Player appears multiple times "
                "in the same team."
            )

        return matching_indices[0]

    @staticmethod
    def _contains_identity(
        players,
        target,
    ) -> bool:
        return any(
            player is target
            for player in players
        )

    # ========================================================
    # Estadísticas
    # ========================================================

    def _invalidate_statistics(
        self,
    ) -> None:
        for team in (
            self.team_a,
            self.team_b,
            self.team_c,
        ):
            self._invalidate_team_statistics(
                team
            )

    def _invalidate_statistics_safely(
        self,
    ) -> None:
        for team in (
            self.team_a,
            self.team_b,
            self.team_c,
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

        if callable(
            invalidate
        ):
            invalidate()

    # ========================================================
    # Estado
    # ========================================================

    @property
    def is_applied(
        self,
    ) -> bool:
        return self._applied

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"{self.player_a!r} → "
            f"{getattr(self.team_b, 'name', 'B')}, "
            f"{self.player_b!r} → "
            f"{getattr(self.team_c, 'name', 'C')}, "
            f"{self.player_c!r} → "
            f"{getattr(self.team_a, 'name', 'A')}, "
            f"applied={self._applied})"
        )
