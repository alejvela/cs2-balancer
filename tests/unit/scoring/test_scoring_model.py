from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from models.player import Player
from optimizer.activity.activity_factor_model import ActivityFactorModel
from optimizer.normalization.normalizer import Normalizer
from scoring.attribute_score_component import AttributeScoreComponent
from scoring.score_component import ScoreComponent
from scoring.scoring_model import ScoringModel
from scrapers.player_record import ActivityRecord


class DeterministicComponent(ScoreComponent):
    def __init__(
        self,
        name: Any,
        scores: float | Mapping[str, float] = 50.0,
        available: bool | Mapping[str, bool] = True,
        raw_values: float | Mapping[str, float | None] | None = None,
    ) -> None:
        self._name = name
        self._scores = scores
        self._available = available
        self._raw_values = raw_values

    @property
    def name(self):
        return self._name

    def score(self, player: Player):
        return self._resolve(self._scores, player)

    def has_value(self, player: Player) -> bool:
        return bool(self._resolve(self._available, player))

    def raw_value(self, player: Player):
        return self._resolve(self._raw_values, player)

    @staticmethod
    def _resolve(value, player: Player):
        if isinstance(value, Mapping):
            return value[player.nick]

        return value


class FixedNormalizer(Normalizer):
    def __init__(self, score: float) -> None:
        self.score = score

    def normalize(self, value: float) -> float:
        return self.score


def make_model(
    *,
    score: float = 50.0,
    minimum_available_weight: float = 0.0,
    default_power: float = 0.0,
    activity_factor_model: ActivityFactorModel | None = None,
) -> ScoringModel:
    return ScoringModel(
        components=[DeterministicComponent("Power", score)],
        weights={"Power": 10.0},
        minimum_available_weight=minimum_available_weight,
        default_power=default_power,
        activity_factor_model=activity_factor_model,
    )


def make_activity(
    matches_0_7_days: int,
    matches_8_30_days: int,
    matches_31_90_days: int,
) -> ActivityRecord:
    return ActivityRecord(
        matches_0_7_days=matches_0_7_days,
        matches_8_30_days=matches_8_30_days,
        matches_31_90_days=matches_31_90_days,
        total_matches_90_days=(
            matches_0_7_days
            + matches_8_30_days
            + matches_31_90_days
        ),
    )


def test_configuration_properties_and_defensive_weight_copy():
    component = DeterministicComponent("Power", 75.0)
    activity_model = ActivityFactorModel()
    model = ScoringModel(
        components=[component],
        weights={"power": 25.0},
        minimum_available_weight=40.0,
        default_power=15.0,
        activity_factor_model=activity_model,
    )

    returned_weights = model.weights
    returned_weights["Power"] = 999.0

    assert model.components == (component,)
    assert model.weights == {"Power": 25.0}
    assert model.minimum_available_weight == pytest.approx(40.0)
    assert model.default_power == pytest.approx(15.0)
    assert model.activity_factor_model is activity_model
    assert model.activity_enabled is True
    assert len(model) == 1


@pytest.mark.parametrize(
    ("components", "exception", "message"),
    [
        (None, ValueError, "components cannot be None"),
        (123, TypeError, "components must be iterable"),
        ([], ValueError, "At least one ScoreComponent is required"),
        ([None], ValueError, "Component 1 cannot be None"),
        ([object()], TypeError, "must be a ScoreComponent instance"),
    ],
)
def test_constructor_rejects_invalid_component_collections(
    components,
    exception,
    message,
):
    with pytest.raises(exception, match=message):
        ScoringModel(components=components, weights={"Power": 1.0})


@pytest.mark.parametrize(
    ("name", "exception", "message"),
    [
        (123, TypeError, "must expose a string name"),
        ("   ", ValueError, "has an empty name"),
    ],
)
def test_constructor_rejects_invalid_component_names(name, exception, message):
    with pytest.raises(exception, match=message):
        ScoringModel(
            components=[DeterministicComponent(name)],
            weights={"Power": 1.0},
        )


def test_constructor_rejects_duplicate_component_names_case_insensitively():
    with pytest.raises(ValueError, match="Duplicated component name"):
        ScoringModel(
            components=[
                DeterministicComponent("Power"),
                DeterministicComponent(" power "),
            ],
            weights={"Power": 1.0},
        )


@pytest.mark.parametrize(
    ("weights", "exception", "message"),
    [
        (None, ValueError, "weights cannot be None"),
        ([10.0], TypeError, "weights must be a mapping"),
        ({1: 10.0}, TypeError, "weight key must be a string"),
        ({"  ": 10.0}, ValueError, "Weight names cannot be empty"),
        ({"Power": True}, TypeError, "must be numeric"),
        ({"Power": "10"}, TypeError, "must be numeric"),
        ({"Power": 0.0}, ValueError, "must be greater than zero"),
        ({"Power": -1.0}, ValueError, "must be greater than zero"),
        ({}, ValueError, "Missing weight for component"),
        (
            {"Power": 10.0, "Unknown": 5.0},
            ValueError,
            "unknown components",
        ),
    ],
)
def test_constructor_rejects_invalid_weights(weights, exception, message):
    with pytest.raises(exception, match=message):
        ScoringModel(
            components=[DeterministicComponent("Power")],
            weights=weights,
        )


def test_weights_are_case_insensitive_and_need_not_sum_to_one_or_one_hundred():
    model = ScoringModel(
        components=[
            DeterministicComponent("ELO", 80.0),
            DeterministicComponent("KD", 20.0),
        ],
        weights={"elo": 3.0, "kd": 1.0},
    )

    assert model.weights == {"ELO": 3.0, "KD": 1.0}
    assert model.base_power(Player(nick="Player")) == pytest.approx(65.0)


@pytest.mark.parametrize("value", [True, "40"])
def test_minimum_available_weight_rejects_non_numeric_values(value):
    with pytest.raises(TypeError, match="must be numeric"):
        make_model(minimum_available_weight=value)


@pytest.mark.parametrize("value", [-0.01, 100.01])
def test_minimum_available_weight_must_be_between_zero_and_one_hundred(value):
    with pytest.raises(ValueError, match="must be between 0 and 100"):
        make_model(minimum_available_weight=value)


@pytest.mark.parametrize("value", [True, "20"])
def test_default_power_rejects_non_numeric_values(value):
    with pytest.raises(TypeError, match="default_power must be numeric"):
        make_model(default_power=value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-10.0, 0.0),
        (110.0, 100.0),
    ],
)
def test_default_power_is_clamped(value, expected):
    assert make_model(default_power=value).default_power == pytest.approx(expected)


def test_constructor_rejects_invalid_activity_model():
    with pytest.raises(TypeError, match="ActivityFactorModel or None"):
        make_model(activity_factor_model=object())


def test_weighted_aggregation_and_component_breakdown():
    model = ScoringModel(
        components=[
            DeterministicComponent("ELO", 80.0, raw_values=1800.0),
            DeterministicComponent("KD", 20.0, raw_values=1.1),
        ],
        weights={"ELO": 75.0, "KD": 25.0},
    )

    result = model.evaluate_base(Player(nick="Player"))

    assert result["base_power"] == pytest.approx(65.0)
    assert result["configured_weight"] == pytest.approx(100.0)
    assert result["available_weight"] == pytest.approx(100.0)
    assert result["missing_weight"] == pytest.approx(0.0)
    assert result["availability_percentage"] == pytest.approx(100.0)
    assert result["has_sufficient_data"] is True
    assert result["components"]["ELO"] == {
        "available": True,
        "raw_value": 1800.0,
        "score": 80.0,
        "configured_weight": 75.0,
        "effective_weight": 75.0,
        "weighted_score": 6000.0,
    }


def test_missing_attribute_component_is_excluded_and_weight_is_redistributed():
    elo = AttributeScoreComponent(
        name="ELO",
        attribute="elo",
        normalizer=FixedNormalizer(80.0),
        default_score=10.0,
    )
    kd = AttributeScoreComponent(
        name="KD",
        attribute="kd",
        normalizer=FixedNormalizer(20.0),
        default_score=90.0,
    )
    model = ScoringModel(
        components=[elo, kd],
        weights={"ELO": 25.0, "KD": 75.0},
    )

    result = model.evaluate_base(Player(nick="Player", elo=1800))

    assert result["base_power"] == pytest.approx(80.0)
    assert result["available_weight"] == pytest.approx(25.0)
    assert result["missing_weight"] == pytest.approx(75.0)
    assert result["availability_percentage"] == pytest.approx(25.0)
    assert result["components"]["ELO"]["effective_weight"] == pytest.approx(100.0)
    assert result["components"]["KD"] == {
        "available": False,
        "raw_value": None,
        "score": None,
        "configured_weight": 75.0,
        "effective_weight": 0.0,
        "weighted_score": 0.0,
    }


@pytest.mark.parametrize(
    ("threshold", "expected_power", "sufficient"),
    [
        (60.0, 80.0, True),
        (60.01, 12.0, False),
    ],
)
def test_availability_threshold_includes_exact_boundary(
    threshold,
    expected_power,
    sufficient,
):
    model = ScoringModel(
        components=[
            DeterministicComponent("Available", 80.0),
            DeterministicComponent("Missing", 20.0, available=False),
        ],
        weights={"Available": 60.0, "Missing": 40.0},
        minimum_available_weight=threshold,
        default_power=12.0,
    )

    result = model.evaluate_base(Player(nick="Player"))

    assert result["base_power"] == pytest.approx(expected_power)
    assert result["has_sufficient_data"] is sufficient


def test_no_available_components_use_default_power_even_at_zero_threshold():
    model = ScoringModel(
        components=[DeterministicComponent("Missing", 80.0, available=False)],
        weights={"Missing": 10.0},
        minimum_available_weight=0.0,
        default_power=30.0,
    )

    result = model.evaluate_base(Player(nick="Player"))

    assert result["base_power"] == pytest.approx(30.0)
    assert result["available_weight"] == pytest.approx(0.0)
    assert result["availability_percentage"] == pytest.approx(0.0)
    assert result["has_sufficient_data"] is False


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (-20.0, 0.0),
        (120.0, 100.0),
    ],
)
def test_component_scores_are_clamped_for_finite_values(score, expected):
    model = make_model(score=score)

    result = model.evaluate_base(Player(nick="Player"))

    assert result["base_power"] == pytest.approx(expected)
    assert result["components"]["Power"]["score"] == pytest.approx(expected)


@pytest.mark.parametrize("score", [True, "50"])
def test_invalid_component_scores_are_rejected(score):
    model = make_model(score=score)

    with pytest.raises(TypeError, match="must return a numeric score"):
        model.base_power(Player(nick="Player"))


def test_activity_disabled_keeps_base_and_final_power_equal():
    model = make_model(score=80.0)
    player = Player(nick="Player", level=6, activity=make_activity(0, 0, 0))

    result = model.evaluate(player)

    assert model.activity_evaluation(player) is None
    assert model.activity_factor(player) == pytest.approx(1.0)
    assert model.adjusted_power(player) == pytest.approx(80.0)
    assert result["base_power"] == pytest.approx(80.0)
    assert result["power"] == pytest.approx(80.0)
    assert result["activity_enabled"] is False
    assert result["activity"]["enabled"] is False


def test_activity_enabled_adjusts_only_final_power():
    component = AttributeScoreComponent(
        name="ELO",
        attribute="elo",
        normalizer=FixedNormalizer(80.0),
    )
    model = ScoringModel(
        components=[component],
        weights={"ELO": 40.0},
        activity_factor_model=ActivityFactorModel(),
    )
    player = Player(
        nick="Player",
        elo=1800,
        level=6,
        activity=make_activity(0, 0, 0),
    )

    result = model.evaluate(player)

    assert result["components"]["ELO"]["score"] == pytest.approx(80.0)
    assert result["base_power"] == pytest.approx(80.0)
    assert result["activity_factor"] == pytest.approx(0.75)
    assert result["adjusted_power"] == pytest.approx(60.0)
    assert result["power"] == pytest.approx(60.0)
    assert result["activity_enabled"] is True
    assert result["activity"]["enabled"] is True


@pytest.mark.parametrize(
    ("base_power", "exception", "message"),
    [
        (True, TypeError, "base_power must be numeric"),
        ("80", TypeError, "base_power must be numeric"),
        (-1.0, ValueError, "base_power cannot be negative"),
    ],
)
def test_explicit_activity_base_power_is_validated(base_power, exception, message):
    model = make_model(activity_factor_model=ActivityFactorModel())
    player = Player(nick="Player")

    with pytest.raises(exception, match=message):
        model.adjusted_power(player, base_power=base_power)


def test_explicit_activity_base_power_is_clamped_to_one_hundred():
    model = make_model(activity_factor_model=ActivityFactorModel())

    assert model.adjusted_power(
        Player(nick="Player"),
        base_power=120.0,
    ) == pytest.approx(100.0)


def test_component_access_helpers_are_case_insensitive():
    component = DeterministicComponent("Power", 75.0)
    model = ScoringModel([component], {"Power": 25.0})
    player = Player(nick="Player")

    assert model.get_component(" power ") is component
    assert model.get_weight("POWER") == pytest.approx(25.0)
    assert model.has_component("pOwEr") is True
    assert model.has_component(123) is False
    assert model.has_component("  ") is False
    assert model.component_score(player, "power") == pytest.approx(75.0)


def test_component_score_returns_none_when_component_is_unavailable():
    model = ScoringModel(
        [DeterministicComponent("Missing", 75.0, available=False)],
        {"Missing": 10.0},
    )

    assert model.component_score(Player(nick="Player"), "Missing") is None


@pytest.mark.parametrize("name", [None, 123, "  "])
def test_get_component_rejects_invalid_names(name):
    model = make_model()
    exception = TypeError if not isinstance(name, str) else ValueError

    with pytest.raises(exception):
        model.get_component(name)


def test_get_component_rejects_unknown_name():
    with pytest.raises(KeyError, match="was not found"):
        make_model().get_component("Unknown")


def test_as_dict_describes_components_and_activity_configuration():
    model = ScoringModel(
        components=[
            AttributeScoreComponent(
                "ELO",
                "elo",
                FixedNormalizer(80.0),
            )
        ],
        weights={"ELO": 40.0},
        minimum_available_weight=25.0,
        default_power=10.0,
        activity_factor_model=ActivityFactorModel(),
    )

    result = model.as_dict()

    assert result["component_count"] == 1
    assert result["configured_weight"] == pytest.approx(40.0)
    assert result["minimum_available_weight"] == pytest.approx(25.0)
    assert result["default_power"] == pytest.approx(10.0)
    assert result["activity_enabled"] is True
    assert result["activity_model"]["type"] == "ActivityFactorModel"
    assert result["components"] == [{
        "name": "ELO",
        "type": "AttributeScoreComponent",
        "weight": 40.0,
        "attribute": "elo",
    }]


def test_rank_uses_final_power_then_base_power_then_elo_then_nickname():
    players = [
        Player(
            nick="BaseHigh",
            elo=1000,
            level=6,
            activity=make_activity(0, 0, 0),
        ),
        Player(
            nick="EloHigh",
            elo=2000,
            level=6,
            activity=make_activity(10, 20, 30),
        ),
        Player(
            nick="Zulu",
            elo=1500,
            level=6,
            activity=make_activity(10, 20, 30),
        ),
        Player(
            nick="Alpha",
            elo=1500,
            level=6,
            activity=make_activity(10, 20, 30),
        ),
    ]
    scores = {
        "BaseHigh": 80.0,
        "EloHigh": 60.0,
        "Zulu": 60.0,
        "Alpha": 60.0,
    }
    model = ScoringModel(
        [DeterministicComponent("Power", scores)],
        {"Power": 1.0},
        activity_factor_model=ActivityFactorModel(),
    )

    ranked = model.rank(players)

    assert [player.nick for player in ranked] == [
        "BaseHigh",
        "EloHigh",
        "Zulu",
        "Alpha",
    ]


def test_rank_supports_ascending_order():
    players = [Player(nick="High"), Player(nick="Low")]
    model = ScoringModel(
        [DeterministicComponent("Power", {"High": 80.0, "Low": 20.0})],
        {"Power": 1.0},
    )

    assert [player.nick for player in model.rank(players, descending=False)] == [
        "Low",
        "High",
    ]


@pytest.mark.parametrize(
    ("players", "message"),
    [
        (None, "players cannot be None"),
        ([], "At least one player is required"),
        ([None], "Player 1 cannot be None"),
    ],
)
def test_rank_rejects_invalid_player_collections(players, message):
    with pytest.raises(ValueError, match=message):
        make_model().rank(players)


def test_ranking_helpers_preserve_order_and_return_expected_shapes():
    players = [Player(nick="Low"), Player(nick="High")]
    model = ScoringModel(
        [DeterministicComponent("Power", {"Low": 20.0, "High": 80.0})],
        {"Power": 1.0},
    )

    scores = model.rank_with_scores(players)
    evaluations = model.rank_with_evaluations(players)

    assert [(player.nick, score) for player, score in scores] == [
        ("High", 80.0),
        ("Low", 20.0),
    ]
    assert [player.nick for player, _ in evaluations] == ["High", "Low"]
    assert evaluations[0][1]["power"] == pytest.approx(80.0)
    assert evaluations[1][1]["power"] == pytest.approx(20.0)


def test_evaluation_does_not_mutate_player():
    player = Player(
        nick="Player",
        elo=1800,
        level=6,
        activity=make_activity(5, 10, 15),
    )
    before = player.as_dict()
    model = ScoringModel(
        [
            AttributeScoreComponent(
                "ELO",
                "elo",
                FixedNormalizer(80.0),
            )
        ],
        {"ELO": 1.0},
        activity_factor_model=ActivityFactorModel(),
    )

    model.evaluate(player)

    assert player.as_dict() == before


def test_repr_contains_useful_configuration():
    model = ScoringModel(
        [DeterministicComponent("ELO"), DeterministicComponent("KD")],
        {"ELO": 40.0, "KD": 25.0},
    )

    assert repr(model) == (
        "ScoringModel("
        "components=[ELO, KD], "
        "configured_weight=65.00, "
        "activity_model=disabled)"
    )
