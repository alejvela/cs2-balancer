"""GLOBAL lookahead controls; hard assignment constraints are unconditional."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GlobalPruningPolicy:
    use_capacity_pruning: bool = True
    use_seed_pruning: bool = True
    use_power_bound: bool = True

    def __post_init__(self) -> None:
        for field in ("use_capacity_pruning", "use_seed_pruning", "use_power_bound"):
            if not isinstance(getattr(self, field), bool):
                raise TypeError(f"{field} must be a boolean.")
