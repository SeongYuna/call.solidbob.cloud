# Requirement: A-6, SEC-2
"""`GET /hub/uploads/page` 가 내주는 한 장짜리 페이지.

**여기에 비밀이 없다.** 토큰은 사람이 붙여 넣고 `sessionStorage` 에만 남는다(탭을 닫으면 사라진다).
AWS 자격증명은 어떤 형태로도 이 문자열에 들어가지 않는다 — 그게 `decisions/110` 의 전부다.

콜 미디에이터의 `services/call-mediator/src/adapters/dev_page.ts` 와 같은 모양으로 둔다. 별도 프런트 빌드를
만들지 않는 이유: `apps/` 는 조서희 전담이고(`decisions/302`), 이건 팀 내부 도구라 화면을 늘릴 일이 아니다.
"""

from __future__ import annotations

UPLOAD_PAGE_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CallGuard — 테스트 음성 보관</title>
<style>
 :root { color-scheme: light dark; }
 body { font: 15px/1.6 system-ui, -apple-system, sans-serif; margin: 0; padding: 24px 16px; max-width: 760px; }
 h1 { font-size: 1.15rem; margin: 0 0 4px; }
 p.sub { margin: 0 0 20px; opacity: .7; font-size: .9rem; }
 label { display: block; font-weight: 600; margin: 16px 0 6px; font-size: .9rem; }
 input[type=password], input[type=file] { width: 100%; box-sizing: border-box; padding: 8px;
   border: 1px solid rgba(128,128,128,.45); border-radius: 6px; background: transparent; color: inherit; }
 button { margin-top: 14px; padding: 9px 16px; border-radius: 6px; border: 1px solid rgba(128,128,128,.45);
   background: transparent; color: inherit; font: inherit; cursor: pointer; }
 button:disabled { opacity: .5; cursor: default; }
 #log { margin-top: 18px; padding: 10px 12px; border-left: 3px solid rgba(128,128,128,.5);
   white-space: pre-wrap; font-size: .85rem; min-height: 1.6em; }
 table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: .85rem; }
 td, th { text-align: left; padding: 6px 4px; border-bottom: 1px solid rgba(128,128,128,.25); }
 th { font-weight: 600; opacity: .7; }
 td.k { word-break: break-all; }
 audio { width: 100%; margin-top: 10px; }
 .warn { margin-top: 24px; font-size: .8rem; opacity: .75; border-top: 1px solid rgba(128,128,128,.25); padding-top: 12px; }
</style></head><body>
<h1>테스트 음성 보관</h1>
<p class="sub">브라우저가 S3 로 직접 올립니다. 이 페이지에 AWS 키는 없습니다.</p>

<label for="tok">업로드 토큰</label>
<input id="tok" type="password" placeholder="UPLOAD_TOKEN" autocomplete="off">

<label for="f">음성 파일 (wav · mp3 · m4a · flac · ogg)</label>
<input id="f" type="file" accept="audio/*">

<button id="go">올리기</button>
<button id="refresh">목록 새로고침</button>

<div id="log"></div>
<audio id="player" controls hidden></audio>
<table id="list"><thead><tr><th>파일</th><th>크기</th><th>올린 때</th><th></th></tr></thead><tbody></tbody></table>

<p class="warn">⚠ 자체 통화 녹음은 올리지 않습니다 (절대 원칙 7). AI Hub 등 저작권·개인정보가 해결된 출처만 씁니다.
버킷 버전 관리가 꺼져 있어 지운 파일은 되살릴 수 없습니다.</p>

<script>
const $ = (id) => document.getElementById(id);
const log = (m) => { $("log").textContent = m; };
const tok = () => $("tok").value.trim();

// 토큰은 이 탭에만 남는다. localStorage 를 쓰지 않는다 — 공용 PC 에서 다음 사람에게 남는다.
try { $("tok").value = sessionStorage.getItem("callguard_upload_token") || ""; } catch (e) {}
$("tok").addEventListener("change", () => {
  try { sessionStorage.setItem("callguard_upload_token", tok()); } catch (e) {}
});

const api = async (path, options = {}) => {
  const res = await fetch(path, {
    ...options,
    headers: { "Authorization": "Bearer " + tok(), ...(options.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(res.status + " — " + body.slice(0, 300));
  }
  return res.json();
};

const fmtSize = (n) => { n = Number(n); return n > 1048576 ? (n / 1048576).toFixed(1) + " MB"
  : n > 1024 ? (n / 1024).toFixed(0) + " KB" : n + " B"; };

async function refresh() {
  try {
    const data = await api("/hub/uploads?limit=50");
    const body = $("list").querySelector("tbody");
    body.innerHTML = "";
    for (const item of data.items) {
      const tr = document.createElement("tr");
      const name = item.key.split("/").pop();
      tr.innerHTML = '<td class="k"></td><td></td><td></td><td></td>';
      tr.children[0].textContent = name;
      tr.children[1].textContent = fmtSize(item.size);
      tr.children[2].textContent = new Date(item.last_modified).toLocaleString("ko-KR");
      const play = document.createElement("button");
      play.textContent = "듣기";
      play.style.margin = "0";
      play.onclick = () => listen(item.key);
      tr.children[3].appendChild(play);
      body.appendChild(tr);
    }
    log("보관 " + data.total + "건");
  } catch (e) { log("목록 실패: " + e.message); }
}

async function listen(key) {
  try {
    const t = await api("/hub/uploads/download-ticket", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ key }),
    });
    $("player").src = t.url;
    $("player").hidden = false;
    $("player").play();
  } catch (e) { log("재생 실패: " + e.message); }
}

$("go").onclick = async () => {
  const file = $("f").files[0];
  if (!file) { log("파일을 고르세요"); return; }
  if (!tok()) { log("토큰을 넣으세요"); return; }
  $("go").disabled = true;
  try {
    log("티켓 발급 중…");
    const ticket = await api("/hub/uploads/ticket", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || "audio/wav",
        content_length: file.size,
      }),
    });

    // S3 규칙: 정책 필드를 먼저 싣고 `file` 을 **맨 뒤**에 붙인다. 순서가 바뀌면 거절당한다.
    const form = new FormData();
    for (const [k, v] of Object.entries(ticket.fields)) form.append(k, v);
    form.append("file", file);

    log("올리는 중… (" + fmtSize(file.size) + ")");
    const put = await fetch(ticket.url, { method: "POST", body: form });
    if (!put.ok) throw new Error("S3 " + put.status + " — " + (await put.text()).slice(0, 300));

    log("완료: " + ticket.key);
    $("f").value = "";
    refresh();
  } catch (e) {
    log("실패: " + e.message);
  } finally {
    $("go").disabled = false;
  }
};

$("refresh").onclick = refresh;
</script></body></html>
"""
