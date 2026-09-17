# Requirement: [Task 1], SEC-2
"""배포 태그가 올바른지 본다 — 「코드가 바뀌었는데 newTag 가 그대로」를 막는다.

`release.yml`(머지 후)과 `tag-check.yml`(PR)이 **같은 판정**을 쓰도록 여기 한 곳에 둔다.
전에는 이 로직이 `release.yml` 안의 셸 함수였고, PR 쪽에 같은 것을 복사하면 둘이 조용히
어긋난다 — 이 저장소는 브랜치·job·룰셋 이름을 따로 고치다 두 번 어긋난 이력이 있다.

## 왜 필요한가

파드가 `imagePullPolicy: IfNotPresent` 라, 코드를 고치고도 `newTag` 를 그대로 두면
같은 태그로 다시 구워도 **노드가 캐시된 옛 이미지를 계속 쓴다.** 배포는 초록인데 옛 코드가
돈다. 그래서 그 조합을 빨간불로 만든다.

## fail-closed (2026-09-14)

전에는 `docker manifest inspect` 의 **모든** 비정상 종료를 「태그 없음」으로 접었다.
레이트 리밋·5xx·비공개 저장소(2026-09-11 콜 미디에이터가 실제로 그랬다)·타임아웃이 전부
「없음」이 되고, 그러면 게이트가 **조용히 통과**한 뒤 같은 태그를 덮어 구워 위의 사고가
그대로 난다 — 빨간불이 아니라 초록으로 샌다.

여기서는 셋을 가른다: **200 = 있음 · 404 = 없음 · 그 외 = 판정 불가.**
판정 불가면 종료 코드 2 로 죽는다. 못 미더운 초록보다 멈추는 쪽이 낫다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

AUTH_URL = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
MANIFEST_URL = "https://registry-1.docker.io/v2/{repo}/manifests/{tag}"
ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    )
)

# 이미지마다 «그 이미지에 실제로 들어가는 경로»만 본다. server.Dockerfile 의 COPY 집합과 같아야 한다.
# 예전엔 server 가 `infra/docker/` 전체를 봐서 call-mediator.Dockerfile 만 고쳐도 server 변경으로 잡혔다.
IMAGES = {
    "server": {
        "image": "seongyuna/callguard-server",
        "paths": re.compile(r"^(server/|ai/|infra/docker/server\.Dockerfile|\.dockerignore)"),
        "output": "build",
    },
    # 콜 미디에이터 이미지는 src/ 와 package*.json 만 담는다(call-mediator.Dockerfile) — test/·README 는 태그를 올릴 일이 아니다.
    "call-mediator": {
        "image": "seongyuna/callguard-call-mediator",
        "paths": re.compile(
            r"^(services/call-mediator/(src/|package(-lock)?\.json)|infra/docker/call-mediator\.Dockerfile|\.dockerignore)"
        ),
        "output": "call_mediator_build",
    },
    # ES(nori 포함). 2026-09-15 추가 — 전에는 CI 가 이 이미지를 아예 몰라서 갈래 둘이 뚫려 있었다:
    #  ① Dockerfile 을 고쳐도 release.yml 의 paths 에 없어 워크플로가 깨어나지 않았다
    #  ② newTag 만 올리면 워크플로는 도는데 **굽는 잡이 없어** 없는 태그를 적용 → ImagePullBackOff.
    #     server 스모크는 통과하므로 늦게 발견된다.
    # 태그는 ES 버전을 따라간다(Dockerfile 의 ARG ES_VERSION) — 버전을 올릴 때만 굽는다.
    "es": {
        "image": "seongyuna/callguard-es",
        "paths": re.compile(r"^infra/elasticsearch/"),
        "output": "es_build",
    },
}

DEFAULT_KUSTOMIZATION = "infra/k8s/base/kustomization.yaml"

UNDECIDED = 2


class Undecided(Exception):
    """레지스트리에 태그가 있는지 «판정하지 못했다». 없다는 뜻이 아니다."""


def read_tags(kustomization: str) -> dict[str, str]:
    """`kustomization.yaml` 의 images 에서 이미지별 newTag 를 읽는다.

    PyYAML 없이 돈다 — CI 가 의존성을 깔지 않고 부르기 때문이다(`check_session_end.py` 와 같은 이유).
    """
    with open(kustomization, encoding="utf-8") as fh:
        text = fh.read()
    tags = {}
    for key, spec in IMAGES.items():
        m = re.search(
            r"-\s*name:\s*" + re.escape(spec["image"]) + r"\s*\n\s*newTag:\s*\"?([^\"\s]+)\"?",
            text,
        )
        if not m:
            sys.exit(f"{kustomization} 에서 {spec['image']} 의 newTag 를 찾지 못했습니다.")
        tags[key] = m.group(1)
    return tags


def _get(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:  # 404 도 여기로 온다 — 상태 코드를 그대로 돌려준다
        return exc.code, b""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Undecided(f"네트워크 오류: {exc}") from exc


def _token(repo: str) -> str:
    """pull 스코프 토큰. 자격증명이 있으면 인증 토큰을 받는다 — 익명은 레이트 리밋에 쉽게 걸린다."""
    headers = {}
    user = os.environ.get("DOCKERHUB_USERNAME")
    secret = os.environ.get("DOCKERHUB_TOKEN")
    if user and secret:
        import base64

        basic = base64.b64encode(f"{user}:{secret}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"
    status, body = _get(AUTH_URL.format(repo=repo), headers)
    if status != 200:
        raise Undecided(f"토큰 발급 실패 (HTTP {status})")
    try:
        return json.loads(body)["token"]
    except (ValueError, KeyError) as exc:
        raise Undecided(f"토큰 응답을 읽지 못했다: {exc}") from exc


def tag_exists(repo: str, tag: str, attempts: int = 3) -> bool:
    """200=있음 · 404=없음 · 그 외=Undecided. 일시적 오류만 재시도한다."""
    last = "원인 미상"
    for i in range(attempts):
        try:
            token = _token(repo)
            status, _ = _get(
                MANIFEST_URL.format(repo=repo, tag=tag),
                {"Authorization": f"Bearer {token}", "Accept": ACCEPT},
            )
            if status == 200:
                return True
            if status == 404:
                return False
            last = f"HTTP {status}"
        except Undecided as exc:
            last = str(exc)
        if i < attempts - 1:
            time.sleep(2 * (i + 1))
    raise Undecided(last)


def _git(*args: str) -> str | None:
    """git 을 부른다. 실패하면 None — 이 검사는 있으면 좋은 것이지 필수가 아니다."""
    import subprocess

    try:
        r = subprocess.run(("git",) + args, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def warn_tag_taken_elsewhere(tags: dict[str, str]) -> None:
    """**아직 레지스트리에 없는** 태그를 다른 브랜치가 이미 집었는지 본다.

    레지스트리 검사로는 이걸 못 잡는다 — 두 브랜치가 같은 새 태그를 집으면 **양쪽 다
    `exists=false`** 라 통과하고, 나중에 머지하는 쪽이 릴리스에서 터진다.
    2026-09-14 하루에 두 번 났다(`0.1.4` · `0.1.5`).

    **경고로만 낸다.** 실패시키지 않는 이유: 저쪽 브랜치가 머지되지 않을 수도 있고,
    먼저 머지하는 쪽은 아무 잘못이 없다. 두 번째가 되는 순간은 레지스트리 검사가 잡는다.
    """
    branches = _git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    if not branches:
        return
    here = _git("rev-parse", "HEAD")
    # 이미지별로 모아서 한 번만 알린다 — 머지를 타고 여러 브랜치에 같은 값이 퍼져 있으면
    # 브랜치마다 경고가 나서 읽기 나쁘다(오늘 server 의 값이 frontend 에도 있었다).
    hits: dict[str, list[str]] = {}
    for branch in branches.split():
        if branch.endswith("/HEAD"):
            continue
        # 저장소 경로로 본다 — `--kustomization` 으로 준 임의 경로는 git 이 모른다.
        blob = _git("show", f"{branch}:{DEFAULT_KUSTOMIZATION}")
        if not blob:
            continue
        for key, spec in IMAGES.items():
            m = re.search(
                r"-\s*name:\s*" + re.escape(spec["image"]) + r'\s*\n\s*newTag:\s*"?([^"\s]+)"?',
                blob,
            )
            if not m or m.group(1) != tags[key]:
                continue
            # **저쪽이 그 값을 실제로 «집었는가»** 를 본다. 갈라진 지점(merge-base)의 값과 같으면
            # 그냥 물려받은 것이라 경쟁이 아니다 — 이 필터가 없으면 모두가 공유하는 값
            # (`es` 9.5.1 처럼)마다 경고가 떠서 아무도 안 읽게 된다.
            base = _git("merge-base", "HEAD", branch)
            if base:
                base_blob = _git("show", f"{base.strip()}:{DEFAULT_KUSTOMIZATION}")
                if base_blob:
                    bm = re.search(
                        r"-\s*name:\s*" + re.escape(spec["image"]) + r'\s*\n\s*newTag:\s*"?([^"\s]+)"?',
                        base_blob,
                    )
                    if bm and bm.group(1) == m.group(1):
                        continue  # 저쪽은 안 바꿨다 — 물려받은 값이다
            who = (
                _git("log", "-1", "--format=%an · %ad · %h", "--date=format:%m-%d %H:%M",
                     branch, "--", DEFAULT_KUSTOMIZATION) or ""
            ).strip()
            hits.setdefault(key, []).append(f"{branch}{' (' + who + ')' if who else ''}")

    for key, where in hits.items():
        print(
            f"::warning::{IMAGES[key]['image']} 의 태그 '{tags[key]}' 를 다른 브랜치도 쓰고 있다 — "
            + " · ".join(where)
            + ". 레지스트리엔 아직 없어 지금은 양쪽 다 통과하지만, 나중에 머지하는 쪽이 "
            "릴리스에서 막힌다. 먼저 손댄 쪽이 살고 뒤가 물러난다(`CLAUDE.md` §4).",
            file=sys.stderr,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--kustomization",
        default=DEFAULT_KUSTOMIZATION,
        help="배포 태그의 정본",
    )
    ap.add_argument(
        "--emit-build",
        action="store_true",
        help="GITHUB_OUTPUT 에 tag/call_mediator_tag 와 build/call_mediator_build 를 쓴다 (release.yml 전용). "
        "PR 검사는 굽지 않으므로 쓰지 않는다.",
    )
    ap.add_argument(
        "--force-build",
        action="store_true",
        help="태그가 이미 있어도 굽는다 (workflow_dispatch 전용).",
    )
    args = ap.parse_args()

    tags = read_tags(args.kustomization)
    out = os.environ.get("GITHUB_OUTPUT")

    # 태그도 여기서 내준다 — release.yml 이 image 잡에 넘겨야 하는데, 거기서 따로 파싱하면
    # 같은 정규식이 두 벌이 되고 kustomization 형식이 바뀔 때 **두 곳을 고쳐야** 한다.
    # 이 저장소가 이름 동기화를 두 번 놓친 것과 같은 패턴이다(`CLAUDE.md` §7).
    # 판정 전에 쓴다 — 아래에서 일찍 돌아가도 태그는 나가야 한다.
    if args.emit_build and out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"tag={tags['server']}\n")
            fh.write(f"call_mediator_tag={tags['call-mediator']}\n")
            fh.write(f"es_tag={tags['es']}\n")
    print(f"배포할 태그: server={tags['server']} call-mediator={tags['call-mediator']} es={tags['es']}")

    changed = [line.strip() for line in sys.stdin if line.strip()]
    if not changed:
        print("변경된 파일이 없다 — 판정할 것이 없다.")
        return 0

    # 레지스트리 검사가 못 보는 구멍 하나를 경고로 덮는다(아래 함수 설명 참조).
    warn_tag_taken_elsewhere(tags)

    failed = []
    decisions = []

    for key, spec in IMAGES.items():
        image, tag = spec["image"], tags[key]
        code_changed = any(spec["paths"].match(p) for p in changed)
        try:
            exists = tag_exists(image, tag)
        except Undecided as exc:
            # 여기서 「없음」으로 접지 않는다. 접으면 게이트가 조용히 사라진다.
            print(
                f"::error::{image}:{tag} 가 레지스트리에 있는지 판정하지 못했다 ({exc}). "
                "레이트 리밋·비공개 저장소·일시적 장애일 수 있다. 다시 실행하거나 "
                "DOCKERHUB_USERNAME/DOCKERHUB_TOKEN 이 붙어 있는지 확인한다.",
                file=sys.stderr,
            )
            return UNDECIDED

        print(f"[{image}] 태그 {tag} — 레지스트리에 있음: {exists} · 코드 변경: {code_changed}")

        if code_changed and exists and not args.force_build:
            failed.append(
                f"::error::{image} 에 들어가는 코드가 바뀌었는데 newTag 가 '{tag}' 그대로입니다.\n"
                f"같은 태그로 다시 구워도 노드는 캐시된 옛 이미지를 계속 씁니다(IfNotPresent).\n"
                f"{args.kustomization} 의 newTag 를 올려 **같은 PR 안에서** 넣으세요."
            )
        decisions.append((spec["output"], (not exists) or args.force_build))

    # 이미지 둘을 **둘 다** 판정하고 나서 실패시킨다 — 하나가 걸렸다고 멈추면
    # 나머지 문제를 다음 실행에서 또 만나게 된다.
    if failed:
        for message in failed:
            print(message, file=sys.stderr)
        return 1

    if args.emit_build and out:
        with open(out, "a", encoding="utf-8") as fh:
            for name, value in decisions:
                fh.write(f"{name}={'true' if value else 'false'}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
