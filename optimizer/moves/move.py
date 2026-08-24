from abc import ABC, abstractmethod


class Move(ABC):

    @abstractmethod

    def apply(self, teams):
        ...

    @abstractmethod

    def undo(self, teams):
        ...
