# P2 — 진단 규칙과 판정 카드 (40분)

`src/diagnosis.py`, `guides.py`, `verdict.py`를 만들어 줘. 규칙 1개 = 함수 1개, 규칙 목록을 순서대로 실행한다. 결과 항목은 `key, title, evidence, action, guide`.

## 규칙 함수의 형태
- 모든 규칙은 `(ctx: RuleContext) -> Diagnosis | None`. `RuleContext`는 p1의 판정 결과, 스윕, 안테나, cal_mode를 담는 읽기 전용 값이다
- 규칙은 `ctx`만 본다. 다른 규칙의 결과 목록을 보지 않는다. 다른 규칙의 조건이 필요하면(예: other_resonance의 "third_mode가 아니고", uncalibrated의 "positive_s11이 아님") 그 조건을 판정하는 함수를 따로 두고 함께 쓴다
- 결과 목록을 보고 항목을 지우거나 넣는 일은 아래 "배타 규칙" 두 가지와 "폴백" 한 가지뿐이고, 규칙을 모두 실행한 뒤 함수 하나에서 처리한다
- 파일이 300줄을 넘으면 규칙을 단계별 파일(`rules_none.py`, `rules_offtarget.py` 등)로 나누고 `diagnosis.py`에는 규칙 목록과 실행만 둔다
- 표기: status의 수치는 소수 2자리, action의 조정량 %는 정수로 반올림. 반올림 결과가 0이면 "1 % 미만"으로 쓴다

용어: "목표 공진" = p1의 `selected`. "정합 공진" = `band`가 있는 공진. "다른 공진" = p1의 `others`(목표에 가까운 순). "공진이 여럿이면 첫 번째" = `others` 순서상 첫 번째.

길이 이름: 모노폴 "안테나 도체", 패치 "패치 길이(공진 방향 변)". λ/4(cm) = 7500 / 목표MHz.

## 규칙 (위에서부터)
| key | 조건 | 할 일 |
|---|---|---|
| positive_s11 | S11 > 0 dB인 점이 있음 | OSL 교정을 다시 하고 커넥터 체결 확인 후 재측정 |
| feed_short | 급전 공통 조건(아래)이고 low_freq_gamma_real < -0.5 | 테스터로 내심-접지 저항 확인, 납땜 브리지 확인 |
| feed_open | 급전 공통 조건이고 low_freq_gamma_real > 0.5 | 안테나 선과 내심의 납땜 확인, 범위를 넓혀 재측정 |
| feed_fault | 급전 공통 조건이고 low_freq_gamma_real이 None(복소값 없음)이거나 -0.5 이상 0.5 이하 | 내심-접지 저항 확인, 재납땜 |
| lossy | none, -10~-3 dB인 점이 30 % 이상, 다른 공진 없음 | 재납땜, 손·금속에서 띄우고 재측정 |
| length_far | none이고 다른 공진 있음. **목표에 가장 가까운** 공진 사용, ratio = 공진/목표 | ratio < 1이면 줄이기, > 1이면 늘리기. 양 = abs(ratio-1)*100 % |
| out_of_range | none, 첫 점 또는 끝 점의 S11이 **모든 내부 점보다 작음**(동점이면 내지 않는다. 평탄한 트레이스는 해당 없음) | 시작·종료 주파수를 넓혀 재측정 |
| too_short / too_long | offtarget, **목표가 대역 밖**, 공진이 목표보다 높음 / 낮음 | abs(offset_pct) % 늘리기 / 줄이기 |
| feed_lead | too_long과 같은 조건 | 노출된 급전선을 짧게 |
| band_edge | offtarget이고 **목표가 대역 안**(p1이 대역 끝과의 여유 부족으로 offtarget을 낸 경우) | 목표 주변을 더 촘촘한 간격으로 재측정. 길이는 아직 바꾸지 말 것 |
| r_low | unmatched, 공진점 R < 30 | 모노폴: 접지판을 λ/4 이상으로, 라디알 추가. 패치: 급전점을 가장자리 쪽으로 |
| r_high | unmatched, 공진점 R > 90 | 모노폴: 접지판과 커넥터 접지의 납땜·접촉 확인. 패치: 급전점을 중심 쪽으로 |
| reactance | unmatched, 30 <= 공진점 R <= 90 | 방향은 공진점이 아니라 **목표 주파수의 X**(목표를 사이에 둔 두 측정점의 X를 선형 보간)로 정한다. X > 0이면 줄이기, X < 0이면 늘리기 미세 조정. X = 0이거나 목표가 스윕 범위 밖이면 방향 없이 "더 촘촘한 간격으로 재측정" |
| match_unknown | unmatched, 복소값 없음 | 복소값이 있는 측정으로 다시, 접지판과 납땜 확인 |
| common_mode | unmatched | 케이블을 잡아 보고 변하면 접지판 확대·페라이트 |
| third_mode | **모노폴만**, 목표 공진이 있고(단계 무관), 그보다 낮은 정합 공진 중 `목표 공진 / 그 공진`이 2.6 이상 3.4 이하인 것이 있음. evidence에는 그중 첫 번째 | 기본 모드로 맞추려면 도체를 약 1/3로. 확신 없이 자르지 말 것 |
| other_resonance | third_mode가 아니고, 다른 정합 공진이 있음. **length_far에 쓴 공진은 제외**. 남은 것이 여럿이면 evidence에는 첫 번째 | 케이블 위치를 바꾸거나 페라이트 후 재측정 |
| narrow | narrow | 모노폴: 도체를 굵게. 패치: 기판을 두껍게 또는 유전율 낮게 |
| good | good | 손·케이블 위치를 바꿔도 유지되는지 확인하고 저장 |
| uncalibrated | cal_mode가 unknown이고 positive_s11이 아님 | 본체 OSL 교정 후 같은 조건으로 재측정 |

급전 공통 조건: none **이고** -1 dB보다 큰 점이 90 % 이상 **이고** 다른 공진 없음. 세 가지를 모두 만족한 뒤에만 low_freq_gamma_real로 feed_short / feed_open / feed_fault를 가른다. 크기만 있는 스윕이라도 공통 조건을 만족하지 않으면 feed_fault를 내지 않는다.

배타 규칙: positive_s11이 나오면 그것만 낸다. feed_* 또는 lossy가 나오면 out_of_range는 내지 않는다.
폴백: uncalibrated를 빼고 결과가 비어 있으면 `no_resonance`(할 일: 범위를 넓히고 점 수를 늘려 재측정, 납땜과 연결 확인)를 맨 앞에 넣는다.
길이 조정 문구에는 항상 "초기 추정, 한 번에 절반씩, 자르기 전에 다시 측정"을 넣는다.

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
`stage, headline, status, diagnoses`. 직렬화한 모양은 `contract/measurement.json`의 `card`와 같아야 한다.
- stage: p1의 단계 값 그대로. 단, positive_s11이 나오면 `invalid`. 카드의 stage 값은 `none | unmatched | offtarget | narrow | good | invalid` (`invalid`는 카드에만 있고 p1의 단계에는 없다)
- headline: 단계별 한 문장. 단, positive_s11이 나오면 단계 문장 대신 "측정값이 올바르지 않아 판정할 수 없다"는 뜻의 문장을 쓴다 (p1 단계가 good이어도 합격으로 보이지 않게). band_edge가 나오면 stage는 `offtarget` 그대로 두고, 단계 문장 대신 "목표가 대역 끝에 가까워 이 측정 간격으로는 확정할 수 없다"는 뜻의 문장을 쓴다 (공진이 목표와 같은데 "맞지 않는다"고 하지 않게)
- status: 공진·목표 차이·깊이·대역, 공진점 R/X, 교정 상태와 측정 간격
  - 값이 없는 항목은 줄을 내지 않는다 (unmatched의 대역, 복소값 없는 스윕의 R/X)
  - 목표 공진이 없으면 공진 줄 대신 "목표 근처에 공진 없음"을 낸다. 다른 공진의 수치는 status에 쓰지 않고 해당 진단의 evidence에만 쓴다
  - 측정 간격: 인접 점 간격의 최솟값과 최댓값이 소수 2자리 표기로 같으면 하나만, 다르면 "최소~최대 MHz"

## 통과 검사
위 표 전체와 unknown 경우 테스트 통과. 기대값은 고치지 마.
합성 샘플로는 발동하지 않는 규칙은 스윕을 직접 만들어 테스트한다:
- 양성: feed_fault(복소값 없음 / 사이 값), out_of_range, reactance(목표점 X가 양·음·0), match_unknown, band_edge, no_resonance
- 음성: 평탄한 트레이스는 out_of_range 아님. 공통 조건을 못 채운 크기 전용 스윕은 feed_fault 아님
- 경계: 공진점 R = 30, 90은 reactance. 모드 비 2.6, 3.4는 third_mode. low_freq_gamma_real = ±0.5는 feed_fault
- reactance 방향: `rlc(425, 50, 36)`, 400/430/460 MHz, 목표 420 MHz → 늘리기 (공진점 430 MHz의 X는 양수지만 400~430 MHz 사이를 보간한 목표점 X는 음수)
- positive_s11 + good: 400/433/466 MHz, +0.1/-30/0 dB, 목표 433 MHz → 카드 stage는 `invalid`, diagnoses는 positive_s11 하나, headline은 합격 문장이 아님
- 조정량이 0으로 반올림되면 "1 % 미만"
- 카드 직렬화 key가 `contract/measurement.json`의 `card`와 일치
