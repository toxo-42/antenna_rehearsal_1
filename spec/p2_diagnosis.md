# P2 — 진단 규칙과 판정 카드 (40분)

`src/diagnosis.py`, `guides.py`, `verdict.py`를 만들어 줘. 규칙은 단계별 파일(`rules_none.py`, `rules_offtarget.py`, `rules_unmatched.py`, `rules_common.py`)에 두고, 규칙들이 함께 쓰는 문구·반올림 도구는 `rule_tools.py`에 둔다. 목표 주파수의 X를 구하는 `reactance_at`은 `impedance.py`에 추가한다. 규칙 1개 = 함수 1개, 규칙 목록을 순서대로 실행한다. 결과 항목은 `key, title, evidence, action, guide`.

## 규칙 함수의 형태
- 모든 규칙은 `(ctx: RuleContext) -> Diagnosis | None`. `RuleContext`는 p1의 판정 결과, 스윕, 안테나, cal_mode를 담는 읽기 전용 값이다
- 규칙은 `ctx`만 본다. 다른 규칙의 결과 목록을 보지 않는다. 다른 규칙의 조건이 필요하면(예: other_resonance의 "third_mode가 아니고", uncalibrated의 "positive_s11이 아님") 그 조건을 판정하는 함수를 따로 두고 함께 쓴다
- 결과 목록을 보고 항목을 지우거나 넣는 일은 아래 "배타 규칙" 두 가지와 "폴백" 한 가지뿐이고, 규칙을 모두 실행한 뒤 함수 하나에서 처리한다
- 파일이 300줄을 넘으면 규칙을 단계별 파일(`rules_none.py`, `rules_offtarget.py` 등)로 나누고 `diagnosis.py`에는 규칙 목록과 실행만 둔다
- 표기: status의 수치는 소수 2자리, action의 조정량 %는 정수로 반올림(0.5는 올림). 계산값이 `25.49999999999999`처럼 어긋나도 25.5 %는 26 %가 되도록 p1의 허용 오차를 더해 반올림한다. 반올림 결과가 0이면 "1 % 미만"으로 쓴다
- positive_s11은 S11이 **+0.2 dB를 넘는** 점이 있을 때만 낸다(허용 오차 없이 `> 0.2`). 0 dB 근처의 작은 양수는 잡음이다. 실측에서 교정된 계측기 값은 최대 +0.02 dB, USB 수신값은 +0.07 dB까지 나왔고, 교정이 틀어진 측정은 +1 dB를 넘었다. 기준값은 `models.py`의 상수로 둔다
- 목표 주파수의 X: 목표가 측정점과 정확히 같으면 보간하지 않고 그 점의 X를 쓴다. 결과가 유한하지 않으면 값이 없는 것으로 보고 방향 없는 안내로 간다
- title은 진단을 한 구로 요약하고 원인을 단정하지 않는다 (예: "손실이 있을 수 있음", "급전부가 단락된 것으로 보임")

용어: "목표 공진" = p1의 `selected`. "정합 공진" = `band`가 있는 공진. "다른 공진" = p1의 `others`(목표에 가까운 순). "공진이 여럿이면 첫 번째" = `others` 순서상 첫 번째.

길이 이름: 모노폴 "안테나 도체", 패치 "패치 길이(공진 방향 변)". λ/4(cm) = 7500 / 목표MHz.

## 규칙 (위에서부터)
| key | 조건 | 할 일 |
|---|---|---|
| positive_s11 | S11 > +0.2 dB인 점이 있음 | OSL 교정을 다시 하고 커넥터 체결 확인 후 재측정 |
| feed_short | 급전 공통 조건(아래)이고 low_freq_gamma_real < -0.5 | 테스터로 내심-접지 저항 확인, 납땜 브리지 확인 |
| feed_open | 급전 공통 조건이고 low_freq_gamma_real > 0.5 | 안테나 선과 내심의 납땜 확인, 범위를 넓혀 재측정 |
| feed_fault | 급전 공통 조건이고 low_freq_gamma_real이 None(복소값 없음)이거나 -0.5 이상 0.5 이하 | 내심-접지 저항 확인, 재납땜 |
| lossy | none, -10~-3 dB인 점이 30 % 이상, 다른 공진 없음 | 재납땜, 손·금속에서 띄우고 재측정 |
| length_far | none이고 다른 공진 있음. **목표에 가장 가까운** 공진 사용, ratio = 공진/목표 | ratio < 1이면 줄이기, > 1이면 늘리기. 양 = abs(ratio-1)*100 % |
| weak_fundamental | **모노폴만**, third_mode가 아니고, 판단 공진(목표 공진, 없으면 length_far가 쓸 공진)보다 낮은 **약한 딥**(p1의 `weak_dips`) 중 `판단 공진 / 그 딥`이 2.6 이상 3.4 이하인 것이 있음. 이때 **length_far는 내지 않는다**(3배 자리 공진으로 길이를 계산하면 "184 % 늘리기" 같은 틀린 안내가 나온다) | 급전부 납땜과 안테나 도체가 곧은지 확인한 뒤 재측정. 길이는 아직 바꾸지 말 것 |
| missing_fundamental | **모노폴이고 길이를 입력함**, none, 예상 주파수 ±10 % 안에 약한 딥도 없음, 급전 공통 조건이 아님 | 급전부 납땜과 접지 연결을 확인한 뒤 재측정. 길이는 아직 바꾸지 말 것. 단, 예상 주파수가 스윕 범위 밖이면 "예상 공진 N MHz가 들어가도록 측정 범위를 넓혀 재측정" |
| out_of_range | none, 첫 점 또는 끝 점의 S11이 **모든 내부 점보다 작음**(동점이면 내지 않는다. 평탄한 트레이스는 해당 없음) | 시작·종료 주파수를 넓혀 재측정 |
| too_short / too_long | (offtarget이고 **목표가 대역 밖**) 또는 **길이 우선 조건**, 공진이 목표보다 높음 / 낮음 | abs(offset_pct) % 늘리기 / 줄이기 |
| feed_lead | too_long과 같은 조건 | 노출된 급전선을 짧게 |
| band_edge | offtarget이고 **목표가 대역 안**(p1이 대역 끝과의 여유 부족으로 offtarget을 낸 경우) | 목표 주변을 더 촘촘한 간격으로 재측정. 길이는 아직 바꾸지 말 것 |
| r_low | unmatched, 공진점 R < 30 | 모노폴: 접지판을 λ/4 이상으로, 라디알 추가. 패치: 급전점을 가장자리 쪽으로 |
| r_high | unmatched, 공진점 R > 90 | 모노폴: 접지판과 커넥터 접지의 납땜·접촉 확인. 패치: 급전점을 중심 쪽으로 |
| reactance | unmatched, 30 <= 공진점 R <= 90, **길이 우선 조건이 아님** | 방향은 공진점이 아니라 **목표 주파수의 X**(목표를 사이에 둔 두 측정점의 X를 선형 보간)로 정한다. X > 0이면 줄이기, X < 0이면 늘리기 미세 조정. X = 0이거나 목표가 스윕 범위 밖이면 방향 없이 "더 촘촘한 간격으로 재측정" |
| match_unknown | unmatched, 복소값 없음 | 복소값이 있는 측정으로 다시, 접지판과 납땜 확인 |
| common_mode | unmatched | 케이블을 잡아 보고 변하면 접지판 확대·페라이트 |
| third_mode | **모노폴만**, 목표 공진이 있고(단계 무관), 그보다 낮은 공진(**정합 여부 무관**. 얕은 공진도 기본 공진으로 본다) 중 `목표 공진 / 그 공진`이 2.6 이상 3.4 이하인 것이 있음. evidence에는 그중 첫 번째 | 기본 모드로 맞추려면 도체를 약 1/3로. 확신 없이 자르지 말 것 |
| other_resonance | third_mode가 아니고, 다른 정합 공진이 있음. **length_far에 쓴 공진은 제외. 모노폴이면 기준 주파수(목표 공진, 없으면 weak_fundamental의 약한 딥)의 2.6~3.4배 자리와 4.5~5.5배 자리 공진도 제외**(안테나 자신의 3배·5배 모드이지 케이블 문제가 아니다. 실측 비는 3배 2.75~3.17, 5배 4.82~5.01). 남은 것이 여럿이면 evidence에는 첫 번째 | 케이블 위치를 바꾸거나 페라이트 후 재측정 |
| narrow | narrow | 모노폴: 도체를 굵게. 패치: 기판을 두껍게 또는 유전율 낮게 |
| good | good | 손·케이블 위치를 바꿔도 유지되는지 확인하고 저장 |
| uncalibrated | cal_mode가 unknown이고 positive_s11이 아님 | 수치는 경향 참고용. 교정된 측정으로 다시 확인 (USB로 받은 값에는 장비의 교정이 반영되지 않는다) |

길이 우선 조건: unmatched **이고** abs(offset_pct) >= 5 % **이고** 공진과 목표의 거리가 측정 간격 한 칸 이상(공진점 양옆 두 간격 중 넓은 쪽. 정확히 한 칸이면 해당). 5 %는 임시값이고 `LENGTH_FIRST_PCT` 상수 하나로 둔다. 이 조건이면 얕은 공진이라도 too_short / too_long(too_long이면 feed_lead도)을 먼저 내고, 정합 점검(r_low, r_high, match_unknown, common_mode)은 그 뒤에 함께 낸다. 방향을 말하는 규칙이 둘이 되지 않게 reactance는 내지 않는다. 목표가 스윕 범위 밖이어도 같다. (이전에는 딥이 -10 dB보다 얕으면 목표에서 10 % 벗어나도 정합 점검만 안내했다)

길이를 입력한 모노폴(p1의 예상 주파수 기준 선택): none이면 다른 자리의 공진으로 길이를 계산하지 않으므로 **length_far를 내지 않는다**. 예상 주파수 ±10 % 안에 약한 딥이 있으면 weak_fundamental(evidence: "길이 L cm의 예상 공진 F MHz 근처에 얕은 딥 … 만 있음", 3배 비는 보지 않는다), 없으면 missing_fundamental(evidence: "길이 L cm의 예상 공진 F MHz 근처(low~high MHz)에 공진이 없음"). 카드 status에는 공진 줄 다음에 "예상 공진 F MHz (도체 길이 L cm)"를 넣고, 공진이 없을 때의 줄은 "예상 주파수 근처에 공진 없음"으로 쓴다. missing_fundamental이 나오면 headline은 "이 길이라면 있어야 할 공진이 보이지 않습니다". 검사: 길이 37.5 cm(예상 200 MHz), 목표 200. 200 MHz에 -4 dB, 400 MHz에 -20 dB → weak_fundamental 하나. 400 MHz 공진만 → missing_fundamental 하나(180~220 MHz). 평탄한 0 dB → feed_fault 하나. 길이 7.5 cm(예상 1000 MHz)인데 스윕이 800 MHz에서 끝남 → 범위를 넓히라는 action. 실측 `monopole_12cm.csv`, 목표 433, 길이 12 → unmatched, too_short(약 44 % 늘리기), match_unknown, common_mode

급전 공통 조건: none **이고** -1 dB보다 큰 점이 90 % 이상 **이고** 다른 공진 없음. 세 가지를 모두 만족한 뒤에만 low_freq_gamma_real로 feed_short / feed_open / feed_fault를 가른다. 크기만 있는 스윕이라도 공통 조건을 만족하지 않으면 feed_fault를 내지 않는다.

배타 규칙: positive_s11이 나오면 그것만 낸다. feed_* 또는 lossy가 나오면 out_of_range는 내지 않는다.
폴백: uncalibrated를 빼고 결과가 비어 있으면 `no_resonance`(할 일: 범위를 넓히고 점 수를 늘려 재측정, 납땜과 연결 확인)를 맨 앞에 넣는다.
길이를 바꾸라는 action(length_far, too_short, too_long, 방향이 있는 reactance, third_mode)에는 항상 주의 문구를 넣는다. 줄이는 방향이면 "초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정", **늘리는 방향이면 "초기 추정. 한 번에 절반씩, 자르지 말고 덧붙여서 확인"**(늘리라는 안내에 "자르기 전에"가 붙으면 학생도 LLM도 자르라는 말로 읽는다). feed_lead에는 넣지 않는다. 늘리는 action과 줄이는 action의 문구가 다른지 테스트한다.

## guide 문장 (그대로 사용. 화면에 기본으로 보여 주는 설명이다)
값이 객체인 key(`length_far`, `too_short`, `too_long`, `r_low`, `r_high`, `narrow`)는 안테나 종류로 문장을 고른다.
문장은 원인을 단정하지 않는다. 이 측정만으로 확정할 수 없는 것은 "~일 수 있다"로 쓴다.
```json
{"positive_s11":"수동 안테나는 들어온 것보다 큰 신호를 되돌려 보낼 수 없으므로, 그런 값이 나오면 교정이나 연결이 잘못된 것이다.",
"feed_short":"신호선과 접지가 서로 닿으면 신호가 안테나로 가지 못하고 거의 모두 되돌아온다.",
"feed_open":"신호선이 안테나에 전기적으로 붙어 있지 않으면 신호가 끊어진 곳에서 거의 모두 되돌아온다.",
"feed_fault":"안테나가 전기적으로 연결되지 않으면 모든 주파수에서 신호가 거의 모두 되돌아온다.",
"lossy":"접촉이 나쁘거나 손이나 금속이 가까우면 신호가 열로 사라져서, 뚜렷한 골짜기 없이 넓은 범위에서 반사가 조금씩 줄어든다.",
"length_far":{"monopole":"안테나 도체가 길수록 공진 주파수는 낮아지고 짧을수록 높아진다.",
  "patch":"패치의 공진 방향 변이 길수록 공진 주파수는 낮아지고 짧을수록 높아진다."},
"out_of_range":"반사가 가장 작은 지점이 측정 범위의 끝에 있으면 진짜 공진은 측정 범위 밖에 있을 수 있다.",
"too_short":{"monopole":"도체가 짧으면 공진 주파수가 목표보다 높아진다.",
  "patch":"패치의 공진 방향 변이 짧으면 공진 주파수가 목표보다 높아진다."},
"too_long":{"monopole":"도체가 길면 공진 주파수가 목표보다 낮아진다.",
  "patch":"패치의 공진 방향 변이 길면 공진 주파수가 목표보다 낮아진다."},
"feed_lead":"급전부의 노출된 선이 길거나 납땜 덩어리가 크면 공진 주파수가 낮아진다.",
"band_edge":"측정 점 사이가 넓으면 대역의 끝이 어디인지 정확히 알 수 없어서, 목표가 대역 끝에 가까우면 대역 안에 있다고 확신할 수 없다.",
"r_low":{"monopole":"접지판이 작으면 공진은 보이지만 안테나의 입력 저항이 낮아져 신호가 잘 들어가지 않는다.",
  "patch":"패치는 급전점이 중심에 가까울수록 입력 저항이 낮아져, 너무 안쪽이면 신호가 잘 들어가지 않는다."},
"r_high":{"monopole":"접지 연결의 접촉이 나쁘면 안테나의 입력 저항이 높아져 신호가 잘 들어가지 않는다.",
  "patch":"패치는 급전점이 가장자리에 가까울수록 입력 저항이 높아져, 너무 바깥쪽이면 신호가 잘 들어가지 않는다."},
"reactance":"저항이 알맞아도 남은 리액턴스가 있으면 신호 일부가 되돌아온다.",
"match_unknown":"공진은 있지만 정합이 얕고, 저항과 리액턴스 중 어느 쪽이 원인인지는 이 데이터로 나눌 수 없다.",
"common_mode":"케이블 바깥면에 전류가 흐르면 케이블도 안테나처럼 동작해서, 손으로 잡거나 위치를 바꾸면 측정값이 달라진다.",
"third_mode":"목표 근처에서 보인 공진은 기본 공진이 아니라 더 높은 주파수에서 다시 나타난 공진일 수 있다.",
"weak_fundamental":"모노폴은 기본 공진의 약 3배 주파수에서 다시 공진한다. 급전부 연결이 나쁘거나 도체가 휘면 기본 공진이 얕아져서 3배 자리 공진만 뚜렷하게 보일 수 있다.",
"missing_fundamental":"모노폴은 도체 길이가 파장의 약 1/4이 되는 주파수에서 공진한다. 그 자리에 공진이 없으면 길이보다 급전부나 접지 연결을 먼저 의심한다.",
"other_resonance":"안테나가 아닌 케이블이나 접지판도 다른 주파수에서 공진할 수 있다.",
"narrow":{"monopole":"도체가 가늘면 잘 동작하는 주파수 폭이 좁아진다.",
  "patch":"기판이 얇거나 유전율이 높으면 잘 동작하는 주파수 폭이 좁아진다."},
"no_resonance":"이 측정에서는 반사가 뚜렷하게 줄어드는 골짜기가 보이지 않는다. 공진이 측정 범위 밖에 있거나 너무 얕아서 드러나지 않았을 수 있다.",
"good":"목표 주파수에서 반사가 작고 동작하는 폭도 충분하다.",
"uncalibrated":"교정을 확인하지 않으면 케이블과 커넥터의 영향이 측정값에 섞인다."}
```

## 기대 key 순서 (cal_mode = vna)
| 합성 이름 | keys |
|---|---|
| good | good |
| offtarget_low | too_long, feed_lead |
| offtarget_high | too_short |
| narrow | narrow |
| unmatched_low_r | r_low, common_mode |
| unmatched_high_r | r_high, common_mode |
| far_low | length_far (36 % 줄이기) |
| far_high | length_far (61 % 늘리기) |
| open / short / lossy / positive | feed_open / feed_short / lossy / positive_s11 |
| two_res | length_far (881.2 MHz, 36 % 늘리기), other_resonance (277.3 MHz) |
| third_mode | r_low, common_mode, third_mode |
| patch_good | good |
| patch_narrow | narrow (action에 "기판") |
| patch_low_r | r_low (action에 "가장자리"), common_mode |
| patch_high_r | r_high (action에 "중심"), common_mode |

cal_mode = unknown이면 positive를 뺀 모든 경우의 끝에 uncalibrated가 붙는다.

## 카드
`stage, headline, status, diagnoses, remeasure`. 직렬화한 모양은 `contract/measurement.json`의 `card`와 같아야 한다.
- stage: p1의 단계 값 그대로. 단, positive_s11이 나오면 `invalid`. 카드의 stage 값은 `none | unmatched | offtarget | narrow | good | invalid` (`invalid`는 카드에만 있고 p1의 단계에는 없다)
- headline: 단계별 한 문장이고 아래 문장을 그대로 쓴다. `none` "목표 근처에서 공진을 찾지 못했습니다", `unmatched` "공진은 있지만 정합이 얕습니다", `offtarget` "공진은 있지만 목표 주파수에 맞지 않습니다", `narrow` "목표에서 공진하지만 대역이 좁습니다", `good` "목표 주파수에서 잘 동작합니다". 단, positive_s11이 나오면 단계 문장 대신 "측정값이 올바르지 않아 판정할 수 없다"는 뜻의 문장을 쓴다 (p1 단계가 good이어도 합격으로 보이지 않게). band_edge가 나오면 stage는 `offtarget` 그대로 두고, 단계 문장 대신 "목표가 대역 끝에 가까워 이 측정 간격으로는 확정할 수 없다"는 뜻의 문장을 쓴다 (공진이 목표와 같은데 "맞지 않는다"고 하지 않게). 길이 우선 조건이면 stage는 `unmatched` 그대로 두고 "공진이 목표 주파수에서 벗어나 있고 정합도 얕습니다"를 쓴다
- status: 공진·목표 차이·깊이·대역, 공진점 R/X, 교정 상태와 측정 간격
  - 값이 없는 항목은 줄을 내지 않는다 (unmatched의 대역, 복소값 없는 스윕의 R/X, R이나 X가 유한하지 않은 경우의 R/X. 반사계수가 정확히 1이면 R이 무한대다). 이때 `r_high`의 evidence는 숫자 대신 "공진점 R 무한대"로 쓴다. 카드의 어떤 문자열에도 `inf`, `nan`이 나오지 않는다
  - 목표 공진이 없으면 공진 줄 대신 "목표 근처에 공진 없음"을 낸다. 다른 공진의 수치는 status에 쓰지 않고 해당 진단의 evidence에만 쓴다
  - 측정 간격: 인접 점 간격의 최솟값과 최댓값이 소수 2자리 표기로 같으면 하나만, 다르면 "최소~최대 MHz"
- remeasure: 공진을 잰 점이 부족할 때의 재측정 안내. 없으면 `null`, 있으면 `{start_mhz, stop_mhz, note}` (`src/rules_step.py`). 진단 규칙이 아니므로 diagnoses와 guide 목록에는 넣지 않는다
  - 조건: 목표 공진이 있고, positive_s11이 아니고, `공진 폭 / 공진점 간격 < 5`. 공진 폭은 정합 대역이 있으면 그 폭, 없으면 통상 대역폭(모노폴 8 %, 패치 2.5 %) × 공진 주파수. 공진점 간격은 공진점 양옆 두 간격 중 넓은 쪽. 정확히 5이면 해당 없음
  - 범위: 공진 주파수의 ±20 %를 정수 MHz로 반올림. 장비 한도로 자르지 않는다(측정할 때 장비 쪽 검사가 알려 준다)
  - note: "측정 점이 성겨서 공진 주파수와 S11 값이 정확하지 않을 수 있습니다 (공진 근처 간격 a MHz, 공진 폭 약 b MHz). s~e MHz 범위로 좁혀서 다시 측정해 보세요." 길이 방향 낱말(늘리, 줄이, 자르, 덧붙)을 쓰지 않는다
  - 점 사이의 바닥을 계산으로 추정하지 않는다(점이 4개뿐이면 추정값도 믿기 어렵고, 추정값이 -10 dB 기준을 넘나들면 판정이 흔들린다). 프로그램이 자동으로 다시 측정하지도 않는다
  - 화면(p4): 카드에 note를 보여 주고, 측정 탭이 있을 때만 "이 범위를 USB 측정 칸에 채우기" 버튼을 둔다. 버튼은 시작·종료 칸만 채우고 측정 탭으로 옮긴다(점 개수는 그대로, 측정은 학생이 누른다). 이 칸이 생기기 전에 저장된 카드에는 `remeasure`가 없을 수 있다
  - 검사: 500~700 MHz 5 MHz 간격, 595~605 MHz 대역 → 480~720. 2 MHz 간격에 594~606 MHz 대역(6칸) → null. 420 MHz -8 dB 딥(대역 없음, 모노폴): 10 MHz 간격 → 336~504, 6 MHz 간격 → null. 패치 400 MHz 딥: 2 MHz 간격(정확히 5칸) → null, 2.1 MHz → 있음. 목표 공진 없음 → null. 첫 점 +0.3 dB → null

## 통과 검사
위 표 전체와 unknown 경우 테스트 통과. 기대값은 고치지 마.
합성 샘플로는 발동하지 않는 규칙은 스윕을 직접 만들어 테스트한다:
- 양성: feed_fault(복소값 없음 / 사이 값), out_of_range, reactance(목표점 X가 양·음·0), match_unknown, band_edge, no_resonance
- 음성: 평탄한 트레이스는 out_of_range 아님. 공통 조건을 못 채운 크기 전용 스윕은 feed_fault 아님
- 경계: 공진점 R = 30, 90은 reactance. 모드 비 2.6, 3.4는 third_mode. low_freq_gamma_real = ±0.5는 feed_fault
- reactance 방향: `rlc(425, 50, 36)`, 400/430/460 MHz, 목표 420 MHz → 늘리기 (공진점 430 MHz의 X는 양수지만 400~430 MHz 사이를 보간한 목표점 X는 음수)
- 길이 우선: 400~440 MHz 10 MHz 간격, 420 MHz에 -8 dB 딥. 목표 400(+5 %) → too_short, match_unknown, common_mode. 목표 401(+4.74 %) → match_unknown, common_mode. 400/430/460 MHz, 430 MHz 딥, 목표 409(+5.13 %지만 21 MHz < 한 칸 30 MHz) → 길이 조언 없음, 목표 400(정확히 한 칸) → too_short. `rlc(425, 50, 36)`, 400/430/460 MHz: 목표 400 → too_short, common_mode / 목표 460 → too_long, feed_lead, common_mode (reactance 없음) / 목표 420 → reactance, common_mode (그대로)
- reactance의 "목표가 스윕 범위 밖" 사례는 5 % 안쪽에서 확인한다: 400/430/440 MHz, 430 MHz 딥, 목표 445
- weak_fundamental: 100~800 MHz 10 MHz 간격, 200 MHz에 -4 dB 딥, 600 MHz에 -20 dB 딥. 모노폴 목표 200 → weak_fundamental 하나(length_far 없음), 목표 600 → weak_fundamental, narrow. 비 2.6, 3.4는 해당, 2.55, 3.45는 length_far. 200 MHz 딥이 -1.9 dB(약한 딥 아님)이거나 딥이 없거나 패치이면 length_far
- 3배 모드: 200 MHz에 -8 dB, 600 MHz에 -20 dB, 목표 600 → third_mode, narrow. 둘 다 -20 dB이고 목표 200 → narrow 하나(other_resonance 없음), 500 MHz 공진이 더 있으면 other_resonance(500 MHz). 5배 자리: 200 MHz와 900 MHz(4.5배) 또는 1100 MHz(5.5배) → narrow 하나, 880 MHz(4.4배)나 1120 MHz(5.6배) → other_resonance, narrow
- positive_s11 + good: 400/433/466 MHz, +0.3/-30/0 dB, 목표 433 MHz → 카드 stage는 `invalid`, diagnoses는 positive_s11 하나, headline은 합격 문장이 아님
- 작은 양수는 정상 판정: 같은 스윕에서 첫 점이 +0.1 dB이면 positive_s11이 없고 stage는 p1의 단계 그대로. 정확히 +0.2 dB도 positive_s11이 아님

실측 파일(`tests/data/`, 목표와 종류는 p1의 실측 표와 같음)의 key 순서. cal_mode = unknown이면 끝에 uncalibrated가 붙는다.

| 파일 (목표 MHz) | 카드 stage | key 순서 |
|---|---|---|
| monopole_5cm.csv (1350) | good | other_resonance, good |
| monopole_11.5cm.csv (650) | unmatched | match_unknown, common_mode |
| monopole_12cm.csv (625) | unmatched | match_unknown, common_mode |
| monopole_12cm.csv (433) | none | length_far, other_resonance |
| monopole_14cm.csv (535) | narrow | narrow |
| saa2_patch_2450.csv (2450) | good | good |
| monopole_12cm.csv (690) | unmatched | too_long, feed_lead, match_unknown, common_mode |
| monopole_12cm.csv (560) | unmatched | too_short, match_unknown, common_mode |
| monopole_12cm.csv (1834) | narrow | third_mode, narrow |
| monopole_10cm_weak.csv (750) | none | weak_fundamental |

(11.5 cm, 12 cm 파일의 3배 자리 공진 1894, 1834 MHz는 이전에는 other_resonance로 "케이블·페라이트" 안내가 나왔다. 14 cm 파일의 1575 MHz(3배 자리)와 2631 MHz(5배 자리)도 같다)

(모노폴 파일은 모두 첫 점이 +0.001~+0.007 dB다. 이 때문에 `invalid`가 되면 안 된다)
- 조정량이 0으로 반올림되면 "1 % 미만"
- `offtarget_low`를 `cal_mode = vna`로 판정한 카드가 `contract/measurement.json`의 `card`와 글자까지 일치
