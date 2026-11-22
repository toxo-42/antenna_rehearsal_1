# P3 — 저장과 API (30분)

`src/store.py`(표준 `sqlite3`), `sources.py`, `service.py`, `api.py`를 만들어 줘. `app.py`는 조립만 한다.

- `antennas(id, name, kind, target_mhz)`
- `measurements(id, antenna_id, measured_at, source, cal_mode, stage, resonance_mhz, s11_db, bandwidth_pct, sweep_json, card_json, change_note)`, 인덱스 `(antenna_id, measured_at)`, `stage`
- 값은 전부 `?` 바인딩. 한 측정은 트랜잭션 하나. `sweep_json`은 `[f_hz, s11_db, re, im]` 목록(re, im은 null 가능)
- DB 경로는 `create_app(db_path)`의 인자로 받는다(기본은 프로젝트 루트의 `antenna.db`, `app = create_app()`은 유지). sqlite 연결은 요청마다 열고 닫는다(FastAPI는 요청을 여러 스레드에서 처리하므로 연결 하나를 공유하지 않는다)
- `measured_at`은 서버가 저장할 때 넣는다. 계약 예시와 같은 초 단위 ISO 현지 시각. 선택된 공진이 없으면 `resonance_mhz, s11_db, bandwidth_pct`는 null
- `SweepSource`는 Protocol. 이번에는 `SyntheticSource`와 `StoredSource`(저장된 측정 id의 스윕을 다시 돌려준다)만. `source` 값은 `usb | csv | stored | synthetic`
- 판정 코어(p1·p2)는 스윕을 검사하지 않는다. 어느 source에서 온 스윕이든 `service`가 판정 전에 CSV 파서와 같은 검사(3점 이상, 주파수 오름차순, 유한한 수, 허용 범위)를 한 곳에서 거치게 하고, 어기면 422. 이 경우의 테스트를 둔다
- 허용 범위: 주파수 1 Hz~1 THz, `S11_dB` -1000~1000, `S11_real`·`S11_imag` -1000~1000(경계 포함). CSV 파서와 `check_sweep`이 같은 범위를 쓴다. 이 범위 안이면 판정이 만드는 값(깊이, 목표 차이 %, 대역 폭 %, 모드 비 등)이 모두 유한하고 0으로 나누는 일이 없다. 범위 안의 극단값으로 만든 스윕을 판정해도 예외가 없고 카드에 `inf`, `nan`이 없음을 테스트한다
- 판정에 쓰는 안테나는 항상 DB의 안테나(`antenna_id`)다. 합성 샘플이 가진 안테나 정보는 `/api/samples` 안내용으로만 쓴다

| 메서드 | 경로 |
|---|---|
| GET, POST | `/api/antennas` |
| GET | `/api/samples` (합성 샘플 목록. 항목은 `name, kind, target_mhz`) |
| POST | `/api/measurements` (`antenna_id, source, sample?, cal_mode, change_note`) |
| POST | `/api/measurements/upload` (multipart: CSV 파일과 `antenna_id, cal_mode, change_note`. 2 MB 제한) |
| GET | `/api/measurements?antenna_id&stage&limit&offset` |
| GET | `/api/measurements/{id}` (`contract/measurement.json` 형태. `resonance_mhz, s11_db, bandwidth_pct`는 저장한 열의 값 그대로이고 공진이 없으면 `null`) |

- `POST /api/measurements`는 이번에는 `source = synthetic`만 받고 `sample`이 필수다. 다른 source 값과 모르는 sample 이름은 422 (`usb`는 p6에서 추가, `csv`는 upload 경로로만 들어온다)
- 목록 응답은 배열이고 항목은 `measurements`의 열에서 `sweep_json`과 `card_json`을 뺀 것이다. `measured_at` 내림차순, 같으면 `id` 내림차순. `limit` 기본 50, 최대 200
- 업로드한 파일은 UTF-8(BOM 허용)로 읽는다. 읽을 수 없으면 422, 2 MB를 넘으면 413(정확히 2 MB는 받는다). multipart 형식이 깨진 요청도 한국어 422
- 생성 요청은 200을 돌려준다. `change_note`는 생략할 수 있고 생략하면 `""`
- 목록: `limit`이 200을 넘거나 `offset`이 음수면 422. 없는 `antenna_id`로 거르면 404가 아니라 빈 배열
- 숫자 필드는 엄격하게 받는다. JSON `true`나 `"1"`을 `antenna_id`, `target_mhz`로 받지 않는다(422). SQLite 정수 범위를 넘는 id는 없는 id로 본다(404, 500이 아님)

응답에는 `NaN`, `Infinity`가 나가지 않는다. 숫자 필드는 `null`로 바꾸고, 카드 문자열에도 `inf`, `nan`이 없어야 한다(p2의 status 규칙). 테스트: 공진점의 반사계수가 정확히 1(`S11_real = 1, S11_imag = 0`)인 CSV를 업로드하면 200이고 status에 공진점 R/X 줄이 없다.

값 목록: `kind`는 `monopole | patch`, `cal_mode`는 `vna | unknown`. 저장하는 `stage`는 카드의 stage 값이다(`invalid` 포함). 이 밖의 값은 422. 안테나의 `name`은 빈 문자열이 아니고 `target_mhz`는 유한한 양수여야 한다.

오류: 잘못된 입력 422, 없는 id 404(요청 본문의 `antenna_id` 포함), 한국어 메시지. 목표가 스윕의 첫 주파수보다 작거나 끝 주파수보다 크면 422(판정하면 "길이가 많이 다르다"는 틀린 안내가 나온다).

통과 검사: 임시 DB로 합성 18종을 샘플과 같은 `kind`, `target_mhz`의 안테나로 저장 → `GET /api/measurements/{id}`의 카드가 판정 코어를 직접 부른 결과와 같고, **`StoredSource`로 다시 읽어 판정한 카드도 같음**. **`GET /api/measurements/{id}` 응답의 키 구조(중첩 포함)와 값 타입이 `contract/measurement.json`과 같음**(정수와 실수는 같은 타입으로 본다. 계약의 `433`과 응답의 `433.0`. `null`이 될 수 있는 세 숫자는 공진이 있는 샘플로 비교하고, 공진이 없는 샘플에서 `null`인 것도 확인한다), CSV 업로드, 오류 3종, **앱 재시작 후에도 이력 유지** 테스트 통과.
