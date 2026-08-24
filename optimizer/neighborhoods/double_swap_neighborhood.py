from __future__ import annotations

from itertools import combinations

from optimizer.moves.double_swap_move import (
    DoubleSwapMove,
)
from optimizer.neighborhoods.neighborhood import (
    Neighborhood,
)


class DoubleSwapNeighborhood(Neighborhood):
    """
    Genera todos los double swaps independientes posibles.

    Cada movimiento utiliza cuatro equipos diferentes:

        A ↔ B
        C ↔ D

    Las particiones de equipos se generan de forma canónica para
    evitar duplicados equivalentes como:

        A-B + C-D
        C-D + A-B
        B-A + D-C

    Para cuatro equipos existen exactamente tres particiones:

        A-B + C-D
        A-C + B-D
        A-D + B-C
    """

    def iterate(self, teams):

        team_list = list(teams)

        if len(team_list) < 4:
            return

        for selected_teams in combinations(
            team_list,
            4,
        ):
            (
                team_a,
                team_b,
                team_c,
                team_d,
            ) = selected_teams

            pairings = (
                (
                    team_a,
                    team_b,
                    team_c,
                    team_d,
                ),
                (
                    team_a,
                    team_c,
                    team_b,
                    team_d,
                ),
                (
                    team_a,
                    team_d,
                    team_b,
                    team_c,
                ),
            )

            for (
                first_team_a,
                first_team_b,
                second_team_a,
                second_team_b,
            ) in pairings:

                for player_a in first_team_a.players:

                    for player_b in first_team_b.players:

                        for player_c in second_team_a.players:

                            for player_d in second_team_b.players:

                                yield DoubleSwapMove(
                                    first_team_a,
                                    player_a,
                                    first_team_b,
                                    player_b,
                                    second_team_a,
                                    player_c,
                                    second_team_b,
                                    player_d,
                                )

    def sample(
        self,
        teams,
        k: int,
    ):

        if k <= 0:
            return

        count = 0

        for move in self.iterate(teams):

            if count >= k:
                break

            yield move

            count += 1
