from __future__ import annotations

from abc import ABC, abstractmethod


class Neighborhood(ABC):

    def generate(
        self,
        teams,
    ):
        """Unused v0.7 compatibility hook; enumeration uses iterate().

        Deliberately returns None. Concrete neighborhoods implement iterate
        and sample; callers must not use this hook to enumerate moves.
        """
        return None

    @abstractmethod
    def sample(
        self,
        teams,
        k: int,
    ):
        ...
