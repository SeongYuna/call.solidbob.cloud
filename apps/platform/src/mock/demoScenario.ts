export const DEMO_DURATION_SEC = 72;
export const DEMO_PLAYBACK_RATE = 6;
export const DEMO_LOOP_HOLD_MS = 1400;

export type DemoSpeaker = "시민" | "상담원";

export interface DemoTurn {
  at: number;
  speaker: DemoSpeaker;
  body: string;
  bodyPlain: string;
  translation?: string;
}

export interface DemoStep {
  at: number;
  clock: string;
  label: string;
  title: string;
  points: readonly string[];
  footer: string | null;
  reportBox?: boolean;
}

export const DEMO_TURNS: readonly DemoTurn[] = [
  {
    at: 3,
    speaker: "시민",
    body: "여보세요, 저희 집 앞 골목이 비만 오면 물에 잠겨서 차도 못 다녀요. 봉은사로 **길 **호인데 벌써 세 번째예요. 연락처는 010-****-6789 예요.",
    bodyPlain:
      "여보세요, 저희 집 앞 골목이 비만 오면 물에 잠겨서 차도 못 다녀요. 봉은사로 12길 34호인데 벌써 세 번째예요. 연락처는 010-1234-6789 예요.",
  },
  {
    at: 7,
    speaker: "상담원",
    body: "불편을 겪으신 점 정말 죄송합니다. 봉은사로 **길 ** 앞 맞으시죠? 결과는 010-****-6789로 문자 드리겠습니다.",
    bodyPlain:
      "불편을 겪으신 점 정말 죄송합니다. 봉은사로 12길 34 앞 맞으시죠? 결과는 010-1234-6789로 문자 드리겠습니다.",
  },
  {
    at: 21,
    speaker: "상담원",
    body: "그리고 이건 솔직히 저희가 해결할 수 있는 게 아니라서요, 구청에 직접 알아보셔야 할 것 같은데요.",
    bodyPlain:
      "그리고 이건 솔직히 저희가 해결할 수 있는 게 아니라서요, 구청에 직접 알아보셔야 할 것 같은데요.",
  },
  {
    at: 38,
    speaker: "시민",
    body: "Sorry, can I ask in English? I reported this before and nothing changed.",
    bodyPlain:
      "Sorry, can I ask in English? I reported this before and nothing changed.",
    translation:
      "죄송하지만 영어로 말씀드려도 될까요? 예전에도 신고했는데 아무 변화가 없었어요.",
  },
  {
    at: 54,
    speaker: "시민",
    body: "아니 진짜, 세 번이나 말했는데 또 이러면 나 어떡하라는 거예요? 이번에도 안 되면 나 진짜... 어휴, 답답해서 죽겠네 진짜.",
    bodyPlain:
      "아니 진짜, 세 번이나 말했는데 또 이러면 나 어떡하라는 거예요? 이번에도 안 되면 나 진짜... 어휴, 답답해서 죽겠네 진짜.",
  },
  {
    at: 72,
    speaker: "상담원",
    body: "세 번씩이나 불편을 겪으신 점, 정말 죄송합니다. 오늘 안으로 도로관리과에 이첩하고, 48시간 내 현장 점검 결과를 문자로 안내해 드리겠습니다.",
    bodyPlain:
      "세 번씩이나 불편을 겪으신 점, 정말 죄송합니다. 오늘 안으로 도로관리과에 이첩하고, 48시간 내 현장 점검 결과를 문자로 안내해 드리겠습니다.",
  },
];

export const DEMO_STEPS: readonly DemoStep[] = [
  {
    at: 3,
    clock: "00:03",
    label: "실시간 대화 분석",
    title: "핵심 민원 포착",
    points: [
      "주제: 도로·골목 침수",
      "감정 톤: 불만 · 반복 민원 (3회)",
      "요청: 근본적 해결 요구",
    ],
    footer: "유형 분류 진행 중...",
  },
  {
    at: 7,
    clock: "00:07",
    label: "민원 유형 · 근거 추천",
    title: "도로 침수 민원 처리 패키지",
    points: [
      "필요 정보: 주소 · 침수 빈도 · 피해 사진 (개인정보는 마스킹 저장)",
      "근거 문서: 「도로법 시행령 제23조」 배수시설 유지관리 기준",
      "연결 부서: 도로관리과 배수 민원 담당 (즉시 이첩 가능)",
    ],
    footer: "과거 동일 지역 민원 2건 — 재발 사례로 표시됨",
  },
  {
    at: 21,
    clock: "00:21",
    label: "컴플라이언스 감지",
    title: "부적절 표현 감지 — 대체 표현 제안",
    points: [
      "감지: 「저희가 해결할 수 있는 게 아니라서요」 — 책임 회피성 표현",
      "대체 제안: 「담당 부서에서 처리하는 사안이라, 제가 바로 이첩하고 진행 상황까지 안내해 드리겠습니다」",
    ],
    footer: "상담 품질 가이드라인 4.2항 참조",
  },
  {
    at: 38,
    clock: "00:38",
    label: "동시 통번역 · EN",
    title: "외국인 고객 감지 — 실시간 통번역",
    points: [
      "시민 발화(영어) → 한국어로 즉시 번역해 상담원 화면에 표시",
      "번역 텍스트에도 동일한 개인정보 마스킹 규칙 적용",
      "상담원 답변(한국어) → 영어 자막·음성으로 실시간 전달",
      "지원 언어: 영어 · 중국어 · 일본어 · 베트남어 · 태국어",
    ],
    footer: null,
  },
  {
    at: 54,
    clock: "00:54",
    label: "정서 위기 감지",
    title: "격앙·정서 위기 신호 — 관리자 알림 발송",
    points: [
      "감지 신호: 어조 격앙·절망 표현 (「죽겠네」)",
      "관리자 대시보드에 실시간 알림 전송됨 · 지원 상담원 배치 가능",
      "상담원 권장 대응: 감정 수용 → 구체적 약속 → 책임자 연결",
    ],
    footer: "상담원 보호 프로토콜 준비 완료",
  },
  {
    at: 72,
    clock: "01:12",
    label: "통화 후 자동 정리",
    title: "종료 즉시 후속 조치 생성",
    points: [
      "요약: 골목 반복 침수(3회) — 도로관리과 이첩, 48시간 내 점검 약속",
      "유형 분류: 시설/도로 > 배수 > 반복민원(재발)",
      "지역자원 연계: 침수 피해 지원 안내 문자 자동 발송",
    ],
    footer: "처리 기록 자동 저장 · 개인정보 마스킹 적용 · 상담원 입력 0건",
    reportBox: true,
  },
];
