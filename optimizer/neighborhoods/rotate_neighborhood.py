from __future__ import annotations

from itertools import combinations

from optimizer.moves.rotate_move import (
    RotateMove,
)
from optimizer.neighborhoods.neighborhood import (
    Neighborhood,
)


class RotateNeighborhood(Neighborhood):
    """
    Genera todas las rotaciones posibles de un jugador entre
    tres equipos distintos.

    Para cada combinación de equipos:

        A
        B
        C

    se generan las dos direcciones posibles.

    Dirección 1:

        A → B
        B → C
        C → A

    Dirección 2:

        A → C
        C → B
        B → A

    Para cuatro equipos de cinco jugadores:

        C(4, 3) = 4 combinaciones de equipos

        5 × 5 × 5 = 125 selecciones de jugadores

        2 direcciones

        4 × 125 × 2 = 1000 movimientos
    """

    def iterate(
        self,
        teams,
    ):
        team_list = list(
            teams
        )

        if len(team_list) < 3:
            return

        # ====================================================
        # Combinaciones únicas de tres equipos
        # ====================================================

        for (
            team_a,
            team_b,
            team_c,
        ) in combinations(
            team_list,
            3,
        ):

            # =================================================
            # Dirección 1
            #
            # player_a:
            #     A → B
            #
            # player_b:
            #     B → C
            #
            # player_c:
            #     C → A
            # =================================================

            for player_a in team_a.players:

                for player_b in team_b.players:

                    for player_c in team_c.players:

                        yield RotateMove(
                            team_a=team_a,
                            player_a=player_a,

                            team_b=team_b,
                            player_b=player_b,

                            team_c=team_c,
                            player_c=player_c,
                        )

            # =================================================
            # Dirección 2
            #
            # Queremos:
            #
            #     A → C
            #     C → B
            #     B → A
            #
            # RotateMove siempre interpreta:
            #
            #     team_a → team_b
            #     team_b → team_c
            #     team_c → team_a
            #
            # Por eso pasamos:
            #
            #     team_a = A
            #     team_b = C
            #     team_c = B
            # =================================================

            for player_a in team_a.players:

                for player_c in team_c.players:

                    for player_b in team_b.players:

                        yield RotateMove(
                            team_a=team_a,
                            player_a=player_a,

                            team_b=team_c,
                            player_b=player_c,

                            team_c=team_b,
                            player_c=player_b,
                        )

    def sample(
        self,
        teams,
        k: int,
    ):
        """
        Devuelve como máximo los primeros k movimientos.

        Mantiene el mismo contrato que SwapNeighborhood.
        """

        if isinstance(
            k,
            bool,
        ):
            raise TypeError(
                "k must be an integer."
            )

        if not isinstance(
            k,
            int,
        ):
            raise TypeError(
                "k must be an integer."
            )

        if k <= 0:
            return

        count = 0

        for move in self.iterate(
            teams
        ):
            if count >= k:
                break

            yield move

            count += 1

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}()"
        )
