# 브리핑 대본 고객 셋 — `dasan-briefing`

> 근거: [`decisions/220`](../../../_project/decisions/) (F-3 통화 수신 전 고객 브리핑). `source: synthetic` — 가짜 번호·가짜 상황이다.

고객 셋이 각자 **지난 통화 → 이번 통화** 두 건을 갖는다. 이번 통화의 벨이 울리는 동안(`--ring-seconds`) 서버가 만든 브리핑의
**목적 범주**가 대본 작성자가 적은 라벨과 같은지 글자 비교로 채점한다(규칙 채점, 절대 원칙 1).

| 고객 | 번호 | 지난 통화 | 이번 통화 | 정답 목적 | 지난 통화에서 남는 사실 |
|---|---|---|---|---|---|
| A | `01000000301` | SYN-301 초본 대리 발급(4.3) — 위임장만 안내 | SYN-302 | 서류 보완 | closure `incomplete`(신분증 누락) |
| B | `01000000302` | SYN-303 단수 지연 불만(톤 raised, 욕설 없음) | SYN-304 | 컴플레인 | follow_up_action(「회신드리겠습니다」) |
| C | `01000000303` | SYN-305 외국인 여권 재발급(4.23) | SYN-306 | 후속 확인 | follow_up_action(「문자로 안내드리겠습니다」) |

- **정답 라벨은 대본 작성자가 쓴 상한이다.** 브리핑을 한 번도 돌리기 전에 적었고(커밋 순서가 증거다), 일반 성능이 아니다 — 측정 불가.
- 브리핑은 이번 통화의 첫 고객 발화를 **보지 못한다**(벨 시간에 만든다). 지난 통화 사실만으로 맞혀야 한다.
- 폭언·성적 표현 없음(`decisions/209` 4항). B 의 `raised` 는 톤일 뿐이라 call_guard 플래그는 생기지 않는 것이 정상이다.
- 발신 번호는 회차마다 `briefing_check.py` 가 환경변수 `CALLER_PHONE` 으로 바꿔 끼운다 — 앞 회차 통화가 지난 통화로 섞이지 않게 한다.

```bash
.venv/bin/python scripts/persona_sim/briefing_check.py --core-url http://localhost:8001 \
    --mediator-url ws://localhost:8081 --repeat 3 --ring-seconds 15
# 결과: data/processed/briefing/briefing-check-<시각>.json
```
