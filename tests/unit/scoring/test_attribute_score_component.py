from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from models.player import Player
from optimizer.normalization.linear_normalizer import LinearNormalizer
from optimizer.normalization.normalizer import Normalizer
from scoring.attribute_score_component import AttributeScoreComponent


def build_component(
    *,
    name: str = "elo",
    attribute: str = "elo",
    normalized_score: float = 50.0,
    default_score: float = 0.0,
) -> tuple[AttributeScoreComponent, MagicMock]:
    normalizer = MagicMock(spec=Normalizer)
    normalizer.normalize.return_value = normalized_score

    component = AttributeScoreComponent(
        name=name,
        attribute=attribute,
        normalizer=normalizer,
        default_score=default_score,
    )

    return component, normalizer


def test_score_normalizes_configured_player_attribute():
    component, normalizer = build_component(normalized_score=72.5)
    player = Player(nick="Player", elo=1800)

    assert component.score(player) == pytest.approx(72.5)
    normalizer.normalize.assert_called_once_with(1800.0)


def test_component_is_callable_through_score_component_contract():
    component, _ = build_component(normalized_score=64.0)

    assert component(Player(nick="Player", elo=1500)) == pytest.approx(64.0)


@pytest.mark.parametrize(
    ("elo", "expected"),
    [
        (1000, 100.0),
        (1500, 50.0),
        (2000, 0.0),
    ],
)
def test_score_handles_normalizer_boundary_values(elo, expected):
    component = AttributeScoreComponent(
        name="elo",
        attribute="elo",
        normalizer=LinearNormalizer(min_value=1000, max_value=2000),
    )

    assert component.score(Player(nick="Player", elo=elo)) == pytest.approx(expected)


def test_missing_attribute_returns_configured_default_without_normalizing():
    component, normalizer = build_component(default_score=37.5)

    assert component.score(Player(nick="Player")) == pytest.approx(37.5)
    normalizer.normalize.assert_not_called()


@pytest.mark.parametrize(
    ("default_score", "expected"),
    [
        (-1.0, 0.0),
        (125.0, 100.0),
    ],
)
def test_default_score_is_clamped(default_score, expected):
    component, _ = build_component(default_score=default_score)

    assert component.default_score == expected
    assert component.score(Player(nick="Player")) == expected


@pytest.mark.parametrize(
    ("normalized_score", "expected"),
    [
        (-10.0, 0.0),
        (110.0, 100.0),
    ],
)
def test_normalized_score_is_clamped(normalized_score, expected):
    component, _ = build_component(normalized_score=normalized_score)

    assert component.score(Player(nick="Player", elo=1500)) == expected


def test_has_value_and_raw_value_reflect_numeric_attribute_availability():
    component, _ = build_component(attribute="kd")
    available_player = Player(nick="Available", kd=1.25)
    missing_player = Player(nick="Missing")

    assert component.has_value(available_player) is True
    assert component.raw_value(available_player) == pytest.approx(1.25)
    assert component.has_value(missing_player) is False
    assert component.raw_value(missing_player) is None
    assert component.has_value(None) is False
    assert component.has_value(SimpleNamespace(kd=True)) is False
    assert component.has_value(SimpleNamespace(kd="1.25")) is False


def test_compatibility_alias_is_used_when_configured_attribute_is_missing():
    component, normalizer = build_component(attribute="faceit_elo")

    component.score(SimpleNamespace(elo=1750))

    normalizer.normalize.assert_called_once_with(1750.0)


@pytest.mark.parametrize("field_name", ["name", "attribute"])
@pytest.mark.parametrize("invalid_value", [None, 123])
def test_constructor_rejects_non_string_name_and_attribute(
    field_name,
    invalid_value,
):
    normalizer = MagicMock(spec=Normalizer)
    arguments = {
        "name": "elo",
        "attribute": "elo",
        "normalizer": normalizer,
    }
    arguments[field_name] = invalid_value

    with pytest.raises(TypeError, match=f"{field_name} must be a string"):
        AttributeScoreComponent(**arguments)


@pytest.mark.parametrize("field_name", ["name", "attribute"])
def test_constructor_rejects_empty_name_and_attribute(field_name):
    normalizer = MagicMock(spec=Normalizer)
    arguments = {
        "name": "elo",
        "attribute": "elo",
        "normalizer": normalizer,
    }
    arguments[field_name] = "   "

    with pytest.raises(ValueError, match=f"{field_name} cannot be empty"):
        AttributeScoreComponent(**arguments)


def test_constructor_normalizes_name_and_attribute_whitespace():
    normalizer = MagicMock(spec=Normalizer)

    component = AttributeScoreComponent(
        name="  elo score  ",
        attribute="  elo  ",
        normalizer=normalizer,
    )

    assert component.name == "elo score"
    assert component.attribute == "elo"
    assert component.normalizer is normalizer


@pytest.mark.parametrize(
    ("normalizer", "exception", "message"),
    [
        (None, ValueError, "normalizer cannot be None"),
        (object(), TypeError, "must provide a normalize"),
    ],
)
def test_constructor_rejects_invalid_normalizer(normalizer, exception, message):
    with pytest.raises(exception, match=message):
        AttributeScoreComponent("elo", "elo", normalizer)


@pytest.mark.parametrize("default_score", [True, "50"])
def test_constructor_rejects_non_numeric_default_score(default_score):
    normalizer = MagicMock(spec=Normalizer)

    with pytest.raises(TypeError, match="default_score must be numeric"):
        AttributeScoreComponent(
            "elo",
            "elo",
            normalizer,
            default_score=default_score,
        )


def test_score_rejects_none_player():
    component, _ = build_component()

    with pytest.raises(ValueError, match="player cannot be None"):
        component.score(None)


@pytest.mark.parametrize("value", [True, "1800"])
def test_score_rejects_non_numeric_player_attribute(value):
    component, normalizer = build_component()

    with pytest.raises(TypeError, match="must be numeric"):
        component.score(SimpleNamespace(elo=value))

    normalizer.normalize.assert_not_called()


@pytest.mark.parametrize("normalized_score", [True, "50"])
def test_score_rejects_non_numeric_normalizer_result(normalized_score):
    component, _ = build_component(normalized_score=normalized_score)

    with pytest.raises(TypeError, match="must return a numeric value"):
        component.score(Player(nick="Player", elo=1800))


def test_score_propagates_normalizer_exception():
    component, normalizer = build_component()
    normalizer.normalize.side_effect = RuntimeError("normalizer failed")

    with pytest.raises(RuntimeError, match="normalizer failed"):
        component.score(Player(nick="Player", elo=1800))


def test_raw_value_rejects_none_player_and_non_numeric_attribute():
    component, _ = build_component()

    with pytest.raises(ValueError, match="player cannot be None"):
        component.raw_value(None)

    with pytest.raises(TypeError, match="must be numeric"):
        component.raw_value(SimpleNamespace(elo="1800"))


def test_repr_contains_useful_configuration():
    component, _ = build_component(
        name="ELO score",
        attribute="faceit_elo",
        default_score=25.0,
    )

    assert repr(component) == (
        "AttributeScoreComponent("
        "name='ELO score', "
        "attribute='faceit_elo', "
        "default_score=25.0)"
    )
