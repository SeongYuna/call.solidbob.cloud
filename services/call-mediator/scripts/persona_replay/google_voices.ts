// Requirement: A-5, D-5
/**
 * 페르소나 → Google Cloud TTS **ko-KR WaveNet** 음성 배분. 순수 표와 조회 함수만 둔다(테스트 대상).
 *
 * WaveNet 을 고른 이유: SSML `<prosody>`(속도·높이·크기)를 받아 `tone` 을 연기할 수 있고, 무료 한도가 가장 넓다
 * (`TTS.md` 비용 표). 음성 이름·성별은 공식 음성 목록에서 확인했다 —
 * https://docs.cloud.google.com/text-to-speech/docs/voices (2026-09-18 확인): A·C 여성, B·D 남성.
 *
 * 같은 통화에서 상담원과 고객이 같은 목소리가 되지 않게 짰다 — 상담원은 A01→A · A02→B · A03→C 로 고정하고,
 * 고객은 대본의 상담원 조합을 보고 나머지에서 골랐다(`scripts/persona_sim/dasan-v0/SYN-*.json` 의 `agent_persona`).
 * 같은 음성을 쓰는 페르소나는 `pitch`(반음)로 갈라 놓는다 — 고령은 낮게, 청년·유학생은 조금 높게.
 *
 * 우선순위: `personas.json` 의 `google_tts_voice`(있으면 그것) → 이 표 → `tts_voice_hint` 의 「남성/여성」 → `ko-KR-Wavenet-A`.
 * 새 페르소나(A04~·C14~)는 표에 없어도 힌트로 돌아간다.
 */

export type WavenetVoice = "ko-KR-Wavenet-A" | "ko-KR-Wavenet-B" | "ko-KR-Wavenet-C" | "ko-KR-Wavenet-D";

export interface VoiceChoice {
  voice: WavenetVoice;
  /** 기본 높이 보정(반음, -20~20). 같은 음성을 쓰는 페르소나를 가른다. 0 이면 보내지 않는다. */
  pitch: number;
}

export const WAVENET_GENDER: Record<WavenetVoice, "FEMALE" | "MALE"> = {
  "ko-KR-Wavenet-A": "FEMALE",
  "ko-KR-Wavenet-B": "MALE",
  "ko-KR-Wavenet-C": "FEMALE",
  "ko-KR-Wavenet-D": "MALE",
};

export const FALLBACK_VOICE: WavenetVoice = "ko-KR-Wavenet-A";

/** 2026-09-18 기준 페르소나(상담원 3 · 고객 13). `say_voice` 의 성별을 따랐다. */
export const PERSONA_VOICES: Record<string, VoiceChoice> = {
  // 상담원
  A01: { voice: "ko-KR-Wavenet-A", pitch: 1 }, // 신입 · 여성 · 밝은 톤
  A02: { voice: "ko-KR-Wavenet-B", pitch: 0 }, // 일반 · 남성 · 차분
  A03: { voice: "ko-KR-Wavenet-C", pitch: -1 }, // 베테랑 · 여성 · 낮고 일정
  // 고객
  C01: { voice: "ko-KR-Wavenet-C", pitch: 2 }, // 중국인 유학생(Flo)
  C02: { voice: "ko-KR-Wavenet-A", pitch: 0 }, // 베트남 결혼이민자(Sandy)
  C03: { voice: "ko-KR-Wavenet-D", pitch: 0 }, // 직장인(Eddy)
  C04: { voice: "ko-KR-Wavenet-C", pitch: 1 }, // 필리핀 초보 부모(Flo)
  C05: { voice: "ko-KR-Wavenet-D", pitch: -1 }, // 자영업자(Rocko)
  C06: { voice: "ko-KR-Wavenet-B", pitch: -2 }, // 반복 악성 민원인(Grandpa)
  C07: { voice: "ko-KR-Wavenet-A", pitch: -1 }, // 재문의 민원인(Sandy)
  C08: { voice: "ko-KR-Wavenet-C", pitch: -3 }, // 70대 고령 세대원(Grandma)
  C09: { voice: "ko-KR-Wavenet-D", pitch: 1 }, // 청년(Eddy)
  C10: { voice: "ko-KR-Wavenet-D", pitch: -1 }, // 두 번 폭발(Rocko)
  C11: { voice: "ko-KR-Wavenet-B", pitch: 0 }, // 내내 화남(Eddy)
  C12: { voice: "ko-KR-Wavenet-A", pitch: -3 }, // 지친 고령 보호자(Grandma)
  C13: { voice: "ko-KR-Wavenet-A", pitch: 0 }, // 차분한 민원인(Sandy)
};

export interface PersonaVoiceHints {
  /** `personas.json` 에 명시된 구글 음성 — 있으면 표보다 우선한다. */
  google_tts_voice?: string;
  /** 「여성, 20대, 밝은 톤」 같은 문장. 「남성」/「여성」 만 본다. */
  tts_voice_hint?: string;
}

export function isWavenetVoice(name: unknown): name is WavenetVoice {
  return typeof name === "string" && Object.hasOwn(WAVENET_GENDER, name);
}

export function pickVoice(personaId: string | undefined, hints: PersonaVoiceHints = {}): VoiceChoice {
  if (isWavenetVoice(hints.google_tts_voice)) {
    return { voice: hints.google_tts_voice, pitch: personaId !== undefined ? (PERSONA_VOICES[personaId]?.pitch ?? 0) : 0 };
  }
  if (personaId !== undefined && PERSONA_VOICES[personaId] !== undefined) {
    return PERSONA_VOICES[personaId];
  }
  const hint = hints.tts_voice_hint ?? "";
  if (hint.includes("남성")) {
    return { voice: "ko-KR-Wavenet-B", pitch: 0 };
  }
  if (hint.includes("여성")) {
    return { voice: "ko-KR-Wavenet-A", pitch: 0 };
  }
  return { voice: FALLBACK_VOICE, pitch: 0 };
}
