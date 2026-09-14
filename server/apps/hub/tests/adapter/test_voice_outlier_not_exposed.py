# Requirement: D-5, QUA-1
"""부록 A-1 — `robust_z` 는 **저장만 하고 화면으로 내보내지 않는다.** HTTP 표면(inbound adapter)에
그 이름이 나타나는 순간 실패한다. 저장 쪽(`voice_outlier_repository.py`)은 대상이 아니다."""

from pathlib import Path

INBOUND = Path(__file__).resolve().parents[2] / "adapter" / "inbound"


def test_HTTP_표면에_robust_z_가_없다():
    offenders = [p.relative_to(INBOUND) for p in INBOUND.rglob("*.py") if "robust_z" in p.read_text(encoding="utf-8")]
    assert INBOUND.is_dir()
    assert offenders == [], f"robust_z 가 응답 스키마·라우터에 나타났다(부록 A-1): {offenders}"
