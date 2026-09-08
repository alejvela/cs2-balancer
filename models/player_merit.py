"""Immutable, presentation-independent statistical merit definitions and results."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class MeritCategory(StrEnum):
    COMBAT = "combat"
    OPENING = "opening"
    CLUTCH = "clutch"
    MULTIKILL = "multikill"
    SUPPORT = "support"
    UTILITY = "utility"
    PRECISION = "precision"
    SURVIVAL = "survival"
    ECONOMY = "economy"


class MetricDirection(StrEnum):
    MAXIMUM = "maximum"
    MINIMUM = "minimum"


ACTIVE_MERIT_IDS = (
    "el_verdugo",
    "la_apisonadora",
    "el_abrelatas",
    "sin_miedo_al_exito",
    "rey_del_clutch",
    "el_coleccionista",
    "pikachu",
    "el_escudero",
    "el_alquimista",
    "el_cirujano",
    "el_francotirador_sin_mira",
    "el_superviviente",
    "tio_gilito",
)


@dataclass(frozen=True, slots=True)
class MeritTieBreaker:
    """Sum of raw fields, optionally divided by another sum; undefined ranks last."""

    fields: tuple[str, ...]
    denominator_fields: tuple[str, ...] = ()
    direction: MetricDirection = MetricDirection.MAXIMUM

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", tuple(self.fields))
        object.__setattr__(self, "denominator_fields", tuple(self.denominator_fields))
        if not self.fields or any(
            not field.strip() for field in self.fields + self.denominator_fields
        ):
            raise ValueError("tie-break fields must be non-empty")
        if not isinstance(self.direction, MetricDirection):
            raise ValueError("invalid tie-break direction")


@dataclass(frozen=True, slots=True)
class MeritRule:
    stable_id: str
    title: str
    category: MeritCategory
    description: str
    evidence_label: str
    terms: tuple[tuple[str, float], ...]
    denominator: str | None = None
    requires_participation: bool = False
    direction: MetricDirection = MetricDirection.MAXIMUM
    tie_breakers: tuple[MeritTieBreaker, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "terms", tuple(tuple(term) for term in self.terms))
        object.__setattr__(self, "tie_breakers", tuple(self.tie_breakers))
        if not self.stable_id.strip() or not self.title.strip():
            raise ValueError("rule id and title must be non-empty")
        if not self.terms or len({field for field, _ in self.terms}) != len(self.terms):
            raise ValueError("metric requires unique terms")
        if any(
            not field or not math.isfinite(weight) or weight < 0
            for field, weight in self.terms
        ):
            raise ValueError("metric weights must be finite and non-negative")
        if not isinstance(self.category, MeritCategory):
            raise ValueError("invalid category")
        if not isinstance(self.direction, MetricDirection):
            raise ValueError("invalid metric direction")


@dataclass(frozen=True, slots=True)
class MeritEvidence:
    metric: str
    value: int | float

    def __post_init__(self) -> None:
        if not self.metric.strip() or not math.isfinite(self.value) or self.value < 0:
            raise ValueError("evidence must be named, finite and non-negative")


@dataclass(frozen=True, slots=True)
class PlayerMerit:
    rule_id: str
    title: str
    category: MeritCategory
    player_id: str
    display_name: str
    evidence_value: int | float
    evidence_label: str
    explanation: str
    evidence: tuple[MeritEvidence, ...]
    observed_aliases: tuple[str, ...]
    observed_teams: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("evidence", "observed_aliases", "observed_teams"):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        if (
            not self.rule_id.strip()
            or not self.title.strip()
            or not self.player_id.strip()
        ):
            raise ValueError("rule id, title and player id must be non-empty")
        if not math.isfinite(self.evidence_value) or self.evidence_value < 0:
            raise ValueError("evidence must be finite and non-negative")
        if not self.evidence or len({item.metric for item in self.evidence}) != len(
            self.evidence
        ):
            raise ValueError("raw evidence must be present and unique")


@dataclass(frozen=True, slots=True)
class TournamentMerits:
    merits: tuple[PlayerMerit, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "merits", tuple(self.merits))
        ids = [item.rule_id for item in self.merits]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate rule id: each title has exactly one recipient")
        if any(rule_id not in ACTIVE_MERIT_IDS for rule_id in ids):
            raise ValueError("unavailable or unknown merit rule")
        if ids != sorted(ids, key=ACTIVE_MERIT_IDS.index):
            raise ValueError("merits must follow frozen catalog order")

    def for_rule(self, rule_id: str) -> tuple[PlayerMerit, ...]:
        return tuple(item for item in self.merits if item.rule_id == rule_id)
