from __future__ import annotations

from abc import ABC, abstractmethod


class Neighborhood(ABC):

    @abstractmethod
    def generate(
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
