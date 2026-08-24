from __future__ import annotations

from collections.abc import Iterable, Iterator

from optimizer.optimization_phase import OptimizationPhase


class OptimizationPipeline:
    """
    Colección ordenada de fases de optimización.

    El pipeline no ejecuta la optimización por sí mismo.
    Su responsabilidad es almacenar, ordenar y exponer las fases
    que utilizará LocalOptimizer.
    """

    def __init__(
        self,
        phases: Iterable[OptimizationPhase] | None = None,
    ) -> None:
        self._phases: list[OptimizationPhase] = []

        if phases is not None:
            for phase in phases:
                self.add(phase)

    def add(
        self,
        phase: OptimizationPhase,
    ) -> OptimizationPipeline:
        """
        Añade una fase al final del pipeline.

        Devuelve la propia instancia para permitir encadenamiento.
        """
        if phase is None:
            raise ValueError(
                "phase cannot be None."
            )

        if not isinstance(phase, OptimizationPhase):
            raise TypeError(
                "phase must be an OptimizationPhase instance."
            )

        if self.contains(phase.name):
            raise ValueError(
                f"A phase named '{phase.name}' already exists."
            )

        self._phases.append(phase)

        return self

    def insert(
        self,
        index: int,
        phase: OptimizationPhase,
    ) -> OptimizationPipeline:
        """
        Inserta una fase en una posición concreta.
        """
        if phase is None:
            raise ValueError(
                "phase cannot be None."
            )

        if not isinstance(phase, OptimizationPhase):
            raise TypeError(
                "phase must be an OptimizationPhase instance."
            )

        if self.contains(phase.name):
            raise ValueError(
                f"A phase named '{phase.name}' already exists."
            )

        if index < 0 or index > len(self._phases):
            raise IndexError(
                "index is outside the valid pipeline range."
            )

        self._phases.insert(index, phase)

        return self

    def remove(
        self,
        phase_name: str,
    ) -> OptimizationPhase:
        """
        Elimina una fase por nombre y devuelve la fase eliminada.
        """
        index = self._find_index(phase_name)

        if index is None:
            raise KeyError(
                f"Phase '{phase_name}' was not found."
            )

        return self._phases.pop(index)

    def get(
        self,
        phase_name: str,
    ) -> OptimizationPhase | None:
        """
        Devuelve una fase por nombre.

        Si no existe, devuelve None.
        """
        index = self._find_index(phase_name)

        if index is None:
            return None

        return self._phases[index]

    def contains(
        self,
        phase_name: str,
    ) -> bool:
        """
        Indica si existe una fase con el nombre recibido.
        """
        return self._find_index(phase_name) is not None

    def enable(
        self,
        phase_name: str,
    ) -> None:
        """
        Habilita una fase.
        """
        phase = self._require_phase(phase_name)
        phase.enabled = True

    def disable(
        self,
        phase_name: str,
    ) -> None:
        """
        Deshabilita una fase.
        """
        phase = self._require_phase(phase_name)
        phase.enabled = False

    def move(
        self,
        phase_name: str,
        new_index: int,
    ) -> None:
        """
        Cambia la posición de una fase dentro del pipeline.
        """
        if new_index < 0 or new_index >= len(self._phases):
            raise IndexError(
                "new_index is outside the valid pipeline range."
            )

        phase = self.remove(phase_name)
        self._phases.insert(new_index, phase)

    def clear(self) -> None:
        """
        Elimina todas las fases.
        """
        self._phases.clear()

    def reset(self) -> None:
        """
        Reinicia el estado interno de todas las fases.

        Esto reinicia, por ejemplo, la temperatura de las estrategias
        de recocido simulado.
        """
        for phase in self._phases:
            phase.reset()

    @property
    def phases(self) -> tuple[OptimizationPhase, ...]:
        """
        Devuelve una vista inmutable de las fases.
        """
        return tuple(self._phases)

    @property
    def enabled_phases(self) -> tuple[OptimizationPhase, ...]:
        """
        Devuelve únicamente las fases habilitadas.
        """
        return tuple(
            phase
            for phase in self._phases
            if phase.enabled
        )

    @property
    def is_empty(self) -> bool:
        return len(self._phases) == 0

    def as_dict(self) -> dict:
        """
        Devuelve una representación serializable del pipeline.
        """
        return {
            "phase_count": len(self._phases),
            "enabled_phase_count": len(self.enabled_phases),
            "phases": [
                phase.as_dict()
                for phase in self._phases
            ],
        }

    def _find_index(
        self,
        phase_name: str,
    ) -> int | None:
        """
        Busca una fase ignorando mayúsculas y espacios laterales.
        """
        if not phase_name or not phase_name.strip():
            raise ValueError(
                "phase_name cannot be empty."
            )

        normalized_name = phase_name.strip().casefold()

        for index, phase in enumerate(self._phases):
            if phase.name.casefold() == normalized_name:
                return index

        return None

    def _require_phase(
        self,
        phase_name: str,
    ) -> OptimizationPhase:
        phase = self.get(phase_name)

        if phase is None:
            raise KeyError(
                f"Phase '{phase_name}' was not found."
            )

        return phase

    def __iter__(self) -> Iterator[OptimizationPhase]:
        """
        Recorre las fases en su orden de ejecución.
        """
        return iter(self._phases)

    def __len__(self) -> int:
        return len(self._phases)

    def __getitem__(
        self,
        index: int,
    ) -> OptimizationPhase:
        return self._phases[index]

    def __contains__(
        self,
        phase_name: object,
    ) -> bool:
        if not isinstance(phase_name, str):
            return False

        return self.contains(phase_name)

    def __repr__(self) -> str:
        phase_names = ", ".join(
            phase.name
            for phase in self._phases
        )

        return (
            f"{self.__class__.__name__}("
            f"phases=[{phase_names}])"
        )
