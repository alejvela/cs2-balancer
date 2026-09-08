"""Deterministic tournament merits, independent of ranking and presentation."""

from fractions import Fraction

from application.player_impact import (
    CLUTCH_WIN_WEIGHTS,
    MULTIKILL_EVENT_WEIGHTS,
    calculate_player_impact,
    impact_tie_break_key,
    tournament_impact_eligibility,
)
from models.player_merit import (
    ACTIVE_MERIT_IDS,
    MeritCategory,
    MeritEvidence,
    MeritRule,
    MeritTieBreaker,
    MetricDirection,
    PlayerMerit,
    TournamentMerits,
)
from models.statistics import PlayerStatistics, TournamentStatistics


def _rule(rule_id, title, category, field, denominator=None, *, terms=None):
    terms = tuple(terms.items()) if terms is not None else ((field, 1.0),)
    formula = " + ".join(f"{name} * {weight:g}" for name, weight in terms)
    if denominator:
        formula = f"({formula}) / {denominator}"
    return MeritRule(
        rule_id,
        title,
        category,
        formula,
        formula,
        terms,
        denominator,
        denominator is not None,
        tie_breakers=SECONDARY_CRITERIA[rule_id],
    )


def _secondary(fields, denominator=(), *, minimum=False):
    return MeritTieBreaker(
        (fields,) if isinstance(fields, str) else fields,
        (denominator,) if isinstance(denominator, str) else denominator,
        MetricDirection.MINIMUM if minimum else MetricDirection.MAXIMUM,
    )


SECONDARY_CRITERIA = {
    "el_verdugo": (_secondary("damage"), _secondary("kills", "maps_played")),
    "la_apisonadora": (_secondary("damage"), _secondary("kills", "maps_played")),
    "el_abrelatas": (
        _secondary("entry_wins", "entry_count"),
        _secondary("entry_count"),
    ),
    "sin_miedo_al_exito": (
        _secondary("entry_wins", "maps_played"),
        _secondary("entry_count"),
    ),
    "rey_del_clutch": (
        _secondary(("v1_wins", "v2_wins")),
        _secondary(("v1_wins", "v2_wins"), ("v1_count", "v2_count")),
        _secondary(("v1_count", "v2_count")),
    ),
    "el_coleccionista": tuple(
        _secondary(field) for field in ("enemy5ks", "enemy4ks", "enemy3ks", "enemy2ks")
    ),
    "pikachu": (
        _secondary("flash_successes", "flash_count"),
        _secondary("enemies_flashed"),
        _secondary("flash_successes"),
    ),
    "el_escudero": (_secondary("assists"),),
    "el_alquimista": tuple(
        _secondary(field)
        for field in ("utility_damage", "utility_successes", "utility_count")
    ),
    "el_cirujano": tuple(
        _secondary(field)
        for field in ("head_shot_kills", "kills", "shots_on_target_total")
    ),
    "el_francotirador_sin_mira": (
        _secondary("shots_on_target_total"),
        _secondary("head_shot_kills"),
    ),
    "el_superviviente": (_secondary("live_time"), _secondary("deaths", minimum=True)),
    "tio_gilito": (_secondary("money_saved"), _secondary("cash_earned")),
}


# Explicit product order, independent of category and translated display names.
MERIT_RULES = tuple(
    sorted(
        (
            _rule("el_verdugo", "El Verdugo", MeritCategory.COMBAT, "kills"),
            _rule(
                "la_apisonadora",
                "La Apisonadora",
                MeritCategory.COMBAT,
                "damage",
                "maps_played",
            ),
            _rule("el_abrelatas", "El Abrelatas", MeritCategory.OPENING, "entry_wins"),
            _rule(
                "sin_miedo_al_exito",
                "Sin miedo al éxito",
                MeritCategory.OPENING,
                "entry_count",
                "maps_played",
            ),
            _rule(
                "rey_del_clutch",
                "Rey del Clutch",
                MeritCategory.CLUTCH,
                None,
                terms=CLUTCH_WIN_WEIGHTS,
            ),
            _rule(
                "el_coleccionista",
                "El Coleccionista",
                MeritCategory.MULTIKILL,
                None,
                terms=MULTIKILL_EVENT_WEIGHTS,
            ),
            _rule(
                "el_escudero",
                "El Escudero",
                MeritCategory.SUPPORT,
                "assists",
                "maps_played",
            ),
            _rule(
                "pikachu",
                "Pikachu",
                MeritCategory.SUPPORT,
                "enemies_flashed",
                "maps_played",
            ),
            _rule(
                "el_alquimista",
                "El Alquimista",
                MeritCategory.UTILITY,
                "utility_damage",
                "maps_played",
            ),
            _rule(
                "el_cirujano",
                "El Cirujano",
                MeritCategory.PRECISION,
                "head_shot_kills",
                "kills",
            ),
            _rule(
                "el_francotirador_sin_mira",
                "El Francotirador sin mira",
                MeritCategory.PRECISION,
                "shots_on_target_total",
                "shots_fired_total",
            ),
            _rule(
                "el_superviviente",
                "El Superviviente",
                MeritCategory.SURVIVAL,
                "live_time",
                "maps_played",
            ),
            _rule(
                "tio_gilito",
                "Tío Gilito",
                MeritCategory.ECONOMY,
                "money_saved",
                "maps_played",
            ),
        ),
        key=lambda rule: ACTIVE_MERIT_IDS.index(rule.stable_id),
    )
)


def _evaluate(rule: MeritRule, player: PlayerStatistics, maximum_maps: int):
    eligibility = tournament_impact_eligibility(player, maximum_maps)
    if rule.requires_participation and not eligibility.eligible:
        return None
    evidence = []
    numerator = Fraction(0)
    for field, weight in rule.terms:
        value = getattr(player.raw, field, None)
        if value is None:
            return None
        evidence.append(MeritEvidence(field, value))
        numerator += Fraction(value) * Fraction(str(weight))
    denominator = 1
    if rule.denominator:
        denominator = (
            player.maps_played
            if rule.denominator == "maps_played"
            else getattr(player.raw, rule.denominator, None)
        )
        if denominator is None or denominator == 0:
            return None
        evidence.append(MeritEvidence(rule.denominator, denominator))
    if rule.requires_participation:
        if rule.denominator != "maps_played":
            evidence.append(MeritEvidence("maps_played", player.maps_played))
        evidence.append(MeritEvidence("required_maps", eligibility.required_maps))
        evidence.append(MeritEvidence("maximum_maps_played", maximum_maps))
    return numerator / denominator, tuple(evidence)


def _raw_value(player: PlayerStatistics, field: str):
    return (
        player.maps_played
        if field == "maps_played"
        else getattr(player.raw, field, None)
    )


def _secondary_value(criterion: MeritTieBreaker, player: PlayerStatistics):
    values = [_raw_value(player, field) for field in criterion.fields]
    denominators = [_raw_value(player, field) for field in criterion.denominator_fields]
    if any(value is None for value in values + denominators):
        return None
    denominator = sum(denominators) if denominators else 1
    return Fraction(sum(values), denominator) if denominator else None


def _winner(rule, candidates):
    best = (max if rule.direction == MetricDirection.MAXIMUM else min)(
        value for _, value, _ in candidates
    )
    tied = [item for item in candidates if item[1] == best]
    for criterion in rule.tie_breakers:
        if len(tied) == 1:
            break
        evaluated = [(item, _secondary_value(criterion, item[0])) for item in tied]
        defined = [(item, value) for item, value in evaluated if value is not None]
        if defined:
            best = (max if criterion.direction == MetricDirection.MAXIMUM else min)(
                value for _, value in defined
            )
            tied = [item for item, value in defined if value == best]
    if len(tied) == 1:
        return tied[0]
    return min(
        tied,
        key=lambda item: impact_tie_break_key(
            calculate_player_impact(item[0]), item[0]
        ),
    )


def generate_tournament_merits(statistics: TournamentStatistics) -> TournamentMerits:
    """Consume SCRUM-20 tournament aggregates; omit undefined/unavailable metrics."""
    players = statistics.players
    if len({player.player_id for player in players}) != len(players):
        raise ValueError("tournament statistics must contain unique player ids")
    maximum_maps = max((player.maps_played for player in players), default=0)
    merits = []
    for rule in MERIT_RULES:
        candidates = []
        for player in players:
            result = _evaluate(rule, player, maximum_maps)
            if result is not None:
                value, evidence = result
                candidates.append((player, value, evidence))
        if not candidates:
            continue
        player, value, evidence = _winner(rule, candidates)
        raw_evidence = {item.metric: item for item in evidence}
        for criterion in rule.tie_breakers:
            for field in criterion.fields + criterion.denominator_fields:
                observed = _raw_value(player, field)
                if observed is not None:
                    raw_evidence.setdefault(field, MeritEvidence(field, observed))
        evidence = tuple(raw_evidence.values())
        merits.append(
            PlayerMerit(
                rule.stable_id,
                rule.title,
                rule.category,
                player.player_id,
                player.display_name,
                int(value) if value.denominator == 1 else float(value),
                rule.evidence_label,
                f"{rule.direction.value}: {rule.description}",
                evidence,
                player.observed_aliases,
                player.observed_teams,
            )
        )
    return TournamentMerits(tuple(merits))
