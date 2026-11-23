"""The conductor length a student enters with a measurement (cm). Empty means not entered."""

import math

MAX_LENGTH_CM = 1000.0
LENGTH_ERROR = (
    f"도체 길이(length_cm)는 0보다 크고 {MAX_LENGTH_CM:g} cm 이하인 수여야 합니다. "
    "모르면 비워 두세요."
)


def check_length(value: float | None) -> float | None:
    """The length as a float, or None when it was not entered. Raises ValueError (Korean text)
    for anything that is not a usable length."""
    if value is None:
        return None
    if isinstance(value, bool) or not math.isfinite(value) or not 0 < value <= MAX_LENGTH_CM:
        raise ValueError(f"{LENGTH_ERROR} (받은 값: {value})")
    return float(value)


def parse_length(text: str) -> float | None:
    """The length from a form field; blank means not entered."""
    if not text.strip():
        return None
    try:
        return check_length(float(text))
    except ValueError:
        raise ValueError(f"{LENGTH_ERROR} (받은 값: '{text}')") from None
