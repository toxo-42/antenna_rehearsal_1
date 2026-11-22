from src.tolerance import at_least, at_most


def test_plain_comparisons_still_hold() -> None:
    assert at_least(3.1, 3.0) and not at_least(2.9, 3.0)
    assert at_most(-6.1, -6.0) and not at_most(-5.9, -6.0)


def test_values_equal_up_to_rounding_count_as_meeting_the_limit() -> None:
    assert -3.1 - -6.1 < 3.0  # the rounding error this module exists for
    assert at_least(-3.1 - -6.1, 3.0)
    assert at_most(abs(519.6 - 433.0), 433.0 * 20 / 100)


def test_a_real_difference_is_not_absorbed() -> None:
    assert not at_least(2.999999, 3.0)
    assert not at_most(86.600001, 86.6)
