"""Verified guide sentences shown on the card. The text is fixed by spec/p2_diagnosis.md."""

from src.models import AntennaKind

MONOPOLE = AntennaKind.MONOPOLE
PATCH = AntennaKind.PATCH

GUIDES: dict[str, str | dict[AntennaKind, str]] = {
    "positive_s11": "수동 안테나는 들어온 것보다 큰 신호를 되돌려 보낼 수 없으므로, "
    "그런 값이 나오면 교정이나 연결이 잘못된 것이다.",
    "feed_short": "신호선과 접지가 서로 닿으면 신호가 안테나로 가지 못하고 거의 모두 되돌아온다.",
    "feed_open": "신호선이 안테나에 전기적으로 붙어 있지 않으면 "
    "신호가 끊어진 곳에서 거의 모두 되돌아온다.",
    "feed_fault": "안테나가 전기적으로 연결되지 않으면 "
    "모든 주파수에서 신호가 거의 모두 되돌아온다.",
    "lossy": "접촉이 나쁘거나 손이나 금속이 가까우면 신호가 열로 사라져서, "
    "뚜렷한 골짜기 없이 넓은 범위에서 반사가 조금씩 줄어든다.",
    "length_far": {
        MONOPOLE: "안테나 도체가 길수록 공진 주파수는 낮아지고 짧을수록 높아진다.",
        PATCH: "패치의 공진 방향 변이 길수록 공진 주파수는 낮아지고 짧을수록 높아진다.",
    },
    "out_of_range": "반사가 가장 작은 지점이 측정 범위의 끝에 있으면 "
    "진짜 공진은 측정 범위 밖에 있을 수 있다.",
    "too_short": {
        MONOPOLE: "도체가 짧으면 공진 주파수가 목표보다 높아진다.",
        PATCH: "패치의 공진 방향 변이 짧으면 공진 주파수가 목표보다 높아진다.",
    },
    "too_long": {
        MONOPOLE: "도체가 길면 공진 주파수가 목표보다 낮아진다.",
        PATCH: "패치의 공진 방향 변이 길면 공진 주파수가 목표보다 낮아진다.",
    },
    "feed_lead": "급전부의 노출된 선이 길거나 납땜 덩어리가 크면 공진 주파수가 낮아진다.",
    "band_edge": "측정 점 사이가 넓으면 대역의 끝이 어디인지 정확히 알 수 없어서, "
    "목표가 대역 끝에 가까우면 대역 안에 있다고 확신할 수 없다.",
    "r_low": {
        MONOPOLE: "접지판이 작으면 공진은 보이지만 안테나의 입력 저항이 낮아져 "
        "신호가 잘 들어가지 않는다.",
        PATCH: "패치는 급전점이 중심에 가까울수록 입력 저항이 낮아져, "
        "너무 안쪽이면 신호가 잘 들어가지 않는다.",
    },
    "r_high": {
        MONOPOLE: "접지 연결의 접촉이 나쁘면 안테나의 입력 저항이 높아져 "
        "신호가 잘 들어가지 않는다.",
        PATCH: "패치는 급전점이 가장자리에 가까울수록 입력 저항이 높아져, "
        "너무 바깥쪽이면 신호가 잘 들어가지 않는다.",
    },
    "reactance": "저항이 알맞아도 남은 리액턴스가 있으면 신호 일부가 되돌아온다.",
    "match_unknown": "공진은 있지만 정합이 얕고, "
    "저항과 리액턴스 중 어느 쪽이 원인인지는 이 데이터로 나눌 수 없다.",
    "common_mode": "케이블 바깥면에 전류가 흐르면 케이블도 안테나처럼 동작해서, "
    "손으로 잡거나 위치를 바꾸면 측정값이 달라진다.",
    "third_mode": "목표 근처에서 보인 공진은 기본 공진이 아니라 "
    "더 높은 주파수에서 다시 나타난 공진일 수 있다.",
    "weak_fundamental": "모노폴은 기본 공진의 약 3배 주파수에서 다시 공진한다. "
    "급전부 연결이 나쁘거나 도체가 휘면 기본 공진이 얕아져서 3배 자리 공진만 뚜렷하게 보일 수 있다.",
    "other_resonance": "안테나가 아닌 케이블이나 접지판도 다른 주파수에서 공진할 수 있다.",
    "narrow": {
        MONOPOLE: "도체가 가늘면 잘 동작하는 주파수 폭이 좁아진다.",
        PATCH: "기판이 얇거나 유전율이 높으면 잘 동작하는 주파수 폭이 좁아진다.",
    },
    "no_resonance": "이 측정에서는 반사가 뚜렷하게 줄어드는 골짜기가 보이지 않는다. "
    "공진이 측정 범위 밖에 있거나 너무 얕아서 드러나지 않았을 수 있다.",
    "good": "목표 주파수에서 반사가 작고 동작하는 폭도 충분하다.",
    "uncalibrated": "교정을 확인하지 않으면 케이블과 커넥터의 영향이 측정값에 섞인다.",
}


def guide_for(key: str, kind: AntennaKind) -> str:
    """The guide sentence for one diagnosis key, picked by antenna kind where the text differs."""
    sentence = GUIDES[key]
    if isinstance(sentence, str):
        return sentence
    return sentence[kind]
