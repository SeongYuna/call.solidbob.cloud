# C-6 폭언 감지 시 일시정지 안내 (베타) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 고객 발화에서 폭언이 잡히면 콜 미디에이터가 매뉴얼 5.1·5.2 규칙으로 단계(`warning` → `final_warning` → `end_suggested`)를 정해 `call_guard_intervention` 메시지를 화면에 보낸다 — **베타 스위치가 켜졌을 때만**.

**Architecture:** 단계 판정은 콜 미디에이터 `src/domain/call_guard_intervention.ts` 의 순수 함수(규칙, 절대 원칙 9). `CallRegistry.checkCallGuard` 가 서버 C-6 검사 결과를 받은 뒤 스위치가 켜져 있으면 그 함수를 불러 통화별 폭언 횟수를 올리고 메시지를 방송한다. 서버·DB·`ai/` 는 바뀌지 않는다.

**Tech Stack:** Node 24 TypeScript(`--experimental-strip-types`) · `node:test` · 콜 미디에이터(`services/call-mediator`)

**Spec:** `_project/decisions/221-C-6-폭언-감지-시-통화-일시정지-안내-베타.md` — 실행자는 반드시 함께 읽는다. 화면은 범위 밖(`jekyll/_backlogs/w8-c6-intervention-overlay-ui.md`, 조서희).

## Global Constraints

- 스위치: 환경변수 `CALL_GUARD_INTERVENTION_BETA` 가 정확히 `"1"`(앞뒤 공백 제거) 일 때만 켜진다. **기본 꺼짐.** 꺼져 있으면 판정 함수를 부르지도, 메시지를 보내지도 않는다
- 폭언 갈래는 `insult` · `threat` · `sexual` 셋. `distress` 는 횟수에 넣지 않는다(매뉴얼 5.4)
- 발화 하나에 폭언 갈래가 여럿이어도 횟수는 **1** 올린다
- 단계: 1회 `warning` · 2회 `final_warning` · 3회 이상 `end_suggested` · 2회 이상인데 이번 발화에 `threat`·`sexual` 이 있으면 `end_suggested`
- `pause_ms`: `warning`·`final_warning` = `"8000"`(예시값 — `decisions/141`), `end_suggested` = `"0"`
- `source_doc_id`: `warning`·`final_warning` = `"DASAN-MANUAL-5.1"`, `end_suggested` = `"DASAN-MANUAL-5.2"`
- 안내 문구는 아래 상수 그대로(모델 생성 금지). `end_suggested` 의 `announcement` 는 `null`
  - `warning`: `고객님, 원활한 상담을 위해 업무와 무관한 표현은 삼가 주시기 바랍니다. 이후에도 계속되면 상담이 종료될 수 있습니다. 잠시 후 상담을 이어가겠습니다.`
  - `final_warning`: `다시 한 번 안내드립니다. 같은 표현이 계속되면 상담이 종료될 수 있습니다. 잠시 후 상담을 이어가겠습니다.`
- 페이로드 값은 전부 문자열(7.3절), `announcement` 만 `null` 가능. 필드: `call_id` `segment_id` `stage` `abuse_count` `pause_ms` `announcement` `source_doc_id` `beta`(`"true"`)
- **시스템은 통화를 끊지 않는다**(5.2) — 채널을 닫거나 STT 를 멈추는 코드를 넣지 않는다. 일시정지 동안에도 전사는 계속된다
- 금지 표현(부록 A-1): 「위험」·점수·퍼센트·「확실」 을 문구·로그에 쓰지 않는다
- 새 파일 맨 위 `// Requirement: C-6`
- 새 대본(폭언 포함)을 만들지 않는다(`decisions/209` 4항)
- 커밋은 브랜치 `ai` 에. **푸시·PR 금지**

## Review Focus

- 서버 C-6 검사가 **실패**(501 등)한 발화 — 횟수를 올리지 않고 메시지도 없다 → Task 2 `test_hub_failure_does_not_count`
- **`distress` 만** 잡힌 발화 — 횟수·메시지 없음, 기존 `call_guard` 는 그대로 → Task 1 `distress only` · Task 2 테스트
- **통화가 둘** 동시에 열려 있을 때 — 횟수는 통화별이다(한 통화의 폭언이 다른 통화 단계를 올리지 않는다) → Task 2 `test_counts_are_per_call`
- 서버 응답 `flags` 항목이 **객체가 아니거나 `category` 가 없을 때** — 무시하고 죽지 않는다 → Task 1 `categoriesOf` 테스트
- 스위치 **꺼짐**이면 `call_guard_intervention` 이 0건 — 지금 운영 동작과 같다 → Task 2 `test_off_by_default`

---

### Task 1: 단계 판정 순수 함수

**Files:**
- Create: `services/call-mediator/src/domain/call_guard_intervention.ts`
- Test: `services/call-mediator/test/call_guard_intervention.test.ts`

**Interfaces:**
- Produces:
  - `export type InterventionStage = "warning" | "final_warning" | "end_suggested"`
  - `export interface Intervention { stage: InterventionStage; abuseCount: number; pauseMs: number; announcement: string | null; sourceDocId: string }`
  - `export function categoriesOf(flags: readonly unknown[]): string[]` — 각 항목에서 문자열 `category` 만 뽑는다
  - `export function nextIntervention(abuseCountBefore: number, categories: readonly string[]): Intervention | null` — 폭언이 없으면 `null`. 있으면 `abuseCount = abuseCountBefore + 1` 로 단계를 정한다
  - `export const WARNING_ANNOUNCEMENT`, `FINAL_WARNING_ANNOUNCEMENT`, `INTERVENTION_PAUSE_MS = 8000`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```ts
// Requirement: C-6
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  categoriesOf, nextIntervention, WARNING_ANNOUNCEMENT, FINAL_WARNING_ANNOUNCEMENT, INTERVENTION_PAUSE_MS,
} from "../src/domain/call_guard_intervention.ts";

test("첫 폭언 → warning, 일시정지, 「종료될 수 있다」 안내, 5.1", () => {
  const it = nextIntervention(0, ["insult"])!;
  assert.equal(it.stage, "warning");
  assert.equal(it.abuseCount, 1);
  assert.equal(it.pauseMs, INTERVENTION_PAUSE_MS);
  assert.equal(it.announcement, WARNING_ANNOUNCEMENT);
  assert.ok(it.announcement!.includes("종료될 수 있습니다"));
  assert.equal(it.sourceDocId, "DASAN-MANUAL-5.1");
});

test("두 번째 insult → final_warning", () => {
  const it = nextIntervention(1, ["insult"])!;
  assert.equal(it.stage, "final_warning");
  assert.equal(it.announcement, FINAL_WARNING_ANNOUNCEMENT);
  assert.equal(it.abuseCount, 2);
});

test("세 번째 이상 → end_suggested, 일시정지·안내 없음, 5.2", () => {
  for (const before of [2, 5]) {
    const it = nextIntervention(before, ["insult"])!;
    assert.equal(it.stage, "end_suggested");
    assert.equal(it.pauseMs, 0);
    assert.equal(it.announcement, null);
    assert.equal(it.sourceDocId, "DASAN-MANUAL-5.2");
  }
});

test("1차 안내 뒤 threat·sexual → 곧바로 end_suggested (5.2)", () => {
  assert.equal(nextIntervention(1, ["threat"])!.stage, "end_suggested");
  assert.equal(nextIntervention(1, ["sexual", "insult"])!.stage, "end_suggested");
});

test("첫 발화가 threat 이어도 먼저 1차 안내", () => {
  assert.equal(nextIntervention(0, ["threat"])!.stage, "warning");
});

test("distress only → null (5.4 — 폭언과 다르게 다룬다)", () => {
  assert.equal(nextIntervention(0, ["distress"]), null);
  assert.equal(nextIntervention(3, []), null);
});

test("갈래가 여럿이어도 발화당 1회", () => {
  assert.equal(nextIntervention(0, ["insult", "threat", "insult"])!.abuseCount, 1);
});

test("categoriesOf — 객체가 아니거나 category 가 없거나 문자열이 아니면 건너뛴다", () => {
  assert.deepEqual(
    categoriesOf([{ category: "insult" }, null, "x", { phrase: "a" }, { category: 3 }, { category: "distress" }]),
    ["insult", "distress"],
  );
});

test("문구에 금지 표현이 없다 (부록 A-1)", () => {
  for (const text of [WARNING_ANNOUNCEMENT, FINAL_WARNING_ANNOUNCEMENT]) {
    for (const bad of ["위험", "%", "점수", "확실"]) assert.ok(!text.includes(bad));
  }
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd services/call-mediator && node --experimental-strip-types --test test/call_guard_intervention.test.ts`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현한다**

```ts
// Requirement: C-6
/**
 * C-6 베타 — 폭언 감지 뒤의 **대응 단계** 판정(`decisions/221`). 응대매뉴얼 5.1·5.2 를 옮긴 규칙이다(절대 원칙 9).
 *
 * - 1회 `warning` → 2회 `final_warning` → 3회 이상 `end_suggested`
 * - 1차 안내를 받은 뒤 `threat`·`sexual` 이면 곧바로 `end_suggested`(5.2)
 * - `distress` 는 넣지 않는다(5.4 — 종료가 아니라 전문 기관 연결)
 *
 * **시스템은 통화를 끊지 않는다**(5.2) — `end_suggested` 는 상담원에게 보이는 권고일 뿐이다.
 * 안내 문구는 고정 문안이다. 모델이 쓰지 않는다.
 */

export type InterventionStage = "warning" | "final_warning" | "end_suggested";

export interface Intervention {
  stage: InterventionStage;
  abuseCount: number;
  pauseMs: number;
  announcement: string | null;
  sourceDocId: string;
}

const ABUSE = new Set(["insult", "threat", "sexual"]);
const SEVERE = new Set(["threat", "sexual"]);

/** 안내 문구를 읽는 시간을 어림한 **예시값**이다 — 잰 값이 아니다(`decisions/141`). */
export const INTERVENTION_PAUSE_MS = 8000;

export const WARNING_ANNOUNCEMENT =
  "고객님, 원활한 상담을 위해 업무와 무관한 표현은 삼가 주시기 바랍니다. 이후에도 계속되면 상담이 종료될 수 있습니다. 잠시 후 상담을 이어가겠습니다.";
export const FINAL_WARNING_ANNOUNCEMENT =
  "다시 한 번 안내드립니다. 같은 표현이 계속되면 상담이 종료될 수 있습니다. 잠시 후 상담을 이어가겠습니다.";

export function categoriesOf(flags: readonly unknown[]): string[] {
  const out: string[] = [];
  for (const flag of flags) {
    if (typeof flag === "object" && flag !== null) {
      const category = (flag as Record<string, unknown>).category;
      if (typeof category === "string") out.push(category);
    }
  }
  return out;
}

export function nextIntervention(abuseCountBefore: number, categories: readonly string[]): Intervention | null {
  const abuse = categories.filter((c) => ABUSE.has(c));
  if (abuse.length === 0) return null;
  const abuseCount = abuseCountBefore + 1;
  const severe = abuse.some((c) => SEVERE.has(c));
  if (abuseCount >= 3 || (abuseCount >= 2 && severe)) {
    return { stage: "end_suggested", abuseCount, pauseMs: 0, announcement: null, sourceDocId: "DASAN-MANUAL-5.2" };
  }
  if (abuseCount === 2) {
    return { stage: "final_warning", abuseCount, pauseMs: INTERVENTION_PAUSE_MS, announcement: FINAL_WARNING_ANNOUNCEMENT, sourceDocId: "DASAN-MANUAL-5.1" };
  }
  return { stage: "warning", abuseCount, pauseMs: INTERVENTION_PAUSE_MS, announcement: WARNING_ANNOUNCEMENT, sourceDocId: "DASAN-MANUAL-5.1" };
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd services/call-mediator && node --experimental-strip-types --test test/call_guard_intervention.test.ts && npm run typecheck`
Expected: 9 pass · typecheck 무오류

- [ ] **Step 5: 커밋**

```bash
git add services/call-mediator/src/domain/call_guard_intervention.ts services/call-mediator/test/call_guard_intervention.test.ts
git commit -m "code(c6): 폭언 대응 단계 판정 — 매뉴얼 5.1·5.2 규칙, 베타 (decisions/221)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 베타 스위치 · 통화별 횟수 · 메시지 방송

**Files:**
- Modify: `services/call-mediator/src/config.ts` (머리말 표에 키 한 줄 · `CallMediatorConfig.callGuardInterventionBeta: boolean` · `loadConfig`)
- Modify: `services/call-mediator/src/app/ports.ts` (`CallGuardInterventionPayload` · `CallMediatorMessage` 에 한 갈래)
- Modify: `services/call-mediator/src/app/call_registry.ts` (deps `announceCallGuardIntervention?: boolean` · `CallState.abuseCount: number`(초기 0) · `checkCallGuard` 끝에 분기)
- Modify: `services/call-mediator/src/main.ts` (`announceCallGuardIntervention: config.callGuardInterventionBeta,` + 주석 「베타 — 운영 매니페스트에 키를 넣지 않는다(`decisions/221`)」)
- Test: `services/call-mediator/test/call_registry.test.ts` (기존 `setup()` 옵션에 `announceCallGuardIntervention` 추가 · 테스트 넷) · `services/call-mediator/test/config.test.ts` (키 하나)

**Interfaces:**
- Consumes: Task 1 의 `categoriesOf`, `nextIntervention`
- Produces:

```ts
/** C-6 베타 — 폭언 대응 단계(`decisions/221`). 값은 전부 문자열, `announcement` 만 null 가능. */
export interface CallGuardInterventionPayload {
  call_id: string;
  segment_id: string;
  stage: "warning" | "final_warning" | "end_suggested";
  abuse_count: string;
  pause_ms: string;
  announcement: string | null;
  source_doc_id: string;
  beta: "true";
}
// CallMediatorMessage 에: | { type: "call_guard_intervention"; payload: CallGuardInterventionPayload }
```

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `test/call_registry.test.ts`. 먼저 파일 앞쪽 `setup()` 의 옵션 타입(22행 근처 `announceCallGuard?: boolean;`)과 deps 전달(54행 근처)에 `announceCallGuardIntervention` 을 같은 방식으로 더한다. 가짜 서버(`test/fakes.ts` `FakeHub`)는 발화에 `guardPhrase`(기본 「병신」 — 파일에서 확인)가 들어 있으면 `insult` 하나를 돌려주고, `failGuard` 를 숫자로 두면 실패한다. 기존 C-6 테스트(484행 근처) 바로 아래에 붙인다:

```ts
test("C-6 베타 — 기본은 꺼짐: call_guard_intervention 을 보내지 않는다", async () => {
  const { registry, stt, broadcaster } = setup({ announceCallGuard: true });
  const customer = await openOk(registry, "test-1", "customer");
  stt.last().emit("이 병신 같은", true, 900);
  await customer.close();
  assert.equal(broadcaster.ofType("call_guard").length, 1);
  assert.equal(broadcaster.ofType("call_guard_intervention").length, 0);
});

test("C-6 베타 — 켜면 1회 warning · 2회 final_warning · 3회 end_suggested, 값은 문자열", async () => {
  const { registry, stt, broadcaster } = setup({ announceCallGuardIntervention: true });
  const customer = await openOk(registry, "test-1", "customer");
  stt.last().emit("이 병신 같은", true, 900);
  await tick(10);
  stt.last().emit("여권 재발급 서류요", true, 2000);
  await tick(10);
  stt.last().emit("또 병신", true, 3000);
  await tick(10);
  stt.last().emit("병신아", true, 4000);
  await customer.close();
  const sent = broadcaster.ofType("call_guard_intervention");
  assert.deepEqual(sent.map((m) => m.payload.stage), ["warning", "final_warning", "end_suggested"]);
  assert.deepEqual(sent.map((m) => m.payload.abuse_count), ["1", "2", "3"]);
  assert.equal(sent[0]!.payload.pause_ms, "8000");
  assert.equal(sent[0]!.payload.beta, "true");
  assert.equal(sent[0]!.payload.call_id, "test-1");
  assert.equal(typeof sent[0]!.payload.segment_id, "string");
  assert.equal(sent[2]!.payload.announcement, null);
  assert.equal(sent[2]!.payload.pause_ms, "0");
});

test("C-6 베타 — 서버 검사가 실패한 발화는 횟수에 넣지 않는다", async () => {
  const { registry, hub, stt, broadcaster } = setup({ announceCallGuardIntervention: true });
  const customer = await openOk(registry, "test-1", "customer");
  hub.failGuard = 501;
  stt.last().emit("이 병신 같은", true, 900);
  await tick(10);
  hub.failGuard = null;
  stt.last().emit("또 병신", true, 2000);
  await customer.close();
  const sent = broadcaster.ofType("call_guard_intervention");
  assert.deepEqual(sent.map((m) => m.payload.stage), ["warning"]);
});

test("C-6 베타 — 횟수는 통화별이다", async () => {
  const { registry, stt, broadcaster } = setup({ announceCallGuardIntervention: true });
  const a = await openOk(registry, "test-a", "customer");
  stt.last().emit("이 병신 같은", true, 900);
  await tick(10);
  const b = await openOk(registry, "test-b", "customer");
  stt.last().emit("이 병신 같은", true, 900);
  await a.close();
  await b.close();
  const sent = broadcaster.ofType("call_guard_intervention");
  assert.deepEqual(sent.map((m) => [m.callId, m.payload.stage]), [["test-a", "warning"], ["test-b", "warning"]]);
});
```

⚠ `broadcaster.ofType` 이 돌려주는 항목에 `callId` 가 없으면(`CaptureBroadcaster` 를 먼저 읽는다) 마지막 테스트는 `payload.call_id` 로 비교한다. `stt.last()` 가 채널마다 다른 가짜 STT 를 돌려주는지도 확인한다 — 다르면 위 순서 그대로 된다.

`test/config.test.ts` 에:

```ts
test("CALL_GUARD_INTERVENTION_BETA — 정확히 1 일 때만 켜진다 (decisions/221)", () => {
  assert.equal(loadConfig({}).callGuardInterventionBeta, false);
  assert.equal(loadConfig({ CALL_GUARD_INTERVENTION_BETA: " 1 " }).callGuardInterventionBeta, true);
  assert.equal(loadConfig({ CALL_GUARD_INTERVENTION_BETA: "true" }).callGuardInterventionBeta, false);
});
```

(그 파일의 import 와 테스트 모양을 먼저 보고 맞춘다. 설정 전체를 `deepEqual` 하는 기존 테스트가 있으면 기대값에 `callGuardInterventionBeta: false` 를 더한다.)

- [ ] **Step 2: 실패 확인**

Run: `cd services/call-mediator && npm test 2>&1 | grep -E "^ℹ (pass|fail)|not ok" | head`
Expected: 새 테스트 다섯이 fail

- [ ] **Step 3: 구현한다**

`config.ts` — 머리말 표 끝에 `| \`CALL_GUARD_INTERVENTION_BETA\` | C-6 베타 — 폭언 대응 단계 메시지(\`decisions/221\`). **정확히 \`1\` 일 때만** 켠다. 운영 매니페스트에 넣지 않는다 | 꺼짐 |`, 인터페이스에 `/** C-6 베타 스위치(\`decisions/221\`). 기본 false. */ callGuardInterventionBeta: boolean;`, `loadConfig` 반환에 `callGuardInterventionBeta: (env.CALL_GUARD_INTERVENTION_BETA ?? "").trim() === "1",`.

`ports.ts` — 위 Interfaces 의 타입과 메시지 갈래.

`call_registry.ts`:
- deps 인터페이스(`announceCallGuard?: boolean;` 아래)에

```ts
  /**
   * C-6 베타 — 폭언 대응 단계(`call_guard_intervention`)를 보낼까(`decisions/221`). 기본 false.
   * 꺼져 있으면 단계 판정도 하지 않는다. **켜도 통화를 끊지 않는다**(매뉴얼 5.2).
   */
  announceCallGuardIntervention?: boolean;
```

- `CallState` 에 `/** C-6 베타 — 이 통화에서 폭언이 잡힌 고객 발화 수. 메모리에만 둔다(`decisions/221` 6절). */ abuseCount: number;` · `callFor` 초기값 `abuseCount: 0,`
- `checkCallGuard` 의 `try` 안, 기존 `call_guard` 방송 뒤에:

```ts
      if (this.deps.announceCallGuardIntervention === true) {
        const intervention = nextIntervention(this.call.abuseCount, categoriesOf(payload.flags));
        if (intervention !== null) {
          this.call.abuseCount = intervention.abuseCount;
          this.deps.broadcaster.publish(this.callId, {
            type: "call_guard_intervention",
            payload: {
              call_id: this.callId,
              segment_id: String(item.segmentId),
              stage: intervention.stage,
              abuse_count: String(intervention.abuseCount),
              pause_ms: String(intervention.pauseMs),
              announcement: intervention.announcement,
              source_doc_id: intervention.sourceDocId,
              beta: "true",
            },
          });
          this.deps.log.info(`C-6 베타 대응 call=${this.callId} segment=${item.segmentId} stage=${intervention.stage} 횟수=${intervention.abuseCount}`);
        }
      }
```

(`this.call` 이 그 클래스에서 실제로 어떤 이름인지 — `checkCallGuard` 가 속한 클래스에서 `this.call.procedures` 처럼 쓰는 필드 — 를 확인해 맞춘다. 로그에 발화 문구를 싣지 않는다.)
- 파일 위 import 에 `import { categoriesOf, nextIntervention } from "../domain/call_guard_intervention.ts";`

`main.ts` — `announceCallGuard: true,` 아래에:

```ts
  // C-6 베타 — 폭언 대응 단계 메시지(decisions/221). 기본 꺼짐 — CALL_GUARD_INTERVENTION_BETA=1 일 때만. 운영 매니페스트에 넣지 않는다
  announceCallGuardIntervention: config.callGuardInterventionBeta,
```

- [ ] **Step 4: 통과·회귀 확인**

Run: `cd services/call-mediator && npm run typecheck && npm test 2>&1 | grep -E "^ℹ (pass|fail)"`
Expected: typecheck 무오류 · fail 0 (기존 + 새 14)

Run: `cd /Users/ryujun/Documents/com.ryujun.demo && python3 scripts/check_release_tags.py; echo exit=$?`
Expected: 결과를 그대로 보고한다. `src/` 변경이라 콜 미디에이터 버전 올림을 요구할 수 있다 — **요구하면 고치지 말고 보고만 한다**(버전 태그는 PR 단계에서 정한다).

- [ ] **Step 5: 커밋**

```bash
git add services/call-mediator/src services/call-mediator/test
git commit -m "code(c6): 폭언 대응 단계 메시지 call_guard_intervention — 베타 스위치 기본 꺼짐 (decisions/221)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
