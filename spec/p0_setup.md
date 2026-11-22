# P0 — 골격 (20분)

빈 폴더에서 프로젝트 골격을 만들어 줘. 기능 구현은 하지 마.

1. git 저장소가 아니면 `git init`. `uv init`(예제 파일은 삭제), 의존성 추가, `src/__init__.py`, `tests/`, `.gitignore`(.venv, node_modules, __pycache__, *.db, web/dist, .DS_Store). `pyproject.toml`에는 `[tool.ruff]`(`line-length = 100`), `[tool.pytest.ini_options]`(`pythonpath = ["."]`, `testpaths = ["tests"]`), `[tool.claude-kit]`(`check_size = true`) 구획을 넣는다
2. `app.py`: FastAPI 앱 생성. `GET /api/health` → `{"mode":"local","ollama":false,"ports":[]}`. `web/dist`가 있으면 `/`에서 서빙. `tests/test_app.py`에 health 응답 테스트 1개
3. `web/`: Vite React TypeScript 골격. 개발 서버가 `/api`를 `http://localhost:8000`으로 프록시
4. `contract/measurement.json`: 프론트와 백엔드가 공유할 응답 예시. 아래를 그대로 저장

```json
{
  "id": 1, "antenna": {"id": 1, "name": "모노폴 A", "kind": "monopole", "target_mhz": 433},
  "source": "synthetic", "cal_mode": "vna", "measured_at": "2026-11-26T15:00:00", "change_note": "",
  "sweep": [{"f_mhz": 10.0, "s11_db": -0.01}],
  "card": {
    "stage": "offtarget", "headline": "공진은 있지만 목표보다 낮습니다",
    "status": ["공진 381.25 MHz (목표 -51.75 MHz, -11.95 %)"],
    "diagnoses": [
      {"key": "too_long", "title": "안테나 도체가 김", "evidence": "공진 381.25 MHz, 목표 433 MHz", "action": "도체를 약 12 % 줄이는 것이 초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정", "guide": "도체가 길면 공진 주파수가 목표보다 낮아진다."},
      {"key": "feed_lead", "title": "급전부의 노출된 선이 김", "evidence": "공진 381.25 MHz, 목표 433 MHz", "action": "노출된 급전선을 짧게", "guide": "급전부의 노출된 선이 길거나 납땜 덩어리가 크면 공진 주파수가 낮아진다."}
    ]
  }
}
```
(`status`와 `headline` 문구는 p2에서 확정한다)

5. `tests/test_architecture.py`: CLAUDE.md의 구조 규칙을 검사하는 테스트. `ast`로 `app.py`와 `src/*.py`를 읽어 ① 파일 300줄 이하 ② 함수 40줄 이하 ③ 인자 5개 이하(self 제외) ④ `src/`가 `app`을 import하지 않음 ⑤ `src/` 모듈 사이에 순환 import 없음 ⑥ `src/` 하위 폴더에 `.py` 파일 없음을 확인한다. `src/`가 비어 있으면 무조건 통과하므로, 검사기마다 임시 파일로 만든 위반 예시를 실제로 잡는지 확인하는 테스트도 둔다. 이후 단계에서 이 테스트의 한도를 늘리거나 예외를 추가하지 않는다

통과 검사: `uv run pytest` 실행됨, `uv run ruff check .`와 `uv run ruff format --check .` 통과, `uv run uvicorn app:app` 후 `/api/health` 200, `npm --prefix web run build` 성공. 결과를 보여 주고 멈춰. 커밋은 검토 뒤에 한다.
