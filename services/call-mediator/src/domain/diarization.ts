// Requirement: A-2
/**
 * 모노 한 줄에 섞인 두 화자를 가르는 규칙 — `/ingest?speaker=auto` 에서만 쓴다(`decisions/303`).
 *
 * 구글 화자 분리는 단어마다 «1번·2번 화자» 라벨만 붙이고 **누가 상담원인지는 알려 주지 않는다.**
 * 그래서 규칙이 하나 필요하고, 그 규칙은 **추측**이다.
 *
 * - **먼저 말한 화자 = 상담원.** 120 은 상담원이 먼저 인사한다(「네, 120 다산콜센터입니다」).
 *   고객이 먼저 말하는 녹음이면 **방향이 통째로 뒤집힌다** — C-1~C-4(상담원)·C-6(고객)·트리거(고객 발화만)가
 *   전부 반대 사람을 본다. 그래서 기본값이 아니라 생산자가 고를 때만 켠다
 * - 라벨이 셋 이상 나오면(구글에 최대 2명을 요청해도) 첫 라벨이 아닌 것은 전부 고객으로 친다
 *
 * 스트리밍에서 화자 분리를 켜면 구글이 **응답마다 처음부터의 모든 단어를 다시 보낸다**(cloud_speech.proto
 * `diarization_config` 주석). 이미 보낸 단어를 또 보내지 않도록 **끝 시각이 워터마크보다 뒤인 단어만** 새로 친다.
 * 라벨은 모델이 대화를 들을수록 고쳐지지만, 이미 화면·DB 로 나간 발화는 되돌리지 않는다.
 */
import type { Speaker } from "../app/ports.ts";

export interface TaggedWord {
  word: string;
  /** 채널 첫 오디오 기준 단어 끝 시각(ms). */
  endMs: number;
  /** 구글 `speakerLabel`(없으면 `speakerTag`). 비었으면 null. */
  label: string | null;
}

export interface SpeakerRun {
  label: string;
  text: string;
  /** 이 구간 마지막 단어의 끝 시각(ms) — `utterance_end_ms` 의 재료. */
  endMs: number;
}

/**
 * `afterMs` 뒤에 끝난 단어만, 같은 라벨이 이어지는 구간으로 묶는다.
 * 라벨 없는 단어는 앞 구간에 붙이고, 앞 구간이 없으면 버린다(누구 말인지 지어내지 않는다).
 */
export function newRuns(words: readonly TaggedWord[], afterMs: number): SpeakerRun[] {
  const runs: SpeakerRun[] = [];
  for (const word of words) {
    if (word.endMs <= afterMs || word.word.trim().length === 0) {
      continue;
    }
    const last = runs[runs.length - 1];
    const label = word.label ?? last?.label ?? null;
    if (label === null) {
      continue;
    }
    if (last !== undefined && last.label === label) {
      last.text = `${last.text} ${word.word.trim()}`;
      last.endMs = word.endMs;
    } else {
      runs.push({ label, text: word.word.trim(), endMs: word.endMs });
    }
  }
  return runs;
}

/** 통화(채널) 하나 동안 라벨 → 화자를 고정한다. 처음 본 라벨이 상담원이다. */
export class FirstSpeakerIsAgent {
  private agentLabel: string | null = null;

  speakerOf(label: string): Speaker {
    if (this.agentLabel === null) {
      this.agentLabel = label;
    }
    return label === this.agentLabel ? "agent" : "customer";
  }
}
