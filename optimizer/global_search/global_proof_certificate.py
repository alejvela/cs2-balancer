"""Evidence for a completed GLOBAL search, independent of stop labels."""

from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True, slots=True)
class GlobalProofCertificate:
    search_exhausted: bool
    root_complete: bool
    symmetry_safe: bool
    score_pruning_safe: bool
    feasibility_pruning_safe: bool
    ranking_exact: bool
    incumbent_in_domain: bool
    final_score_exact: bool
    bound_strategy: str
    root_expanded: bool = False
    traversal_verified: bool = True

    def __post_init__(self) -> None:
        for item in fields(self):
            if (
                item.name != "bound_strategy"
                and type(getattr(self, item.name)) is not bool
            ):
                raise TypeError(f"{item.name} must be a boolean.")

    @property
    def optimality_proven(self) -> bool:
        return all(
            (
                self.search_exhausted,
                self.root_complete,
                self.symmetry_safe,
                self.score_pruning_safe,
                self.feasibility_pruning_safe,
                self.ranking_exact,
                self.incumbent_in_domain,
                self.final_score_exact,
                self.traversal_verified,
            )
        )

    def as_dict(self) -> dict:
        return asdict(self)
