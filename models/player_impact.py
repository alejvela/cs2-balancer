"""Explainable immutable results for LAN Player Impact Rating v1."""

from __future__ import annotations

import math
from dataclasses import dataclass

LAN_IMPACT_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class ImpactEvidence:
    metric: str
    value: float | int


@dataclass(frozen=True, slots=True)
class ImpactComponentResult:
    component_id: str
    label: str
    score: float
    weight: float
    weighted_contribution: float
    evidence: tuple[ImpactEvidence, ...]

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 100.0 or not math.isfinite(self.score):
            raise ValueError("component score must be finite and between 0 and 100")
        if not 0.0 <= self.weight <= 1.0 or not math.isfinite(self.weight):
            raise ValueError("component weight must be finite and between 0 and 1")
        expected = self.score * self.weight
        if not math.isclose(self.weighted_contribution, expected, abs_tol=1e-12):
            raise ValueError("weighted contribution must equal score * weight")


@dataclass(frozen=True, slots=True)
class PlayerImpactResult:
    player_id: str
    display_name: str
    model_version: str
    score: float
    components: tuple[ImpactComponentResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", tuple(self.components))
        if not 0.0 <= self.score <= 100.0 or not math.isfinite(self.score):
            raise ValueError("impact score must be finite and between 0 and 100")
        if not math.isclose(
            self.score,
            sum(item.weighted_contribution for item in self.components),
            abs_tol=1e-12,
        ):
            raise ValueError("impact score must equal the component contributions")


@dataclass(frozen=True, slots=True)
class TournamentImpactEligibility:
    eligible: bool
    maps_played: int
    required_maps: int
    reason: str
