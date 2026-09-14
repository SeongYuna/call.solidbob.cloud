// Requirement: COST-1
/**
 * `data/processed/stt-usage.json` — `scripts/transcribe_batch.py` 와 **같은 파일**이다.
 * 같은 머신에서 배치 전사와 실시간 스트림이 한 장부를 나눠 써야 캡이 두 배가 되지 않는다.
 *
 * 쓰기는 읽고-더하고-쓰기다. 그 사이 배치 스크립트가 쓴 값을 덮지 않으려는 것이다(완전한
 * 잠금은 아니다 — 두 프로세스가 같은 밀리초에 쓰면 한쪽이 진다. 캡의 1차 방어선은 GCP 쿼터다).
 * 임시 파일에 쓰고 이름을 바꿔, 쓰다 죽어도 반쯤 쓴 JSON 이 남지 않게 한다.
 */
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import type { LedgerStore } from "../app/ports.ts";

export class JsonLedgerFile implements LedgerStore {
  private readonly path: string;

  constructor(path: string) {
    this.path = path;
  }

  async read(): Promise<Record<string, number>> {
    let text: string;
    try {
      text = await readFile(this.path, "utf-8");
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") {
        return {}; // 아직 아무도 안 썼다
      }
      throw error;
    }
    // 깨진 파일은 예외로 올린다 — 빈 장부로 보면 쓴 만큼이 사라진다(가드가 막는다).
    const parsed: unknown = JSON.parse(text);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      throw new Error("사용량 장부 형식이 아니다");
    }
    const ledger: Record<string, number> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === "number" && Number.isFinite(value)) {
        ledger[key] = value;
      }
    }
    return ledger;
  }

  async add(day: string, seconds: number): Promise<Record<string, number>> {
    const ledger = await this.read();
    ledger[day] = (ledger[day] ?? 0) + seconds;
    await mkdir(dirname(this.path), { recursive: true });
    const tmp = `${this.path}.${process.pid}.tmp`;
    // 파이썬 쪽(json.dumps(indent=2, sort_keys=True))과 같은 모양으로 쓴다 — diff 가 조용해진다.
    const sorted = Object.fromEntries(Object.entries(ledger).sort(([a], [b]) => a.localeCompare(b)));
    await writeFile(tmp, JSON.stringify(sorted, null, 2), "utf-8");
    await rename(tmp, this.path);
    return ledger;
  }
}
