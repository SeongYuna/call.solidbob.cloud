/**
 * evidence 옆 설명. true/false 판정은 바꾸지 않는다 — 미안내(미충족) 항목에만 붙는 안내.
 *
 * 금융·쇼핑 조항은 4도메인 시절 POLICY.md · MANUAL.md 에서 옮긴 값이다
 * (decisions/201 이후 해당 지식베이스는 삭제됨. 힌트 표는 되돌리기용으로 남긴다).
 * 다산 서류 키는 응대매뉴얼 3.1 기준 **예시**다. 69종 실측이 오면 이 표를 교체한다.
 */

export interface EvidenceHint {
  /** 예: "이용약관 제3조 2항". 매핑을 모르면 null */
  clause: string | null;
  /** 미충족일 때만 화면에 낸다. 문서에 요구 내용이 없으면 "확인 필요" */
  say: string;
}

const UNKNOWN: EvidenceHint = { clause: null, say: "확인 필요" };

/**
 * POLICY 표의 `N.N조` 표기를 화면용 「제N조 M항」으로 옮긴다.
 * 예: 3.2조 → 이용약관 제3조 2항 (FIN-POLICY-CLOSE-1, 사용자 표시 형식)
 */
function termsClause(chapter: number, paragraph: number): string {
  return `이용약관 제${chapter}조 ${paragraph}항`;
}

const BY_FIELD: Record<string, EvidenceHint> = {
  // FIN-POLICY-CLOSE-1 · FIN-MANUAL-3.1 · FIN-TERM-3.2
  중도해지수수료_안내: {
    clause: termsClause(3, 2),
    say: '"해지 신청 시점의 예상 중도해지수수료 금액을 안내드리겠습니다"라고 고지하면 충족됩니다',
  },
  // FIN-POLICY-CLOSE-1 · FIN-MANUAL-3.1 · FIN-TERM-3.3 ②
  약정혜택소멸_안내: {
    clause: termsClause(3, 3),
    say: '"잔여 약정 혜택(우대금리 등)이 소멸됩니다"라고 고지하면 충족됩니다',
  },
  // FIN-POLICY-CLOSE-1 · FIN-MANUAL-3.1 · FIN-TERM-3.3 (확인 응답)
  고객확인_기록: {
    clause: termsClause(3, 3),
    say: '"지금까지 안내드린 내용, 확인되셨을까요?"라고 여쭤보고 응답을 받으면 충족됩니다',
  },
  // FIN-POLICY-COMPENSATE-1 · FIN-MANUAL-2.2
  사고경위_확인: {
    clause: termsClause(2, 2),
    say: '"신고 시각과 부정사용 내역을 시스템에서 조회해 확인하겠습니다"라고 안내한 뒤 조회하면 충족됩니다',
  },
  귀책여부_확인: {
    clause: termsClause(2, 2),
    say: '"비밀번호 관리 소홀 등 이용자 귀책 사유가 있는지 확인하겠습니다"라고 여쭤보면 충족됩니다',
  },
  // SHOP-POLICY-RETURN-1 · SHOP-MANUAL-3.1 · SHOP-TERM-4.3 ①
  환불금액_안내: {
    clause: termsClause(4, 3),
    say: '"배송비 차감 여부를 포함한 환불 예정 금액을 안내드리겠습니다"라고 고지하면 충족됩니다',
  },
  // SHOP-POLICY-RETURN-1 · SHOP-MANUAL-3.1 · SHOP-TERM-2.2
  환불기간_안내: {
    clause: termsClause(2, 2),
    say: '"결제수단별 환불 소요 기간을 안내드리겠습니다"라고 고지하면 충족됩니다',
  },
  // mock이 금액·기간을 한 키로 묶은 별칭 — 두 행을 합친다
  환불금액_기간_고지: {
    clause: `${termsClause(4, 3)} · ${termsClause(2, 2)}`,
    say: '"배송비 차감 여부를 포함한 환불 예정 금액과, 결제수단별 환불 소요 기간을 안내드리겠습니다"라고 고지하면 충족됩니다',
  },
  // SHOP-POLICY-RETURN-1 표는 이용약관 4.1조
  상품상태_확인: {
    clause: termsClause(4, 1),
    say: '"반품 상품 수거·검수 결과를 확인하겠습니다"라고 안내한 뒤 결과를 확인하면 충족됩니다',
  },
  // SHOP-POLICY-EXCHANGE-1 · SHOP-MANUAL-4.1 · SHOP-TERM-4.4
  교환가능_확인: {
    clause: termsClause(4, 4),
    say: '"사용 흔적·포장 훼손 여부를 확인해 교환 가능 요건을 안내드리겠습니다"라고 확인하면 충족됩니다',
  },
  // SHOP-POLICY-EXCHANGE-1 표는 응대매뉴얼 4.1만 (이용약관 행 없음)
  재고_확인: {
    clause: "응대매뉴얼 4.1",
    say: '"교환 요청하신 사이즈·색상 등 재고를 확인하겠습니다"라고 안내한 뒤 재고를 확인하면 충족됩니다',
  },
  // 다산 mock 예시 — DASAN-MANUAL-3.1. 69종 실측 목록이 아님.
  신분증_사본: {
    clause: "민원응대매뉴얼 3.1",
    say: '"본인 확인용 신분증을 지참해 주세요"라고 안내하면 안내 완료입니다',
  },
  위임장: {
    clause: "민원응대매뉴얼 3.1",
    say: '"대리 신청이면 위임장이 필요합니다"라고 안내하면 안내 완료입니다',
  },
  대리인_신분증: {
    clause: "민원응대매뉴얼 3.1",
    say: '"대리인 본인 신분증도 함께 지참해 주세요"라고 안내하면 안내 완료입니다',
  },
};

const ALIASES: Record<string, string> = {
  사고_경위_확인: "사고경위_확인",
  이용자_귀책_확인: "귀책여부_확인",
  교환가능여부_확인: "교환가능_확인",
};

export function evidenceHint(field: string): EvidenceHint {
  const canonical = ALIASES[field] ?? field;
  return BY_FIELD[canonical] ?? UNKNOWN;
}
