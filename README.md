# 안테나 S11 도우미

안테나를 처음 배우는 학생이 S11 측정 결과를 이해하고 고치도록 돕는 웹 앱입니다. 노트북에서 로컬로 실행합니다.
측정 장비(SAA-2), Ollama, 인터넷이 없어도 합성 샘플로 판정 카드까지 동작합니다.

## 빠른 시작

```sh
uv sync
npm --prefix web ci
npm --prefix web run build
uv run uvicorn app:app --port 8000
```

브라우저에서 <http://localhost:8000> 을 엽니다. 끌 때는 터미널에서 `Ctrl+C`.

- 8000번 포트가 이미 쓰이고 있으면 `--port 8010`처럼 다른 번호를 쓰고 그 주소를 엽니다.
- 측정 기록은 저장소 폴더의 `antenna.db`에 저장됩니다(처음 실행할 때 생깁니다).

## 필요한 것

| 도구 | 용도 | 확인한 버전 |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | Python 실행과 의존성 (Python 3.14 이상, `pyproject.toml`) | uv 0.11.24, Python 3.14.6 |
| Node.js + npm | 화면(`web/`) 빌드와 테스트 | Node 26.3.1, npm 11.16.0 |
| Ollama (선택) | AI 설명과 질문 연결. 없어도 판정 카드는 그대로 나옵니다 | 0.40.16 |
| SAA-2 (선택) | USB 측정. 없으면 합성 샘플이나 CSV 파일을 씁니다 | HW V2_2 |

위 버전은 macOS에서 확인한 것입니다. 이보다 낮은 버전에서 되는지는 확인하지 않았습니다.
Python은 따로 설치하지 않고 `uv`를 통해서만 실행합니다(`pip` 쓰지 않음).

## 설치

`uv sync`는 `.venv`를 만들고 Python 의존성을 설치합니다. `npm --prefix web ci`는 `package-lock.json` 기준으로 `web/node_modules`를 설치합니다.

```sh
uv sync
npm --prefix web ci
```

`npm ci`에서 `fsevents`의 install script에 대한 `allow-scripts` 경고가 나올 수 있습니다. 빌드와 테스트에는 영향이 없었습니다.

## 실행

빌드로 `web/dist`를 만들고(화면을 고친 뒤에는 다시 실행), 서버가 화면과 API를 같은 주소에서 서빙합니다.

```sh
npm --prefix web run build
uv run uvicorn app:app --port 8000
```

`web/dist`가 없으면 API만 뜨고 `/`는 404입니다. 먼저 빌드하세요.

## 테스트

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm --prefix web test
npm --prefix web run lint
```

## 환경 변수

| 이름 | 값 | 동작 |
|---|---|---|
| `OLLAMA_MODEL` | 설정 안 함 | 기본 모델 `qwen3.5:9b`로 AI 설명과 질문 연결을 켭니다 |
| | 빈 값 (`OLLAMA_MODEL=`) | AI 설명과 질문 연결을 모두 끕니다 |
| | 모델 이름 (예: `qwen3.5:4b`) | 그 모델을 씁니다 |
| `OLLAMA_EXPLAIN` | `off` | AI 설명 버튼만 끕니다(질문 연결은 유지) |
| `APP_MODE` | 설정 안 함 또는 `local` | 보통 모드. `antenna.db`를 씁니다 |
| | `demo` | 시연 모드. `demo.db`의 측정을 화면과 API로 볼 수만 있습니다(아래 참고) |

macOS(zsh)에서는 명령 앞에 붙입니다.

```sh
OLLAMA_MODEL= uv run uvicorn app:app --port 8000
OLLAMA_MODEL=qwen3.5:4b OLLAMA_EXPLAIN=off uv run uvicorn app:app --port 8000
```

Windows에서 환경 변수를 주는 방법은 아직 확인하지 않아 적지 않았습니다.

현재 설정은 <http://localhost:8000/api/health> 에서 볼 수 있습니다(`ollama`: 질문 연결, `explain`: AI 설명).

### Ollama (선택)

```sh
ollama pull qwen3.5:9b
```

Ollama 요청은 이 PC의 `127.0.0.1:11434`로만 보냅니다. `HTTP_PROXY` 같은 프록시 설정이 있어도 프록시를 거치지 않습니다(`tests/test_ollama.py`).
Ollama가 꺼져 있어도 앱은 뜨고 판정 카드도 같게 나옵니다. AI 설명은 "AI 설명을 만들지 못했습니다"로 나오고, 질문은 설명 목록에서 직접 고르게 됩니다.
AI가 쓴 글은 항상 "AI 설명(참고용)"으로 표시됩니다. 코드는 글의 "지금 해 볼 것" 부분만 카드의 방향(늘리기/줄이기)과 맞는지 검사해서, 어긋나면 버립니다. 다른 부분까지 검사하지는 않으므로, 기준은 언제나 판정 카드입니다.

### 시연 모드 (`APP_MODE=demo`)

저장된 측정만 보여 주는 모드입니다. 안테나 추가, 측정, 업로드, USB, AI는 꺼집니다. `demo.db`가 있어야 시작합니다.

1. `antenna.db`의 측정 목록을 봅니다.

   ```sh
   uv run python scripts/export_demo.py
   ```

2. 목록의 첫 열(id)에서 고른 번호를 넣어 `demo.db`를 만듭니다. 아래는 id 1과 2를 고른 경우입니다. 목록에 없는 id를 넣으면 종료 코드 1로 끝나고 아무것도 쓰지 않습니다. `demo.db`가 이미 있으면 새 것으로 **교체**됩니다.

   ```sh
   uv run python scripts/export_demo.py 1 2
   ```

3. "측정 N개를 …demo.db에 저장했습니다"가 나온 것을 확인한 뒤 시연 서버를 띄웁니다. 내보내기가 실패했다면 예전 `demo.db`가 그대로 쓰입니다.

   ```sh
   APP_MODE=demo uv run uvicorn app:app --port 8000
   ```

`demo.db`가 없거나 측정이 0건이면 서버가 시작하지 않고 만드는 방법을 알려 줍니다.

## 합성 데이터 안내

- "측정 → 장비 없이 연습하기 (합성 샘플)"의 샘플(`good`, `offtarget_low`, `open` 등 18개)은 **코드로 만든 합성 데이터**입니다. 실제 안테나를 잰 값이 아닙니다.
- 합성 측정은 화면과 이력에 항상 "합성 데이터"로 표시됩니다.
- 판정은 샘플 이름이 아니라 "1. 안테나"에서 고른 안테나(종류, 목표 주파수)로 합니다.
- 실제로 잰 CSV 예시는 `tests/data/`에 있습니다(`monopole_12cm.csv` 등). "3-나. CSV 파일로 측정"에서 올려 볼 수 있습니다.
