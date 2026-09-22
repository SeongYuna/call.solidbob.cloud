# Requirement: SEC-2, QUA-1
"""쓰기 경로를 부르는 라우터 테스트의 서비스 토큰.

그 문(`require_ingest_service`)은 2026-09-22 부터 **토큰이 없으면 닫힌다**(`decisions/120` 「전환 순서」 4번).
전에는 미설정이면 열려서 라우터 테스트가 헤더 없이 통과했다. 문 자체는 `tests/test_main_ingest_guard.py` 가 보고,
여기를 쓰는 테스트들은 **문을 지난 뒤의 동작**을 본다 — 환경변수는 같은 폴더 `conftest.py` 가 넣는다.
"""

TOKEN = "ingest-token-for-router-tests"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
