# Requirement: J-3, J-5, C-6
"""관리자 현황판 건수 — 전부 셀 수 있는 누적 건수다. **상담원 단위로 쪼개지 않는다**(부록 A-1).

점수·비율을 서버가 만들지 않는다 — 비중은 화면이 이 건수로 그린다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class AdminStats:
    calls_total: int            # 시작된 통화 전체
    calls_closed: int           # `/close` 로 닫힌 통화(`status='closed'`, 09-20 부터 쓰인다 — 그 전 통화는 안 닫혀 있다)
    call_guard_flags: int       # 콜 가드(C-6) 신호 전체
    pending_requests: int       # 결정 대기 블랙리스트 요청
    active_entries: int         # 적용 중 블랙리스트 등록(해제 안 됨 · 만료 전)
    routing_decisions: int      # J-5 배정 판정 전체(`routing_log`)
    routing_blacklisted: int    # 그중 블랙리스트 고객
    routing_fell_back: int      # 그중 베테랑이 없어 일반 배정으로 떨어진 건
    counted_at: datetime        # DB 가 센 시각 — 화면의 숫자가 «언제» 값인지
    # 오늘(KST) 칸 — 누적만으로는 「오늘 통화 N건」을 못 읽는다(09-22 운영: 누적 14 중 10건이 09-11~15 테스트, w6-admin-stats-today)
    calls_today: int = 0             # 오늘 시작된 통화
    call_guard_flags_today: int = 0  # 오늘 잡힌 콜 가드 신호
    requests_today: int = 0          # 오늘 올라온 블랙리스트 요청(상태 무관)
    today: date | None = None        # 「오늘」이 어느 날인지(KST) — DB 시각 기준
