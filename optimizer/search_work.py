"""One immutable record of strategy work, independent of accepted movements."""

from dataclasses import asdict, dataclass

from models.numeric import finite_real
from optimizer.optimization_iteration import OptimizationIteration


@dataclass(frozen=True, slots=True)
class SearchWork:
    phase: str
    strategy: str
    neighborhood: str
    evaluations: int
    elapsed: float

    def __post_init__(self) -> None:
        for name in ("phase", "strategy", "neighborhood"):
            object.__setattr__(
                self,
                name,
                OptimizationIteration._validate_name(getattr(self, name), name),
            )
        finite_real(self.evaluations, "evaluations")
        if not isinstance(self.evaluations, int):
            raise TypeError("evaluations must be an integer.")
        elapsed = finite_real(self.elapsed, "elapsed")
        if self.evaluations < 0 or elapsed < 0:
            raise ValueError("evaluations and elapsed must be non-negative.")
        object.__setattr__(self, "elapsed", elapsed)

    def as_dict(self) -> dict:
        return asdict(self)
