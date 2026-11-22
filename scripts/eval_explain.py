"""Generate plain-language explanations for 10 cards with a real local model.

Usage: uv run python scripts/eval_explain.py <model>
Cards: the 6 measured rows of tests/data/ and the synthetic offtarget_low, offtarget_high, good,
unmatched_low_r (cal_mode vna). Pass: at most 2 of 10 rejected or failed and a mean of at most
90 seconds. Exit code 1 on fail. Read the printed texts and check each agrees with its card.
A rejected try (even one a retry recovered) is printed with the sentence or format that broke it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.explain import Explanation, OllamaExplainer
from src.models import Antenna, AntennaKind, CalMode, Card
from src.ollama import DEFAULT_BASE_URL
from src.sweep_parser import parse_sweep_csv
from src.synthetic import make_sample
from src.verdict import build_card

DATA = ROOT / "tests" / "data"
MEASURED = [
    ("monopole_5cm.csv", AntennaKind.MONOPOLE, 1350.0),
    ("monopole_11.5cm.csv", AntennaKind.MONOPOLE, 650.0),
    ("monopole_12cm.csv", AntennaKind.MONOPOLE, 625.0),
    ("monopole_12cm.csv", AntennaKind.MONOPOLE, 433.0),
    ("monopole_14cm.csv", AntennaKind.MONOPOLE, 535.0),
    ("saa2_patch_2450.csv", AntennaKind.PATCH, 2450.0),
]
SYNTHETIC = ["offtarget_low", "offtarget_high", "good", "unmatched_low_r"]
MAX_BAD = 2
MAX_MEAN_S = 90.0


def cards() -> list[tuple[str, Card, Antenna]]:
    found: list[tuple[str, Card, Antenna]] = []
    for name, kind, target in MEASURED:
        sweep = parse_sweep_csv((DATA / name).read_text(encoding="utf-8"))
        antenna = Antenna(name=name, kind=kind, target_mhz=target)
        found.append((f"{name}@{target:g}", build_card(sweep, antenna, CalMode.VNA), antenna))
    for name in SYNTHETIC:
        sample = make_sample(name)
        card = build_card(sample.sweep, sample.antenna, CalMode.VNA)
        found.append((f"합성 {name}", card, sample.antenna))
    return found


def row(name: str, result: Explanation) -> str:
    chars = len(result.text) if result.text is not None else "-"
    tries = len({reason.split(" ", 1)[0] for reason in result.rejections})
    retried = f"  버려짐 {tries}회" if tries else ""
    return (
        f"{name:32} {result.status:9} 경고 {len(result.warnings)}  {chars}자  "
        f"{result.seconds}초{retried}"
    )


def main(model: str) -> int:
    explainer = OllamaExplainer(model, DEFAULT_BASE_URL)
    results = [(name, card, explainer.explain(card, ant)) for name, card, ant in cards()]
    print(f"모델 {model}")
    for name, _, result in results:
        print(row(name, result))
    bad = sum(result.status in ("rejected", "failed") for _, _, result in results)
    mean_s = sum(result.seconds or 0.0 for _, _, result in results) / len(results)
    passed = bad <= MAX_BAD and mean_s <= MAX_MEAN_S
    print(f"버려짐·실패 {bad}/{len(results)}, 평균 {mean_s:.1f}초")
    print("판정:", "합격" if passed else "불합격 (더 큰 모델로 다시, 안 되면 OLLAMA_EXPLAIN=off)")
    for name, card, result in results:
        print(f"\n===== {name} ({result.status}) — 카드: {card.headline}")
        for reason in result.rejections:
            print("버려진 글:", reason)
        if result.warnings:
            print("카드에 없는 수치:", ", ".join(result.warnings))
        print(result.text or "(표시하지 않음)")
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
