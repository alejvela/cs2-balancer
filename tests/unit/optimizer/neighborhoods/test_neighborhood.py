from __future__ import annotations

import inspect

import pytest

from optimizer.neighborhoods.double_swap_neighborhood import DoubleSwapNeighborhood
from optimizer.neighborhoods.neighborhood import Neighborhood
from optimizer.neighborhoods.rotate_neighborhood import RotateNeighborhood
from optimizer.neighborhoods.swap_neighborhood import SwapNeighborhood


class SampleOnlyNeighborhood(Neighborhood):
    def sample(self, teams, k):
        return iter(())


def test_generate_is_concrete_while_sample_is_abstract():
    assert getattr(Neighborhood.generate, "__isabstractmethod__", False) is False
    assert getattr(Neighborhood.sample, "__isabstractmethod__", False) is True
    assert "sample" in Neighborhood.__abstractmethods__
    assert "generate" not in Neighborhood.__abstractmethods__


def test_subclass_implementing_only_sample_is_instantiable_and_inherits_generate():
    neighborhood = SampleOnlyNeighborhood()

    assert neighborhood.generate([]) is None


@pytest.mark.parametrize(
    "neighborhood_type",
    [SwapNeighborhood, RotateNeighborhood, DoubleSwapNeighborhood],
)
def test_concrete_neighborhoods_inherit_concrete_generate_contract(neighborhood_type):
    neighborhood = neighborhood_type()

    assert inspect.isabstract(neighborhood_type) is False
    assert neighborhood_type.generate is Neighborhood.generate
    assert neighborhood.generate([]) is None
