/// apps/admin/src/mock/adminFixtures.ts 그대로 이식. 개인 실험(decisions/405).
library;

import '../models/account_models.dart';
import '../models/blacklist_models.dart';

final List<AgentAccountItem> seedAgentAccounts = [
  AgentAccountItem(
    id: 'acc-seed-1',
    name: '박도윤',
    loginId: 'dyoon.park@dasan120.go.kr',
    tempPassword: 'aB3fK9pQ',
    createdAt: DateTime.parse('2026-09-09T10:00:00+09:00'),
  ),
  AgentAccountItem(
    id: 'acc-seed-2',
    name: '이수아',
    loginId: 'sooa.lee@dasan120.go.kr',
    tempPassword: 'x7Ln2WmZ',
    mustChangePassword: false,
    createdAt: DateTime.parse('2026-08-20T09:30:00+09:00'),
  ),
  AgentAccountItem(
    id: 'acc-seed-3',
    name: '정하윤',
    loginId: '20260091',
    tempPassword: 'Qw8eR4tY',
    createdAt: DateTime.parse('2026-09-12T14:10:00+09:00'),
  ),
];

final List<BlacklistRequestItem> seedRequests = [
  BlacklistRequestItem(
    requestId: 'req-seed-1',
    callId: 'c_seed_1',
    customerRef: 'hmac_seed_1',
    displayHint: '****3841',
    requestedBy: '조서희',
    reason: '상담 도중 반복적인 욕설과 위협이 있었습니다.',
    contextExcerpt: '고객: 이거 안 해주면 알아서 해\n고객: 계속 이따위로 할 거야',
    evidence: const BlacklistEvidence(
      callDurationS: 612,
      insultCount: 4,
      threatCount: 2,
      sexualCount: 0,
      distressCount: 0,
      temperatureOutliers: 3,
    ),
    status: BlacklistStatus.pending,
    requestedAt: DateTime.parse('2026-09-10T09:12:00+09:00'),
  ),
];

final List<BlacklistEntryItem> seedEntries = [
  BlacklistEntryItem(
    entryId: 'ent-seed-1',
    customerRef: 'hmac_seed_2',
    requestId: 'req-seed-0',
    approvedAt: DateTime.parse('2026-09-05T14:00:00+09:00'),
    expiresAt: DateTime.parse('2027-03-04T14:00:00+09:00'),
    note: '폭언 반복 확인 후 승인',
  ),
  // 재등록 예시 — "기존(재범)" 필터가 이 customer_ref를 잡는지 보여준다.
  BlacklistEntryItem(
    entryId: 'ent-seed-2-first',
    customerRef: 'hmac_seed_3',
    requestId: 'req-seed-2a',
    approvedAt: DateTime.parse('2026-07-01T10:00:00+09:00'),
    expiresAt: DateTime.parse('2026-08-01T10:00:00+09:00'),
    releasedAt: DateTime.parse('2026-08-01T10:00:00+09:00'),
    releasedBy: '정성윤',
    releaseReason: '만료 후 자동 해제',
    note: '1차 등록',
  ),
  BlacklistEntryItem(
    entryId: 'ent-seed-2-second',
    customerRef: 'hmac_seed_3',
    requestId: 'req-seed-2b',
    approvedAt: DateTime.parse('2026-09-08T11:30:00+09:00'),
    expiresAt: DateTime.parse('2027-03-08T11:30:00+09:00'),
    note: '해제 뒤 재범으로 재등록',
  ),
];

final List<KnowledgeGapEntry> seedKnowledgeGapLog = [
  KnowledgeGapEntry(
    callId: 'c_seed_2',
    query: '외국인 등록증 재발급',
    found: false,
    loggedAt: DateTime.parse('2026-09-09T10:00:00+09:00'),
  ),
  KnowledgeGapEntry(
    callId: 'c_seed_3',
    query: '외국인 등록증 재발급',
    found: false,
    loggedAt: DateTime.parse('2026-09-09T15:30:00+09:00'),
  ),
  KnowledgeGapEntry(
    callId: 'c_seed_4',
    query: '외국인 등록증 재발급',
    found: false,
    loggedAt: DateTime.parse('2026-09-10T08:20:00+09:00'),
  ),
  KnowledgeGapEntry(
    callId: 'c_seed_5',
    query: '체류지 변경 신고',
    found: false,
    loggedAt: DateTime.parse('2026-09-09T11:00:00+09:00'),
  ),
  KnowledgeGapEntry(
    callId: 'c_seed_6',
    query: '주민등록등본 발급 수수료',
    found: true,
    loggedAt: DateTime.parse('2026-09-09T12:00:00+09:00'),
  ),
];

final List<CallGuardLogEntry> seedCallGuardLog = [
  CallGuardLogEntry(
    callId: 'c_seed_1',
    category: '욕설',
    detectedAt: DateTime.parse('2026-09-10T09:05:00+09:00'),
  ),
  CallGuardLogEntry(
    callId: 'c_seed_1',
    category: '위협',
    detectedAt: DateTime.parse('2026-09-10T09:08:00+09:00'),
  ),
  CallGuardLogEntry(
    callId: 'c_seed_7',
    category: '폭언',
    detectedAt: DateTime.parse('2026-09-08T16:00:00+09:00'),
  ),
];

const int seedCompletedCallsTotal = 24;
