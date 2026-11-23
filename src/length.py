"""The conductor length a student enters with a measurement (cm). Empty means not entered."""

import math
import re

MIN_LENGTH_CM = 0.1
MAX_LENGTH_CM = 1000.0
LENGTH_ERROR = (
    f"도체 길이(length_cm)는 {MIN_LENGTH_CM:g} cm 이상 {MAX_LENGTH_CM:g} cm 이하인 수여야 합니다. "
    "모르면 비워 두세요."
)
_PLAIN_DECIMAL = re.compile(r"[0-9]+(\.[0-9]+)?")  # no sign, exponent, underscore, other digits


def check_length(value: float | None) -> float | None:
    """The length as a float, or None when it was not entered. Raises ValueError (Korean text)
    for anything that is not a usable length."""
    if value is None:
        return None
    in_range = math.isfinite(value) and MIN_LENGTH_CM <= value <= MAX_LENGTH_CM
    if isinstance(value, bool) or not in_range:
        raise ValueError(f"{LENGTH_ERROR} (받은 값: {value})")
    return float(value)


def parse_length(text: str) -> float | None:
    """The length from a form field; blank means not entered. Only plain ASCII decimals such as
    `12` or `12.5` are read: `1e3`, `1_0` and full-width digits are refused."""
    written = text.strip()
    if not written:
        return None
    try:
        if _PLAIN_DECIMAL.fullmatch(written) is None:
            raise ValueError(written)
        return check_length(float(written))
    except ValueError:
        raise ValueError(f"{LENGTH_ERROR} (받은 값: '{text}')") from None
