from __future__ import annotations

from abc import ABC, abstractmethod


class Neighborhood(ABC):

    def generate(  # noqa: B027
        self,
        teams,
    ):
        ...

    @abstractmethod
    def sample(
        self,
        teams,
        k: int,
    ):
        ...
