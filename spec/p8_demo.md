# P8 — 시연 링크 (60분)

`APP_MODE=demo`를 추가해 줘.
- USB 측정은 막고, 저장된 실측과 합성 샘플만 쓴다. LLM은 끈다. 쓰기 요청은 안테나 추가·측정 저장·업로드 모두 403
- 화면에 "시연 모드"를 표시한다
- `npm --prefix web run build` 결과를 FastAPI가 같은 주소에서 서빙한다
- `scripts/export_demo.py`: 현재 DB에서 고른 측정만 `demo.db`로 복사

외부 공개 전에 무엇이 어느 주소로 공개되는지 먼저 알려 주고 내 확인을 받아. 방식은 `cloudflared tunnel --url http://localhost:8000`(노트북이 켜져 있어야 함)을 먼저 시도한다.

통과 검사: demo 모드 쓰기 403 테스트, 휴대폰 LTE에서 링크가 열리고 카드가 보임.
