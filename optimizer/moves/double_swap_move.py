from __future__ import annotations

from collections.abc import Sequence

from models.team import Team
from optimizer.moves.move import Move
from optimizer.moves.swap_move import SwapMove


class DoubleSwapMove(Move):
    """
    Ejecuta dos intercambios independientes entre cuatro equipos distintos.

    Ejemplo:

        Equipo A: player_a1  ↔  Equipo B: player_b1
        Equipo C: player_c1  ↔  Equipo D: player_d1

    El movimiento es atómico:

        - si el segundo swap falla, se revierte el primero;
        - undo() restaura ambos swaps en orden inverso;
        - cada SwapMove conserva sus índices originales;
        - las estadísticas se invalidan mediante SwapMove.

    Se exige que los cuatro equipos sean diferentes para evitar
    interacciones entre ambos intercambios y simplificar las garantías
    de apply()/undo().
    """

    def __init__(
        self,
        team_a: Team,
        player_a,
        team_b: Team,
        player_b,
        team_c: Team,
        player_c,
        team_d: Team,
        player_d,
    ) -> None:

        teams = (
            team_a,
            team_b,
            team_c,
            team_d,
        )

        if any(team is None for team in teams):
            raise ValueError(
                "DoubleSwapMove teams cannot be None."
            )

        if len({id(team) for team in teams}) != 4:
            raise ValueError(
                "DoubleSwapMove requires four different teams."
            )

        players = (
            player_a,
            player_b,
            player_c,
            player_d,
        )

        if any(player is None for player in players):
            raise ValueError(
                "DoubleSwapMove players cannot be None."
            )

        if len({id(player) for player in players}) != 4:
            raise ValueError(
                "DoubleSwapMove requires four different "
                "player instances."
            )

        self.team_a = team_a
        self.team_b = team_b
        self.team_c = team_c
        self.team_d = team_d

        self.player_a = player_a
        self.player_b = player_b
        self.player_c = player_c
        self.player_d = player_d

        self._first_swap = SwapMove(
            team_a,
            player_a,
            team_b,
            player_b,
        )

        self._second_swap = SwapMove(
            team_c,
            player_c,
            team_d,
            player_d,
        )

        self._applied = False

    def apply(
        self,
        teams: Sequence[Team] | None = None,
    ) -> None:
        """
        Aplica ambos swaps de forma atómica.

        Si el segundo intercambio falla, el primero se revierte
        inmediatamente.
        """

        if self._applied:
            raise RuntimeError(
                "DoubleSwapMove has already been applied."
            )

        first_applied = False

        try:
            self._first_swap.apply(teams)
            first_applied = True

            self._second_swap.apply(teams)

        except Exception:
            if first_applied:
                try:
                    self._first_swap.undo(teams)
                except Exception as rollback_error:
                    raise RuntimeError(
                        "DoubleSwapMove failed and rollback "
                        "of the first swap also failed."
                    ) from rollback_error

            raise

        self._applied = True

    def undo(
        self,
        teams: Sequence[Team] | None = None,
    ) -> None:
        """
        Deshace ambos intercambios en orden inverso.

        Primero se deshace el segundo swap y después el primero.
        """

        if not self._applied:
            raise RuntimeError(
                "DoubleSwapMove has not been applied."
            )

        second_undone = False

        try:
            self._second_swap.undo(teams)
            second_undone = True

            self._first_swap.undo(teams)

        except Exception:
            # Si conseguimos deshacer el segundo swap pero falla
            # el primero, intentamos devolver el segundo a su estado
            # aplicado para conservar coherencia.
            if second_undone:
                try:
                    self._second_swap.apply(teams)
                except Exception as rollback_error:
                    raise RuntimeError(
                        "DoubleSwapMove undo failed and rollback "
                        "of the second swap also failed."
                    ) from rollback_error

            raise

        self._applied = False

    @property
    def is_applied(self) -> bool:
        return self._applied

    @property
    def first_swap(self) -> SwapMove:
        return self._first_swap

    @property
    def second_swap(self) -> SwapMove:
        return self._second_swap

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"{self.player_a!r} ↔ {self.player_b!r}, "
            f"{self.player_c!r} ↔ {self.player_d!r}, "
            f"applied={self._applied})"
        )
