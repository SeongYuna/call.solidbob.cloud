# Requirement: [Task 1]
"""DI 프로바이더 — 포트 ↔ 구현체 결합은 여기서만. 스포크 구현체는 main.py(합성 루트)가
`app.dependency_overrides` 로 꽂는다 — `ai/` 스포크는 import 하지 않는다(`.importlinter` 계약 2).

⚠ 옛 표기 「계약 5」는 `.importlinter` 에 없다(계약은 넷). 이 패키지는 `server/` 안 스포크
(masking·closure_gate·postcall·blacklist)의 **기본 구현을 직접 import 한다** — 2026-09-21 전수 조사."""
