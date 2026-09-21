# Requirement: 7.3절 인터페이스 계약
"""hub — 허브. 7.3절 인터페이스 계약 3종(전사 이벤트·추천 카드·종결 판정)을 DTO 로, 스포크에 요구하는 것을
아웃바운드 포트로 소유한다. 도메인 로직은 없다. `ai/` 스포크를 import 하지 않는다(`.importlinter` 계약 2). ⚠ 옛 표기 「계약 5」는 없는 계약이다 —
`server/` 안 스포크(masking·closure_gate·postcall·blacklist)의 기본 구현은 `dependencies/` 가 직접 import 하고, 그것을 막는 계약은 없다.

계약 변경은 3인 컨펌 + _project/decisions/ 기록이 먼저다 (현재 v2 = decisions/003)."""
