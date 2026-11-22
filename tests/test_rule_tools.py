import pytest

from src.models import AntennaKind
from src.rule_tools import LENGTHEN, SHORTEN, amount_text, length_action
from tests.diag_helpers import antenna, context, magnitude_sweep

SWEEP = magnitude_sweep([0.0, -30.0, 0.0])


@pytest.mark.parametrize(
    ("pct", "text"),
    [
        (11.95, "약 12 %"),
        (12.5, "약 13 %"),  # half rounds up, not to the even number
        (0.5, "약 1 %"),
        (0.49, "1 % 미만"),
        (0.0, "1 % 미만"),
        (abs(251.0 / 200.0 - 1) * 100, "약 26 %"),  # exactly 25.5 %, computed as 25.49999999999999
        (abs(32.2 - 40.0) / 40.0 * 100, "약 20 %"),  # exactly 19.5 %, computed just under it
    ],
)
def test_amount_text_rounds_half_up_and_never_says_zero(pct: float, text: str) -> None:
    assert amount_text(pct) == text


@pytest.mark.parametrize(
    ("kind", "name"),
    [(AntennaKind.MONOPOLE, "안테나 도체"), (AntennaKind.PATCH, "패치 길이(공진 방향 변)")],
)
def test_length_action_names_the_length_and_carries_the_caution(
    kind: AntennaKind, name: str
) -> None:
    ctx = context(SWEEP, antenna(410.0, kind))

    assert length_action(ctx, SHORTEN, "약 12 %") == (
        f"{name}를 약 12 % 줄이는 것이 초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정"
    )
    assert "늘리는" in length_action(ctx, LENGTHEN, "약 12 %")
