"""Inclusive comparisons that survive floating-point rounding.

The spec's limits are inclusive ("3 dB or more"). Subtracting two measured values can land a hair
on the wrong side (-3.1 - -6.1 == 2.9999999999999996), so limits are compared with a tolerance far
below any measurement resolution.
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-9


def _same(value: float, limit: float) -> bool:
    return math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_least(value: float, limit: float) -> bool:
    return value >= limit or _same(value, limit)


def at_most(value: float, limit: float) -> bool:
    return value <= limit or _same(value, limit)
