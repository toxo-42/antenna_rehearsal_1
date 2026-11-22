# 프로젝트
안테나를 처음 배우는 학생이 S11 측정 결과를 이해하고 고치도록 돕는 웹 앱. 노트북에서 로컬로 실행한다.

# 절대 원칙
1. 숫자, 방향(늘리기/줄이기), 결론, 할 일은 **코드의 규칙**이 만든다. LLM은 이것들을 생성하거나 수정하지 않는다. LLM의 역할은 학생 질문을 검증된 설명에 연결하는 것뿐이다.
2. LiteVNA, Ollama, 인터넷이 모두 없어도 샘플 데이터로 판정 카드까지 동작한다.
3. 합성 샘플은 화면에 항상 "합성 데이터"로 표시한다. 실측인 것처럼 보이게 하지 않는다.

# 구조
- 루트: `app.py`(조립만), `src/`(평평한 모듈), `tests/`, `web/`(React + Vite + TypeScript), `README.md`
- `src/`는 `app.py`를 import하지 않는다. 순환 import 금지. 교체할 부품은 `typing.Protocol`로 받는다.
- 함수 40줄, 파일 300줄, 인자 5개 이하. 공개 함수는 타입 힌트와 테스트를 둔다.
- 규칙 추가는 함수 추가로 한다. if/elif를 늘리지 않는다.

# 도구
- Python은 `uv`만 쓴다 (`uv add`, `uv run pytest`). 전역 pip 금지. `requirements.txt`는 기본으로 만들지 않는다. 요청받으면 `uv export --format requirements.txt --no-hashes --no-emit-project -o requirements.txt`로 생성
- 의존성: fastapi, uvicorn, pyserial, python-multipart / 개발: pytest, httpx, ruff. 이 밖의 것은 물어보고 추가
- macOS와 Windows에서 모두 실행되어야 한다. `pathlib` 사용

# 작업 방식
- 요청한 것만 만든다. 테스트를 먼저 쓰고, 실행 결과를 보여 준 뒤 완료라고 한다
- 오류를 숨기거나 기대값을 바꿔 통과시키지 않는다
- 파일을 만들거나 고칠 때는 Edit/Write 도구를 쓴다. 셸의 `cat >`이나 스크립트로 소스 파일을 쓰지 않는다 (포맷·크기 검사 훅이 그 경로에서만 동작한다)
- 사용자에게 보이는 글은 한국어, 코드와 식별자는 영어
- 커밋은 Conventional Commits 접두어 + 한국어 설명
