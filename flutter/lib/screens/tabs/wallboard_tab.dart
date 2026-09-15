import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

class WallboardTab extends StatelessWidget {
  final int completedCallsTotal;
  final int callGuardTotal;
  final int pendingRequestCount;
  final int activeEntryCount;

  const WallboardTab({
    super.key,
    required this.completedCallsTotal,
    required this.callGuardTotal,
    required this.pendingRequestCount,
    required this.activeEntryCount,
  });

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      children: [
        Text(
          '백엔드 연동 전이라 mock 시드 값 + 이 세션에서 처리한 건수입니다. '
          '실시간 통화 현황은 상담원 앱과 분리돼 있어 여기서 볼 수 없습니다.',
          style: TextStyle(color: c.muted, fontSize: 13, height: 1.5),
        ),
        const SizedBox(height: 16),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.3,
          children: [
            _Tile(label: '완료 통화 누적', value: completedCallsTotal),
            _Tile(label: '콜가드 경고 누적', value: callGuardTotal),
            _Tile(label: '승인 대기 요청', value: pendingRequestCount, emphasize: pendingRequestCount > 0),
            _Tile(label: '활성 블랙리스트 등록', value: activeEntryCount),
          ],
        ),
      ],
    );
  }
}

class _Tile extends StatelessWidget {
  final String label;
  final int value;
  final bool emphasize;

  const _Tile({required this.label, required this.value, this.emphasize = false});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Card(
      color: emphasize ? c.warnBg : null,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.cardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: TextStyle(color: emphasize ? c.warnFg : c.muted, fontSize: 13)),
            Text(
              '$value',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.w700,
                color: emphasize ? c.warnFg : c.text,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
