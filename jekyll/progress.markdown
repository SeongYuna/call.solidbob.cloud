---
layout: doc
title: 개발 로그
permalink: /progress/
---

<style>
  main:has(.lg-layout){ max-width:1100px; }
  .lg-layout{ display:flex; gap:1.25rem; align-items:flex-start; margin:0 0 2rem; }
  .lg-sidebar{ flex:0 0 200px; display:flex; flex-direction:column; gap:0.4rem; position:sticky; top:1rem; }
  .lg-nav-item{ display:flex; flex-direction:column; align-items:flex-start; gap:0.3rem; width:100%; padding:0.7rem 0.75rem 0.7rem 0.85rem; border:1px solid rgba(223,228,238,.12); border-radius:6px; background:#080B12; color:#DFE4EE; text-align:left; cursor:pointer; }
  .lg-nav-item:hover{ border-color:rgba(245,166,35,.4); }
  .lg-nav-item.active{ background:#10151F; box-shadow:inset 3px 0 0 currentColor; }
  .lg-nav-item.active.role-all{ color:#DFE4EE; }
  .lg-nav-item.active.role-infra{ color:#8FA8E8; }
  .lg-nav-item.active.role-ai{ color:#F5A623; }
  .lg-nav-item.active.role-app{ color:#FFE6A8; }
  .lg-nav-name{ font-weight:600; color:#DFE4EE; }
  .lg-nav-count{ font-family:'IBM Plex Mono',monospace; font-size:0.72rem; color:#79839B; }
  .lg-nav-item .role{ display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:0.65rem; letter-spacing:.04em; font-weight:600; padding:0.15rem 0.5rem; border-radius:999px; white-space:nowrap; border:1px solid currentColor; }
  .role-all{ background:rgba(223,228,238,.08); color:#9AA4BB; }
  .role-infra{ background:rgba(110,143,214,.12); color:#8FA8E8; }
  .role-ai{ background:rgba(245,166,35,.12); color:#F5A623; }
  .role-app{ background:rgba(255,230,168,.10); color:#FFE6A8; }
  .lg-content{ flex:1; min-width:0; }
  .lg-panel{ display:none; }
  .lg-panel.active{ display:block; animation:lg-fade 140ms ease-out; }
  .lg-panel > h2{ display:flex; align-items:center; gap:0.6rem; margin-top:0; }
  .lg-panel > h2 .count{ font-family:'IBM Plex Mono',monospace; font-size:0.72rem; font-weight:500; color:#79839B; }
  .lg-day{ margin:0 0 0.9rem; background:#10151F; border:1px solid rgba(223,228,238,.12); border-radius:8px; padding:0.85rem 1rem; }
  .lg-day-head{ display:flex; align-items:baseline; gap:0.6rem; margin:0 0 0.55rem; }
  .lg-date{ font-family:'IBM Plex Mono',monospace; font-size:0.8rem; font-weight:600; letter-spacing:.03em; color:#DFE4EE; }
  .lg-who{ font-family:'IBM Plex Mono',monospace; font-size:0.65rem; letter-spacing:.04em; font-weight:600; padding:0.15rem 0.5rem; border-radius:999px; white-space:nowrap; border:1px solid currentColor; }
  .lg-seq{ font-family:'IBM Plex Mono',monospace; font-size:0.7rem; color:#4d5568; margin-left:auto; }
  .lg-day ul{ margin:0; padding-left:1.15rem; }
  .lg-day li{ font-size:0.88rem; line-height:1.65; margin-bottom:0.35rem; }
  .lg-day li:last-child{ margin-bottom:0; }
  .lg-empty{ color:#4d5568; font-size:0.85rem; padding:1rem 0; }
  @keyframes lg-fade{ from{ opacity:0; } to{ opacity:1; } }
  @media (max-width:640px){
    .lg-layout{ flex-direction:column; }
    .lg-sidebar{ flex:none; width:100%; flex-direction:row; flex-wrap:wrap; position:static; }
    .lg-nav-item{ flex:1 1 140px; }
  }
  @media (prefers-reduced-motion: reduce){ .lg-panel.active{ animation:none; } }
</style>

작성자별 개발 로그입니다. **항목 1건 = 파일 1개**(`jekyll/_logs/`)이므로 네 사람이 같은 날 동시에 기록을 남겨도 병합 충돌이 나지 않습니다.
주차별 목표는 [8주 마일스톤](/docs/08/), 티켓 보드는 [칸반](/kanban/), 아직 정하지 못한 것은 [미결 항목](/open-items/)에 있습니다.

{% comment %}
  정렬은 파일 경로로 한다. 파일명이 `YYYY-MM-DD-NN-사람.md` 라서 경로를 내림차순으로
  뒤집으면 그대로 "최신 날짜 → 그날의 늦은 순번" 이 된다.
  date·seq 두 필드로 두 번 정렬하는 방법은 쓰지 않는다 — Liquid 의 sort 는 안정 정렬이
  아니라서 같은 날짜 안의 순서가 섞인다(실제로 섞였다).
{% endcomment %}
{% assign all_logs = site.logs | sort: "path" | reverse %}
{% assign people = "전체,정성윤,류준,장민석,조서희" | split: "," %}

<div class="lg-layout">
  <nav class="lg-sidebar" aria-label="작성자">
    {% for name in people %}
      {% case name %}
        {% when "전체" %}{% assign pid = "all" %}{% assign prole = "all" %}{% assign items = all_logs %}
        {% when "정성윤" %}{% assign pid = "seongyun" %}{% assign prole = "infra" %}{% assign items = all_logs | where: "person", "seongyun" %}
        {% when "류준" %}{% assign pid = "ryujun" %}{% assign prole = "ai" %}{% assign items = all_logs | where: "person", "ryujun" %}
        {% when "장민석" %}{% assign pid = "minseok" %}{% assign prole = "ai" %}{% assign items = all_logs | where: "person", "minseok" %}
        {% when "조서희" %}{% assign pid = "seohee" %}{% assign prole = "app" %}{% assign items = all_logs | where: "person", "seohee" %}
      {% endcase %}
      {% assign day_count = items | map: "date" | uniq | size %}
      <button type="button" class="lg-nav-item role-{{ prole }}{% if forloop.first %} active{% endif %}" data-person="{{ pid }}">
        <span class="role role-{{ prole }}">{% case prole %}{% when "all" %}팀 전체{% when "infra" %}인프라{% when "ai" %}백엔드·AI{% when "app" %}프론트엔드{% endcase %}</span>
        <span class="lg-nav-name">{{ name }}</span>
        <span class="lg-nav-count">{{ items.size }}건 · {{ day_count }}일</span>
      </button>
    {% endfor %}
  </nav>

  <div class="lg-content">
    {% for name in people %}
      {% case name %}
        {% when "전체" %}{% assign pid = "all" %}{% assign items = all_logs %}
        {% when "정성윤" %}{% assign pid = "seongyun" %}{% assign items = all_logs | where: "person", "seongyun" %}
        {% when "류준" %}{% assign pid = "ryujun" %}{% assign items = all_logs | where: "person", "ryujun" %}
        {% when "장민석" %}{% assign pid = "minseok" %}{% assign items = all_logs | where: "person", "minseok" %}
        {% when "조서희" %}{% assign pid = "seohee" %}{% assign items = all_logs | where: "person", "seohee" %}
      {% endcase %}
      <div class="lg-panel{% if forloop.first %} active{% endif %}" data-person="{{ pid }}">
        <h2>{{ name }} <span class="count">{{ items.size }}건</span></h2>
        {% for log in items %}
          {% case log.person %}
            {% when "seongyun" %}{% assign lrole = "infra" %}
            {% when "seohee" %}{% assign lrole = "app" %}
            {% else %}{% assign lrole = "ai" %}
          {% endcase %}
          <article class="lg-day">
            <div class="lg-day-head">
              <span class="lg-date">{{ log.date | date: "%Y-%m-%d" }}</span>
              {% if pid == "all" %}<span class="lg-who role-{{ lrole }}">{{ log.author }}</span>{% endif %}
              <span class="lg-seq">#{{ log.seq }}</span>
            </div>
            {{ log.content | markdownify }}
          </article>
        {% endfor %}
        {% if items.size == 0 %}<div class="lg-empty">아직 기록이 없습니다.</div>{% endif %}
      </div>
    {% endfor %}
  </div>
</div>

<script>
document.querySelectorAll(".lg-nav-item").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var target = btn.dataset.person;
    document.querySelectorAll(".lg-nav-item").forEach(function (other) {
      other.classList.toggle("active", other === btn);
    });
    document.querySelectorAll(".lg-panel").forEach(function (panel) {
      panel.classList.toggle("active", panel.dataset.person === target);
    });
    if (history.replaceState) { history.replaceState(null, "", "#" + target); }
  });
});
// 새로고침·링크 공유 시 해시로 열린 탭을 복원한다 (예: /progress/#ryujun)
(function () {
  var want = (location.hash || "").slice(1);
  if (!want) return;
  var btn = document.querySelector('.lg-nav-item[data-person="' + want + '"]');
  if (btn) { btn.click(); }
})();
</script>

## 기록 남기는 법

`jekyll/_logs/` 에 파일을 하나 만듭니다. **다른 사람 파일은 건드리지 않습니다.**

```yaml
---
date: 2026-08-27
author: "류준"          # 정성윤 | 류준 | 장민석 | 조서희
person: ryujun          # seongyun | ryujun | minseok | seohee
seq: 1                  # 같은 날 안에서의 순서. 자기 것만 1, 2, 3… 으로 센다
---

- **무엇을 했는지** — 왜 그렇게 했는지, 무엇을 확인했는지
- 남은 것: 다음 세션이 이어받을 것
```

파일명은 `YYYY-MM-DD-{seq}-{person}.md` 로 짓습니다(예: `2026-08-27-01-ryujun.md`).
`seq` 는 두 자리로 씁니다 — 정렬이 파일 경로 기준이라 `9` 로 쓰면 `10` 보다 뒤로 갑니다.

**`seq` 는 자기 것만 셉니다.** 예전의 `(44)`, `(45)` 처럼 팀이 공유하는 번호가 아니라서
남과 겹쳐도 됩니다 — 파일명에 작성자가 함께 들어가 있어 **서로 다른 파일이 되고,
브랜치를 합칠 때 충돌이 나지 않습니다.** 겹치면 같은 날 안에서 둘의 앞뒤만 이름순으로 정해집니다.

한 번 쓴 항목은 고치지 않습니다. 틀린 것은 새 항목으로 정정합니다([CLAUDE.md 절대 원칙 8](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/CLAUDE.md)).

---

[← 개발목차로 돌아가기](/toc/)
