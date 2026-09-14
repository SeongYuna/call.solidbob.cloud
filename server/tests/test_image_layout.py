# Requirement: B-1, [Task 1]
"""합성 루트가 `ai/` 에서 불러오는 파일을 서버 이미지가 **전부** 담는지.

`main.py` 는 스포크를 못 꽂으면 **오류 없이** 501 로 남긴다(`decisions/024`) — 그래서 이미지에서 파일 하나가
빠져도 서버는 정상으로 뜨고 `/health` 의 `spokes` 에서만 티가 난다. 2026-09-11 `0.1.2` 가 `ai/provider.py` 없이
나가 운영 `spokes` 에 `trigger` 가 없었다(Dockerfile 이 `ai/apps/` 만 복사했다). 로컬·CI 에서는 저장소 전체가
있어서 이 결함이 보이지 않는다 — 여기서 Dockerfile 을 직접 읽어 막는다.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO / "infra" / "docker" / "server.Dockerfile"
MAIN = REPO / "server" / "main.py"


def _copied_sources() -> set[str]:
    sources = set()
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*COPY\s+(?!--)(\S+)\s+\S+", line)
        if m:
            sources.add(m.group(1).rstrip("/"))
    return sources


def _is_copied(path: str, sources: set[str]) -> bool:
    return any(path == s or path.startswith(s + "/") for s in sources)


def test_합성_루트가_부르는_ai_모듈이_이미지에_들어간다():
    """`main.py` 가 `ai/` 경로에서 import 하는 최상위 이름마다 이미지에 그 파일·디렉터리가 있어야 한다."""
    main_src = MAIN.read_text(encoding="utf-8")
    sources = _copied_sources()

    # ai/apps 아래 패키지(retrieval 등)는 `COPY ai/apps/` 로, ai/ 바로 아래 모듈(provider)은 따로 복사돼야 한다
    needed = []
    for name in sorted(set(re.findall(r"^\s*from\s+(\w+)(?:\.\w+)*\s+import", main_src, re.M))):
        if (REPO / "ai" / "apps" / name).is_dir():
            needed.append(f"ai/apps/{name}")
        elif (REPO / "ai" / f"{name}.py").is_file():
            needed.append(f"ai/{name}.py")

    assert "ai/provider.py" in needed, "main.py 가 provider 를 부르는지 이 테스트의 전제가 바뀌었다"
    missing = [p for p in needed if not _is_copied(p, sources)]
    assert missing == [], f"server.Dockerfile 이 복사하지 않는 파일: {missing} — 운영에서 스포크가 조용히 빠진다"
