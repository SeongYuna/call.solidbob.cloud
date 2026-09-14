/// apps/admin/src/types/blacklist.ts 를 그대로 옮긴 모델.
/// 개인 실험(`_project/decisions/405`) — 화면 확인용이라 서버 계약과
/// 완전히 동기화하지 않는다. 실제 붙일 땐 apps/admin 쪽을 정본으로 본다.
library;

class BlacklistEvidence {
  final int callDurationS;
  final int insultCount;
  final int threatCount;
  final int sexualCount;
  final int distressCount;
  final int temperatureOutliers;

  const BlacklistEvidence({
    required this.callDurationS,
    required this.insultCount,
    required this.threatCount,
    required this.sexualCount,
    required this.distressCount,
    required this.temperatureOutliers,
  });

  int get abuseTotal => insultCount + threatCount + sexualCount;
  bool get hasDistress => distressCount > 0;
}

enum BlacklistStatus { pending, approved, rejected }

class BlacklistRequestItem {
  final String requestId;
  final String callId;
  final String customerRef;
  final String displayHint;
  final String requestedBy;
  final String reason;
  final String contextExcerpt;
  final BlacklistEvidence evidence;
  final BlacklistStatus status;
  final DateTime requestedAt;
  final String? decidedBy;
  final DateTime? decidedAt;

  const BlacklistRequestItem({
    required this.requestId,
    required this.callId,
    required this.customerRef,
    required this.displayHint,
    required this.requestedBy,
    required this.reason,
    required this.contextExcerpt,
    required this.evidence,
    required this.status,
    required this.requestedAt,
    this.decidedBy,
    this.decidedAt,
  });

  BlacklistRequestItem copyWith({
    BlacklistStatus? status,
    String? decidedBy,
    DateTime? decidedAt,
  }) {
    return BlacklistRequestItem(
      requestId: requestId,
      callId: callId,
      customerRef: customerRef,
      displayHint: displayHint,
      requestedBy: requestedBy,
      reason: reason,
      contextExcerpt: contextExcerpt,
      evidence: evidence,
      status: status ?? this.status,
      requestedAt: requestedAt,
      decidedBy: decidedBy ?? this.decidedBy,
      decidedAt: decidedAt ?? this.decidedAt,
    );
  }
}

/// 등록 **에피소드** 1건 — 고객 1명이 아니다. 같은 customer_ref로 여러 건 있을 수 있다
/// (해제 후 재등록). EntriesTab의 "기존(재범)" 판정이 이걸 이용한다.
class BlacklistEntryItem {
  final String entryId;
  final String customerRef;
  final String requestId;
  final DateTime approvedAt;
  final DateTime expiresAt;
  final DateTime? releasedAt;
  final String? releasedBy;
  final String? releaseReason;
  final String? note;

  const BlacklistEntryItem({
    required this.entryId,
    required this.customerRef,
    required this.requestId,
    required this.approvedAt,
    required this.expiresAt,
    this.releasedAt,
    this.releasedBy,
    this.releaseReason,
    this.note,
  });

  BlacklistEntryItem copyWith({
    DateTime? expiresAt,
    DateTime? releasedAt,
    String? releasedBy,
    String? releaseReason,
  }) {
    return BlacklistEntryItem(
      entryId: entryId,
      customerRef: customerRef,
      requestId: requestId,
      approvedAt: approvedAt,
      expiresAt: expiresAt ?? this.expiresAt,
      releasedAt: releasedAt ?? this.releasedAt,
      releasedBy: releasedBy ?? this.releasedBy,
      releaseReason: releaseReason ?? this.releaseReason,
      note: note,
    );
  }
}

class KnowledgeGapEntry {
  final String callId;
  final String query;
  final bool found;
  final DateTime loggedAt;

  const KnowledgeGapEntry({
    required this.callId,
    required this.query,
    required this.found,
    required this.loggedAt,
  });
}

class CallGuardLogEntry {
  final String callId;
  final String category; // 폭언 · 욕설 · 위협
  final DateTime detectedAt;

  const CallGuardLogEntry({
    required this.callId,
    required this.category,
    required this.detectedAt,
  });
}
