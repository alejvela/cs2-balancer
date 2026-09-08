from dataclasses import FrozenInstanceError, replace
from random import Random

import pytest

from application.player_impact import calculate_player_impact
from application.player_merits import (
    MERIT_RULES,
    _secondary_value,
    _winner,
    generate_tournament_merits,
)
from application.player_rankings import rank_tournament
from application.statistics_aggregation import aggregate_tournament
from models.player_merit import (
    MeritEvidence,
    MetricDirection,
    TournamentMerits,
)
from models.statistics import TournamentStatistics
from tests.unit.models.test_player_impact import statistics
from tests.unit.models.test_statistics import import_result, performance, played_map


@pytest.mark.parametrize(
    ("rule_id", "values", "expected"),
    [
        ("el_verdugo", {"kills": 9}, 9),
        ("la_apisonadora", {"damage": 3001}, 1500.5),
        ("el_abrelatas", {"entry_wins": 5}, 5),
        ("sin_miedo_al_exito", {"entry_count": 7}, 3.5),
        ("rey_del_clutch", {"v1_wins": 3, "v2_wins": 2}, 6.5),
        (
            "el_coleccionista",
            {"enemy2ks": 2, "enemy3ks": 3, "enemy4ks": 4, "enemy5ks": 5},
            59,
        ),
        ("pikachu", {"enemies_flashed": 17}, 8.5),
        ("el_escudero", {"assists": 11}, 5.5),
        ("el_alquimista", {"utility_damage": 301}, 150.5),
        ("el_cirujano", {"head_shot_kills": 7, "kills": 11}, 7 / 11),
        (
            "el_francotirador_sin_mira",
            {"shots_on_target_total": 7, "shots_fired_total": 13},
            7 / 13,
        ),
        ("el_superviviente", {"live_time": 301}, 150.5),
        ("tio_gilito", {"money_saved": 301}, 150.5),
    ],
)
def test_catalog_formula_winner_and_raw_evidence(rule_id, values, expected):
    player = statistics("winner", maps_played=2, **values)
    loser = statistics("loser", maps_played=2, kills=1, shots_fired_total=1)
    result = generate_tournament_merits(TournamentStatistics(1, 2, (loser, player)))
    (award,) = result.for_rule(rule_id)
    assert award.player_id == "winner"
    assert award.evidence_value == expected
    raw = {item.metric: item.value for item in award.evidence}
    assert all(raw[key] == value for key, value in values.items())


@pytest.mark.parametrize(
    "rule", [rule for rule in MERIT_RULES if rule.requires_participation]
)
def test_every_rate_requires_existing_participation_eligibility(rule):
    values = {field: 100 for field, _ in rule.terms}
    if rule.denominator != "maps_played":
        values[rule.denominator] = 100
    star = statistics("star", maps_played=1, **values)
    regular = statistics("regular", maps_played=3, kills=200, shots_fired_total=200)
    result = generate_tournament_merits(TournamentStatistics(1, 5, (star, regular)))
    assert [item.player_id for item in result.for_rule(rule.stable_id)] == ["regular"]
    evidence = {
        item.metric: item.value for item in result.for_rule(rule.stable_id)[0].evidence
    }
    assert evidence["required_maps"] == 2


def test_volume_can_be_won_without_rate_eligibility():
    star = statistics("star", kills=100, entry_wins=10, v2_wins=3, enemy5ks=2)
    regular = statistics("regular", maps_played=5, kills=10)
    result = generate_tournament_merits(TournamentStatistics(1, 5, (star, regular)))
    for rule in MERIT_RULES:
        if not rule.requires_participation:
            assert result.for_rule(rule.stable_id)[0].player_id == "star"


def test_single_ties_identity_order_repeat_shuffle_and_immutability():
    players = tuple(
        statistics(pid, display_name=name, kills=10)
        for pid, name in (("3", "AAA"), ("1", "ZZZ"), ("2", "MMM"))
    )
    source = TournamentStatistics(1, 1, players)
    result = generate_tournament_merits(source)
    assert [item.player_id for item in result.for_rule("el_verdugo")] == ["1"]
    assert generate_tournament_merits(source) == result
    assert (
        generate_tournament_merits(replace(source, players=tuple(reversed(players))))
        == result
    )
    shuffled = list(players)
    Random(25).shuffle(shuffled)
    assert (
        generate_tournament_merits(replace(source, players=tuple(shuffled))) == result
    )
    with pytest.raises(FrozenInstanceError):
        result.merits = ()
    with pytest.raises(FrozenInstanceError):
        result.merits[0].evidence_value = 0
    with pytest.raises(FrozenInstanceError):
        result.merits[0].evidence[0].value = 0


def test_aggregation_aliases_ratios_and_no_mutation_of_ranking_impact():
    maps = (
        played_map(
            "s",
            0,
            performance(
                "1",
                name="Old",
                kills=1,
                head_shot_kills=1,
                shots_fired_total=1,
                shots_on_target_total=1,
            ),
        ),
        played_map(
            "s",
            1,
            performance(
                "1",
                name="New",
                kills=9,
                head_shot_kills=2,
                shots_fired_total=9,
                shots_on_target_total=2,
            ),
        ),
    )
    source = import_result(*maps)
    aggregated = aggregate_tournament(source)
    ranking = rank_tournament(source, tournament_id="lan")
    impacts = tuple(calculate_player_impact(player) for player in aggregated.players)
    merits = generate_tournament_merits(aggregated)
    assert merits.for_rule("el_cirujano")[0].evidence_value == 0.3
    assert merits.for_rule("el_francotirador_sin_mira")[0].evidence_value == 0.3
    assert all(item.player_id == "1" for item in merits.merits)
    assert set(merits.merits[0].observed_aliases) == {"Old", "New"}
    assert (
        generate_tournament_merits(aggregate_tournament(import_result(*reversed(maps))))
        == merits
    )
    assert aggregate_tournament(source) == aggregated
    assert rank_tournament(source, tournament_id="lan") == ranking
    assert (
        tuple(calculate_player_impact(player) for player in aggregated.players)
        == impacts
    )


def test_empty_zero_denominators_and_fire_unavailable():
    assert generate_tournament_merits(
        TournamentStatistics(0, 0, ())
    ) == TournamentMerits(())
    zero = statistics(maps_played=0, utility_damage=999999)
    result = generate_tournament_merits(TournamentStatistics(0, 0, (zero,)))
    assert {item.rule_id for item in result.merits} == {
        "el_verdugo",
        "el_abrelatas",
        "rey_del_clutch",
        "el_coleccionista",
    }
    assert not result.for_rule("charmander")
    assert "charmander" not in {rule.stable_id for rule in MERIT_RULES}


def test_missing_metric_is_omitted(monkeypatch):
    import application.player_merits as service

    rule = replace(MERIT_RULES[0], terms=(("explicit_fire_damage", 1.0),))
    monkeypatch.setattr(service, "MERIT_RULES", (rule,))
    assert service.generate_tournament_merits(
        TournamentStatistics(1, 1, (statistics(utility_damage=100),))
    ) == TournamentMerits(())


def test_single_uses_canonical_ranking_order_and_minimum_direction():
    rule = replace(MERIT_RULES[0], tie_breakers=())
    weak = statistics("1", kills=1)
    strong = statistics("2", kills=30, damage=3000)
    assert _winner(rule, [(weak, 5, ()), (strong, 5, ())])[0] == strong
    minimum = replace(rule, direction=MetricDirection.MINIMUM)
    assert _winner(minimum, [(weak, 1, ()), (strong, 5, ())])[0] == weak


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_evidence_rejected(value):
    result = generate_tournament_merits(TournamentStatistics(1, 1, (statistics(),)))
    with pytest.raises(ValueError, match="finite and non-negative"):
        replace(result.merits[0], evidence_value=value)
    with pytest.raises(ValueError, match="finite and non-negative"):
        MeritEvidence("kills", value)


def test_result_and_rule_invariants():
    source = TournamentStatistics(1, 1, (statistics("1"), statistics("2")))
    result = generate_tournament_merits(source)
    first, second = result.merits[:2]
    with pytest.raises(ValueError, match="duplicate"):
        TournamentMerits((first, first))
    with pytest.raises(ValueError, match="frozen catalog"):
        TournamentMerits((second, first))
    with pytest.raises(ValueError, match="duplicate"):
        TournamentMerits((first, replace(first, player_id="other")))
    with pytest.raises(ValueError, match="unavailable"):
        TournamentMerits((replace(first, rule_id="charmander"),))
    for field in ("rule_id", "title", "player_id"):
        with pytest.raises(ValueError, match="non-empty"):
            replace(first, **{field: " "})
    with pytest.raises(ValueError, match="raw evidence"):
        replace(first, evidence=())
    with pytest.raises(ValueError, match="unique player"):
        generate_tournament_merits(replace(source, players=(source.players[0],) * 2))
    with pytest.raises(ValueError, match="non-empty"):
        replace(MERIT_RULES[0], stable_id="")
    with pytest.raises(ValueError, match="unique terms"):
        replace(MERIT_RULES[0], terms=())


def test_frozen_catalog_order():
    expected = (
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
    assert tuple(rule.stable_id for rule in MERIT_RULES) == expected
    result = generate_tournament_merits(
        TournamentStatistics(
            1, 1, (statistics(kills=1, shots_fired_total=1, utility_damage=999999),)
        )
    )
    assert tuple(item.rule_id for item in result.merits) == expected
    assert len({item.player_id for item in result.merits}) == 1
    assert result.for_rule("el_alquimista")[0].evidence_value == 999999
    assert not result.for_rule("charmander")


# Explicit expected secondary formulas, independent of production metadata.
SECONDARIES = [
    ("el_verdugo", [("damage",), ("kills", "maps_played")]),
    ("la_apisonadora", [("damage",), ("kills", "maps_played")]),
    ("el_abrelatas", [("entry_wins", "entry_count"), ("entry_count",)]),
    ("sin_miedo_al_exito", [("entry_wins", "maps_played"), ("entry_count",)]),
    (
        "rey_del_clutch",
        [
            ("v1_wins+v2_wins",),
            ("v1_wins+v2_wins", "v1_count+v2_count"),
            ("v1_count+v2_count",),
        ],
    ),
    ("el_coleccionista", [("enemy5ks",), ("enemy4ks",), ("enemy3ks",), ("enemy2ks",)]),
    (
        "pikachu",
        [
            ("flash_successes", "flash_count"),
            ("enemies_flashed",),
            ("flash_successes",),
        ],
    ),
    ("el_escudero", [("assists",)]),
    (
        "el_alquimista",
        [("utility_damage",), ("utility_successes",), ("utility_count",)],
    ),
    ("el_cirujano", [("head_shot_kills",), ("kills",), ("shots_on_target_total",)]),
    ("el_francotirador_sin_mira", [("shots_on_target_total",), ("head_shot_kills",)]),
    ("el_superviviente", [("live_time",), ("deaths",)]),
    ("tio_gilito", [("money_saved",), ("cash_earned",)]),
]


@pytest.mark.parametrize(("rule_id", "expected"), SECONDARIES)
def test_every_secondary_formula_direction_and_order(rule_id, expected):
    rule = next(rule for rule in MERIT_RULES if rule.stable_id == rule_id)
    assert len(rule.tie_breakers) == len(expected)
    for criterion, formula in zip(rule.tie_breakers, expected, strict=True):
        assert criterion.fields == tuple(formula[0].split("+"))
        assert criterion.denominator_fields == (
            tuple(formula[1].split("+")) if len(formula) > 1 else ()
        )
        fewer = formula == ("deaths",)
        assert criterion.direction == (
            MetricDirection.MINIMUM if fewer else MetricDirection.MAXIMUM
        )
        # Exercise each criterion independently, including later criteria that
        # are algebraically redundant after earlier exact ties in valid data.
        values = {field: 4 for field in criterion.fields}
        values.update({field: 2 for field in criterion.denominator_fields})
        a = statistics("a", **values)
        changed = dict(values)
        changed[criterion.fields[0]] = 3 if fewer else 5
        b = statistics("b", **changed)
        isolated = replace(rule, tie_breakers=(criterion,))
        assert _winner(isolated, [(a, 1, ()), (b, 1, ())])[0] == b
        if criterion.denominator_fields:
            assert _secondary_value(criterion, a) == (4 * len(criterion.fields)) / (
                2 * len(criterion.denominator_fields)
            )


@pytest.mark.parametrize(
    ("rule_id", "a", "b"),
    [
        ("el_verdugo", {"kills": 10, "damage": 100}, {"kills": 10, "damage": 101}),
        (
            "la_apisonadora",
            {"damage": 100, "maps_played": 1},
            {"damage": 200, "maps_played": 2},
        ),
        (
            "el_abrelatas",
            {"entry_wins": 2, "entry_count": 4},
            {"entry_wins": 2, "entry_count": 3},
        ),
        (
            "sin_miedo_al_exito",
            {"entry_count": 4, "entry_wins": 1},
            {"entry_count": 4, "entry_wins": 2},
        ),
        (
            "rey_del_clutch",
            {"v2_wins": 4, "v2_count": 4},
            {"v1_wins": 7, "v1_count": 7},
        ),
        ("el_coleccionista", {"enemy2ks": 7}, {"enemy5ks": 1}),
        (
            "pikachu",
            {"enemies_flashed": 4, "flash_successes": 1, "flash_count": 3},
            {"enemies_flashed": 4, "flash_successes": 1, "flash_count": 2},
        ),
        (
            "el_escudero",
            {"assists": 4, "maps_played": 1},
            {"assists": 8, "maps_played": 2},
        ),
        (
            "el_alquimista",
            {"utility_damage": 4, "maps_played": 1},
            {"utility_damage": 8, "maps_played": 2},
        ),
        (
            "el_cirujano",
            {"head_shot_kills": 1, "kills": 2},
            {"head_shot_kills": 2, "kills": 4},
        ),
        (
            "el_francotirador_sin_mira",
            {"shots_on_target_total": 1, "shots_fired_total": 2},
            {"shots_on_target_total": 2, "shots_fired_total": 4},
        ),
        (
            "el_superviviente",
            {"live_time": 4, "maps_played": 1},
            {"live_time": 8, "maps_played": 2},
        ),
        (
            "tio_gilito",
            {"money_saved": 4, "maps_played": 1},
            {"money_saved": 8, "maps_played": 2},
        ),
    ],
)
def test_each_rule_primary_tie_selects_one_recipient(rule_id, a, b):
    players = (statistics("a", **a), statistics("b", **b))
    result = generate_tournament_merits(TournamentStatistics(1, 2, players))
    (winner,) = result.for_rule(rule_id)
    assert winner.player_id == "b"
    assert len(result.merits) == len({merit.rule_id for merit in result.merits})
    assert (
        generate_tournament_merits(TournamentStatistics(1, 2, players[::-1])) == result
    )


@pytest.mark.parametrize("rule_id", ["el_abrelatas", "rey_del_clutch", "pikachu"])
def test_defined_secondary_zero_outranks_undefined_and_both_undefined_continue(rule_id):
    rule = next(rule for rule in MERIT_RULES if rule.stable_id == rule_id)
    ratio = next(
        criterion for criterion in rule.tie_breakers if criterion.denominator_fields
    )
    defined = statistics("z", **{field: 1 for field in ratio.denominator_fields})
    undefined = statistics("a")
    assert _secondary_value(ratio, undefined) is None
    assert _secondary_value(ratio, defined) == 0
    assert _winner(rule, [(undefined, 0, ()), (defined, 0, ())])[0] == defined
    assert _winner(rule, [(statistics("z"), 0, ()), (undefined, 0, ())])[0] == undefined


def test_final_fallback_reuses_scrum22_and_other_titles_remain_independent(monkeypatch):
    import application.player_merits as service
    from application.player_impact import impact_tie_break_key

    calls = []

    def recording_key(impact, player):
        calls.append(player.player_id)
        return impact_tie_break_key(impact, player)

    monkeypatch.setattr(service, "impact_tie_break_key", recording_key)
    a = statistics("a", kills=10, damage=100, assists=1)
    b = statistics("b", kills=10, damage=100, assists=10)
    result = generate_tournament_merits(TournamentStatistics(1, 1, (a, b)))
    assert result.for_rule("el_verdugo")[0].player_id == "b"
    assert {"a", "b"} <= set(calls)
    a = statistics("a", kills=10, damage=200, assists=1)
    result = generate_tournament_merits(TournamentStatistics(1, 1, (a, b)))
    assert result.for_rule("el_verdugo")[0].player_id == "a"
    assert result.for_rule("el_escudero")[0].player_id == "b"


def test_secondary_ratio_comparisons_do_not_round():
    rule = next(rule for rule in MERIT_RULES if rule.stable_id == "el_abrelatas")
    a = statistics("a", entry_wins=1, entry_count=10**18 + 1)
    b = statistics("b", entry_wins=1, entry_count=10**18)
    assert _winner(rule, [(a, 1, ()), (b, 1, ())])[0] == b
