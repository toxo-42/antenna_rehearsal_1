# P3 — 저장과 API (30분)

`src/store.py`(표준 `sqlite3`), `sources.py`, `service.py`, `api.py`를 만들어 줘. `app.py`는 조립만 한다.

- `antennas(id, name, kind, target_mhz)`
- `measurements(id, antenna_id, measured_at, source, cal_mode, stage, resonance_mhz, s11_db, bandwidth_pct, sweep_json, card_json, change_note)`, 인덱스 `(antenna_id, measured_at)`, `stage`
- 값은 전부 `?` 바인딩. 한 측정은 트랜잭션 하나. `sweep_json`은 `[f_hz, s11_db, re, im]` 목록(re, im은 null 가능)
- `SweepSource`는 Protocol. 이번에는 `SyntheticSource`와 `StoredSource`만. `source` 값은 `usb | csv | stored | synthetic`

| 메서드 | 경로 |
|---|---|
| GET, POST | `/api/antennas` |
| GET | `/api/samples` (합성 이름 목록) |
| POST | `/api/measurements` (`antenna_id, source, sample?, cal_mode, change_note`) |
| POST | `/api/measurements/upload` (CSV, 2 MB 제한) |
| GET | `/api/measurements?antenna_id&stage&limit&offset` (sweep 제외) |
| GET | `/api/measurements/{id}` (`contract/measurement.json` 형태) |

값 목록: `kind`는 `monopole | patch`, `cal_mode`는 `vna | unknown`. 이 밖의 값은 422.

오류: 잘못된 입력 422, 없는 id 404, 한국어 메시지. 목표가 스윕 범위 밖이면 422.

통과 검사: 임시 DB로 합성 18종 저장 → 다시 읽은 카드가 동일, **`GET /api/measurements/{id}` 응답의 키 구조(중첩 포함)와 값 타입이 `contract/measurement.json`과 같음**, CSV 업로드, 오류 3종, **앱 재시작 후에도 이력 유지** 테스트 통과.
