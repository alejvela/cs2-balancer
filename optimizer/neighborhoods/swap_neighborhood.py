from itertools import combinations

from optimizer.moves.swap_move import SwapMove
from optimizer.neighborhoods.neighborhood import Neighborhood


class SwapNeighborhood(Neighborhood):
    """
    Genera todos los intercambios posibles entre parejas de equipos.
    """

    def iterate(self, teams):

        for team_a, team_b in combinations(teams, 2):

            for player_a in team_a.players:

                for player_b in team_b.players:

                    yield SwapMove(
                        team_a,
                        player_a,
                        team_b,
                        player_b
                    )

    def sample(self, teams, k: int):

        count = 0

        for move in self.iterate(teams):

            if count >= k:
                break

            yield move

            count += 1
