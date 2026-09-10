/**
 * QA 리뷰 큐 mock. `apps/dashboard`의 상담기록(`mock/scenarios/`) 전체
 * 시나리오 엔진을 옮기지 않고, 리뷰 목록에 필요한 최소 정보만 담았다 —
 * 문의 유형·요약·상담 분위기·콜가드 건수.
 */
export interface QaReviewFixture {
  call_id: string;
  inquiry_type: string;
  summary: string;
  overall: "양호" | "주의 필요";
  guardFlagCount: number;
  trajectory: string[];
}

export const QA_REVIEW_FIXTURES: QaReviewFixture[] = [
  {
    call_id: "c_seed_1",
    inquiry_type: "시설 민원 · 콜가드",
    summary:
      "하수도 역류 민원으로 접수. 상담 도중 고객의 욕설·위협 발화가 반복돼 콜가드가 두 차례 경고했다.",
    overall: "주의 필요",
    guardFlagCount: 2,
    trajectory: ["차분", "약간 격앙", "격앙"],
  },
  {
    call_id: "c_seed_7",
    inquiry_type: "고객 응대 · 콜가드 감지",
    summary:
      "재난지원금 지급 지연 문의. 대기 시간에 대한 불만으로 폭언이 한 차례 감지됐다.",
    overall: "주의 필요",
    guardFlagCount: 1,
    trajectory: ["약간 격앙", "약간 격앙", "차분"],
  },
  {
    call_id: "c_seed_8",
    inquiry_type: "주민등록등본 재발급 절차",
    summary: "본인확인 절차 안내 후 정상 종료. 특이사항 없음.",
    overall: "양호",
    guardFlagCount: 0,
    trajectory: ["차분", "차분"],
  },
];
