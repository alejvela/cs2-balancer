"""Finite real decision values shared by objective and GLOBAL boundaries."""

from math import isfinite
from numbers import Real


def finite_real(value: object, field_name: str) -> float:
    """Reject booleans, non-numeric values and non-finite float results."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be numeric.")
    try:
        numeric = float(value)
    except OverflowError as error:
        raise ValueError(f"{field_name} must be finite.") from error
    if not isfinite(numeric):
        raise ValueError(f"{field_name} must be finite.")
    return numeric
