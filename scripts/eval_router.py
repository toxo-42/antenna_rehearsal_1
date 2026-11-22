"""Score question linking with a real local model.

Usage: uv run python scripts/eval_router.py <model> [cases.json]
Pass: at least 85 % correct and every unrelated question ("none") refused. Exit code 1 on fail.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.models import AntennaKind
from src.ollama import DEFAULT_BASE_URL
from src.router import OllamaRouter, key_for

DEFAULT_CASES = ROOT / "tests" / "route_cases.json"
PASS_RATE = 0.85
NONE = "none"


def answer_label(number: int | None) -> str:
    if number is None:
        return "failed"
    return key_for(number) or NONE


def main(model: str, cases_path: Path) -> int:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    router = OllamaRouter(model, DEFAULT_BASE_URL)
    wrong: list[tuple[dict, str]] = []
    seconds: list[float] = []
    for case in cases:
        started = time.monotonic()
        got = answer_label(router.choose(case["q"], AntennaKind.MONOPOLE))
        seconds.append(time.monotonic() - started)
        if got not in case["ok"]:
            wrong.append((case, got))
    none_total = sum(NONE in case["ok"] for case in cases)
    none_wrong = sum(NONE in case["ok"] for case, _ in wrong)
    correct = len(cases) - len(wrong)
    rate = correct / len(cases)
    print(f"모델 {model}, 질문 {len(cases)}개 ({cases_path.name})")
    print(
        f"맞음 {correct}/{len(cases)} ({rate * 100:.1f} %), 평균 {sum(seconds) / len(seconds):.2f}초"
    )
    print(f"무관한 질문 거절 {none_total - none_wrong}/{none_total}")
    for case, got in wrong:
        print(f"  틀림: {case['q']} → {got} (정답: {', '.join(case['ok'])})")
    passed = rate >= PASS_RATE and none_wrong == 0
    print("판정:", "합격" if passed else "불합격 (OLLAMA_MODEL을 비운다)")
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    path = Path(sys.argv[2]) if len(sys.argv) == 3 else DEFAULT_CASES
    sys.exit(main(sys.argv[1], path))
