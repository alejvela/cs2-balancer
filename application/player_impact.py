"""Absolute, deterministic LAN Player Impact Rating v1 formula."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType

from models.player_impact import (
    LAN_IMPACT_VERSION,
    ImpactComponentResult,
    ImpactEvidence,
    PlayerImpactResult,
    TournamentImpactEligibility,
)
from models.statistics import PlayerStatistics, safe_ratio


@dataclass(frozen=True, slots=True)
class ImpactComponentDefinition:
    component_id: str
    label: str
    weight: float


IMPACT_COMPONENTS = (
    ImpactComponentDefinition("combat", "Combat", 0.40),
    ImpactComponentDefinition("opening", "Opening / Entry", 0.15),
    ImpactComponentDefinition("multikill", "Multikill", 0.10),
    ImpactComponentDefinition("supported_clutch", "Supported Clutch", 0.15),
    ImpactComponentDefinition("teamplay", "Teamplay", 0.10),
    ImpactComponentDefinition("utility_flash", "Utility / Flash", 0.10),
)
IMPACT_WEIGHTS = MappingProxyType(
    {item.component_id: item.weight for item in IMPACT_COMPONENTS}
)

DAMAGE_PER_MAP_SCALE = 1_500.0
KILLS_PER_MAP_SCALE = 15.0
ENTRY_WINS_PER_MAP_SCALE = 2.0
ENTRY_ATTEMPTS_PER_MAP_CONFIDENCE_SCALE = 3.0
MULTIKILL_VALUE_PER_MAP_SCALE = 5.0
CLUTCH_WIN_VALUE_PER_MAP_SCALE = 0.75
CLUTCH_ATTEMPTS_PER_MAP_CONFIDENCE_SCALE = 1.0
ASSISTS_PER_MAP_SCALE = 6.0
UTILITY_DAMAGE_PER_MAP_SCALE = 150.0
UTILITY_USES_PER_MAP_CONFIDENCE_SCALE = 8.0
ENEMIES_FLASHED_PER_MAP_SCALE = 8.0
FLASH_USES_PER_MAP_CONFIDENCE_SCALE = 8.0

MULTIKILL_EVENT_WEIGHTS = {"enemy2ks": 1.0, "enemy3ks": 2.0, "enemy4ks": 4.0, "enemy5ks": 7.0}
CLUTCH_WIN_WEIGHTS = {"v1_wins": 1.0, "v2_wins": 1.75}


def _validate_weights() -> None:
    if len(IMPACT_WEIGHTS) != len(IMPACT_COMPONENTS):
        raise ValueError("impact component ids must be unique")
    if not math.isclose(sum(IMPACT_WEIGHTS.values()), 1.0, abs_tol=1e-12):
        raise ValueError("impact weights must sum to 1.0")


_validate_weights()


def bounded_positive_score(value: float, scale: float) -> float:
    """Smoothly saturate a non-negative value; scale scores about 63.2."""
    if value < 0 or scale <= 0:
        raise ValueError("value must be non-negative and scale must be positive")
    return min(100.0, max(0.0, 100.0 * -math.expm1(-value / scale)))


def _component(
    component_id: str,
    score: float,
    evidence: tuple[ImpactEvidence, ...],
) -> ImpactComponentResult:
    definition = next(item for item in IMPACT_COMPONENTS if item.component_id == component_id)
    bounded = min(100.0, max(0.0, score))
    return ImpactComponentResult(
        component_id=component_id,
        label=definition.label,
        score=bounded,
        weight=definition.weight,
        weighted_contribution=bounded * definition.weight,
        evidence=evidence,
    )


def calculate_combat_component(stats: PlayerStatistics) -> ImpactComponentResult:
    damage_score = bounded_positive_score(stats.damage_per_map, DAMAGE_PER_MAP_SCALE)
    kill_score = bounded_positive_score(stats.kills_per_map, KILLS_PER_MAP_SCALE)
    survival_score = 100.0 * safe_ratio(stats.raw.kills, stats.raw.kills + stats.raw.deaths)
    score = 0.45 * damage_score + 0.35 * kill_score + 0.20 * survival_score
    return _component(
        "combat",
        score,
        (
            ImpactEvidence("damage_per_map", stats.damage_per_map),
            ImpactEvidence("damage_score", damage_score),
            ImpactEvidence("kills_per_map", stats.kills_per_map),
            ImpactEvidence("kill_score", kill_score),
            ImpactEvidence("kills", stats.raw.kills),
            ImpactEvidence("deaths", stats.raw.deaths),
            ImpactEvidence("survival_engagement_score", survival_score),
            ImpactEvidence("headshot_rate_unweighted", stats.headshot_rate),
            ImpactEvidence("accuracy_unweighted", stats.accuracy),
        ),
    )


def calculate_opening_component(stats: PlayerStatistics) -> ImpactComponentResult:
    wins_per_map = safe_ratio(stats.raw.entry_wins, stats.maps_played)
    attempts_per_map = safe_ratio(stats.raw.entry_count, stats.maps_played)
    volume_score = bounded_positive_score(wins_per_map, ENTRY_WINS_PER_MAP_SCALE)
    confidence = 1.0 - math.exp(-attempts_per_map / ENTRY_ATTEMPTS_PER_MAP_CONFIDENCE_SCALE)
    efficiency_score = 100.0 * stats.entry_success_rate * confidence
    return _component(
        "opening",
        0.60 * volume_score + 0.40 * efficiency_score,
        (
            ImpactEvidence("entry_wins", stats.raw.entry_wins),
            ImpactEvidence("entry_attempts", stats.raw.entry_count),
            ImpactEvidence("entry_wins_per_map", wins_per_map),
            ImpactEvidence("entry_success_rate", stats.entry_success_rate),
            ImpactEvidence("opportunity_confidence", confidence),
        ),
    )


def calculate_multikill_component(stats: PlayerStatistics) -> ImpactComponentResult:
    weighted_value = sum(
        getattr(stats.raw, field) * weight for field, weight in MULTIKILL_EVENT_WEIGHTS.items()
    )
    value_per_map = safe_ratio(weighted_value, stats.maps_played)
    return _component(
        "multikill",
        bounded_positive_score(value_per_map, MULTIKILL_VALUE_PER_MAP_SCALE),
        (
            *(ImpactEvidence(field, getattr(stats.raw, field)) for field in MULTIKILL_EVENT_WEIGHTS),
            ImpactEvidence("weighted_multikill_value", weighted_value),
            ImpactEvidence("weighted_multikill_value_per_map", value_per_map),
        ),
    )


def calculate_clutch_component(stats: PlayerStatistics) -> ImpactComponentResult:
    weighted_wins = sum(
        getattr(stats.raw, field) * weight for field, weight in CLUTCH_WIN_WEIGHTS.items()
    )
    wins_per_map = safe_ratio(weighted_wins, stats.maps_played)
    attempts_per_map = safe_ratio(stats.supported_clutch_attempts, stats.maps_played)
    volume_score = bounded_positive_score(wins_per_map, CLUTCH_WIN_VALUE_PER_MAP_SCALE)
    confidence = 1.0 - math.exp(-attempts_per_map / CLUTCH_ATTEMPTS_PER_MAP_CONFIDENCE_SCALE)
    efficiency_score = 100.0 * stats.supported_clutch_success_rate * confidence
    return _component(
        "supported_clutch",
        0.60 * volume_score + 0.40 * efficiency_score,
        (
            ImpactEvidence("v1_wins", stats.raw.v1_wins),
            ImpactEvidence("v1_attempts", stats.raw.v1_count),
            ImpactEvidence("v2_wins", stats.raw.v2_wins),
            ImpactEvidence("v2_attempts", stats.raw.v2_count),
            ImpactEvidence("weighted_supported_clutch_wins", weighted_wins),
            ImpactEvidence("supported_clutch_success_rate", stats.supported_clutch_success_rate),
            ImpactEvidence("opportunity_confidence", confidence),
        ),
    )


def calculate_teamplay_component(stats: PlayerStatistics) -> ImpactComponentResult:
    return _component(
        "teamplay",
        bounded_positive_score(stats.assists_per_map, ASSISTS_PER_MAP_SCALE),
        (ImpactEvidence("assists_per_map", stats.assists_per_map),),
    )


def calculate_utility_flash_component(stats: PlayerStatistics) -> ImpactComponentResult:
    utility_confidence = 1.0 - math.exp(
        -safe_ratio(stats.raw.utility_count, stats.maps_played)
        / UTILITY_USES_PER_MAP_CONFIDENCE_SCALE
    )
    utility_efficiency = 100.0 * stats.utility_success_rate * utility_confidence
    utility_volume = bounded_positive_score(
        stats.utility_damage_per_map, UTILITY_DAMAGE_PER_MAP_SCALE
    )
    utility_score = 0.60 * utility_volume + 0.40 * utility_efficiency

    flash_confidence = 1.0 - math.exp(
        -safe_ratio(stats.raw.flash_count, stats.maps_played)
        / FLASH_USES_PER_MAP_CONFIDENCE_SCALE
    )
    flash_efficiency = 100.0 * stats.flash_success_rate * flash_confidence
    flash_volume = bounded_positive_score(
        stats.enemies_flashed_per_map, ENEMIES_FLASHED_PER_MAP_SCALE
    )
    flash_score = 0.60 * flash_volume + 0.40 * flash_efficiency
    return _component(
        "utility_flash",
        0.50 * utility_score + 0.50 * flash_score,
        (
            ImpactEvidence("utility_damage_per_map", stats.utility_damage_per_map),
            ImpactEvidence("utility_success_rate", stats.utility_success_rate),
            ImpactEvidence("utility_opportunity_confidence", utility_confidence),
            ImpactEvidence("utility_bucket_score", utility_score),
            ImpactEvidence("enemies_flashed_per_map", stats.enemies_flashed_per_map),
            ImpactEvidence("flash_success_rate", stats.flash_success_rate),
            ImpactEvidence("flash_opportunity_confidence", flash_confidence),
            ImpactEvidence("flash_bucket_score", flash_score),
        ),
    )


def calculate_player_impact(stats: PlayerStatistics) -> PlayerImpactResult:
    components = (
        calculate_combat_component(stats),
        calculate_opening_component(stats),
        calculate_multikill_component(stats),
        calculate_clutch_component(stats),
        calculate_teamplay_component(stats),
        calculate_utility_flash_component(stats),
    )
    return PlayerImpactResult(
        player_id=stats.player_id,
        display_name=stats.display_name,
        model_version=LAN_IMPACT_VERSION,
        score=sum(item.weighted_contribution for item in components),
        components=components,
    )


def tournament_impact_eligibility(
    stats: PlayerStatistics,
    maximum_maps_played: int,
) -> TournamentImpactEligibility:
    if maximum_maps_played < 0:
        raise ValueError("maximum_maps_played cannot be negative")
    required_maps = math.ceil(maximum_maps_played * 0.50)
    eligible = stats.maps_played >= required_maps
    reason = (
        f"played {stats.maps_played} maps; requires at least {required_maps} "
        f"of tournament maximum {maximum_maps_played}"
    )
    return TournamentImpactEligibility(eligible, stats.maps_played, required_maps, reason)


def impact_tie_break_key(
    impact: PlayerImpactResult,
    stats: PlayerStatistics,
) -> tuple[float, float, int, int, float, str]:
    """Comparison evidence for SCRUM-22; this function performs no ranking."""
    return (
        -impact.score,
        -stats.damage_per_map,
        -stats.supported_clutch_wins,
        -stats.raw.entry_wins,
        -stats.kills_per_map,
        stats.player_id,
    )
