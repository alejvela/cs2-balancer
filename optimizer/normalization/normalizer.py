from abc import ABC, abstractmethod


class Normalizer(ABC):

    @abstractmethod
    def normalize(self, value: float) -> float:
        """
        Convierte cualquier valor en una puntuación entre 0 y 100.
        """
        ...

    def clamp(self, value: float) -> float:

        return max(0.0, min(100.0, value))
