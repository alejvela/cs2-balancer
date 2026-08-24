from abc import ABC, abstractmethod
from random import random

from optimizer.optimizers.swap import Swap


class MoveSource(ABC):

    @property
    @abstractmethod

    def name(self) -> str:
        ...

    @abstractmethod

    def iterate(self, teams):
        """
        Devuelve un generador de movimientos.
        """
        ...

    @abstractmethod

    def estimate_size(self, teams):

        total = 0

        for ta in range(len(teams)):

            for tb in range(ta + 1, len(teams)):

                total += (

                    len(teams[ta].players)

                    *

                    len(teams[tb].players)

                )

        return total

    @abstractmethod

    def sample(self, teams, amount):

        generated = set()

        while len(generated) < amount:

            ta = random.randrange(len(teams))
            tb = random.randrange(len(teams))

            if ta == tb:
                continue

            pa = random.choice(
                teams[ta].players
            )

            pb = random.choice(
                teams[tb].players
            )

            move = Swap(
                ta,
                tb,
                pa,
                pb
            )

            if move not in generated:
                generated.add(move)
                yield move
