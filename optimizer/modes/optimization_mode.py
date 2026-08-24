from __future__ import annotations

from enum import Enum


class OptimizationMode(str, Enum):
    """
    Modo utilizado para optimizar automáticamente los equipos.

    FAST
        Optimización local rápida.

    STABLE
        Optimización estable mediante múltiples restarts
        deterministas.

    GLOBAL
        STABLE como warm start seguido de búsqueda global
        Branch & Bound.
    """

    FAST = "fast"
    STABLE = "stable"
    GLOBAL = "global"

    @classmethod
    def from_value(
        cls,
        value: str | OptimizationMode,
    ) -> OptimizationMode:
        if isinstance(value, cls):
            return value

        if not isinstance(value, str):
            raise TypeError(
                "Optimization mode must be a string "
                "or OptimizationMode."
            )

        normalized = value.strip().casefold()

        aliases = {
            "fast": cls.FAST,
            "stable": cls.STABLE,
            "global": cls.GLOBAL,
        }

        mode = aliases.get(normalized)

        if mode is not None:
            return mode

        expected = ", ".join(
            member.value
            for member in cls
        )

        raise ValueError(
            f"Unknown optimization mode {value!r}. "
            f"Expected one of: {expected}."
        )

    def require_available(self) -> None:
        """
        Valida que el modo esté soportado.

        Las dependencias concretas se validan en LanBalancer.
        """

        if self in {
            OptimizationMode.FAST,
            OptimizationMode.STABLE,
            OptimizationMode.GLOBAL,
        }:
            return

        raise RuntimeError(
            f"Optimization mode {self!r} is not available."
        )

    @property
    def deterministic(self) -> bool:
        """
        Indica si el modo pretende producir resultados reproducibles
        para la misma entrada y configuración.
        """

        return self in {
            OptimizationMode.STABLE,
            OptimizationMode.GLOBAL,
        }

    @property
    def uses_stable_optimizer(self) -> bool:
        return self in {
            OptimizationMode.STABLE,
            OptimizationMode.GLOBAL,
        }

    @property
    def uses_global_optimizer(self) -> bool:
        return self is OptimizationMode.GLOBAL

    @property
    def is_fast(self) -> bool:
        return self is OptimizationMode.FAST

    @property
    def is_stable(self) -> bool:
        return self is OptimizationMode.STABLE

    @property
    def is_global(self) -> bool:
        return self is OptimizationMode.GLOBAL

    @property
    def label(self) -> str:
        labels = {
            OptimizationMode.FAST: "Optimización rápida",
            OptimizationMode.STABLE: "Optimización estable",
            OptimizationMode.GLOBAL: "Optimización global",
        }
        return labels[self]

    @property
    def description(self) -> str:
        descriptions = {
            OptimizationMode.FAST: (
                "Optimización local rápida mediante una única "
                "búsqueda desde la distribución inicial."
            ),
            OptimizationMode.STABLE: (
                "Optimización mediante múltiples reinicios "
                "deterministas y selección de la mejor solución."
            ),
            OptimizationMode.GLOBAL: (
                "Optimización global mediante STABLE como warm start "
                "y Branch & Bound para buscar la mejor composición."
            ),
        }
        return descriptions[self]

    def __str__(self) -> str:
        return self.value
