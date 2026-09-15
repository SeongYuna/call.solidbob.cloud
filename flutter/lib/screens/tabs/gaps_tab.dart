import 'package:flutter/material.dart';

import '../../models/blacklist_models.dart';
import '../../theme/app_theme.dart';

class _GapRow {
  final String query;
  int missCount = 0;
  int totalCount = 0;
  final Set<String> callIds = {};

  _GapRow(this.query);
}

class GapsTab extends StatelessWidget {
  final List<KnowledgeGapEntry> log;

  const GapsTab({super.key, required this.log});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final byQuery = <String, _GapRow>{};
    for (final entry in log) {
      final key = entry.query.trim();
      if (key.isEmpty) continue;
      final row = byQuery.putIfAbsent(key, () => _GapRow(key));
      row.totalCount += 1;
      if (!entry.found) row.missCount += 1;
      row.callIds.add(entry.callId);
    }
    final rows = byQuery.values.where((r) => r.missCount > 0).toList()
      ..sort((a, b) {
        final byMiss = b.missCount.compareTo(a.missCount);
        return byMiss != 0 ? byMiss : b.totalCount.compareTo(a.totalCount);
      });

    if (rows.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Text('아직 검색 실패로 기록된 질의가 없습니다.', style: TextStyle(color: c.muted)),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          '상담원이 직접 검색했는데 문서를 못 찾은 질의를 모은 것입니다. '
          '자동 추천이 놓친 것은 화면 밖이라 여기 안 잡힙니다.',
          style: TextStyle(color: c.muted, fontSize: 13, height: 1.5),
        ),
        const SizedBox(height: 16),
        for (final row in rows)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(row.query),
            subtitle: Text('실패 ${row.missCount}/${row.totalCount}건 · 통화 ${row.callIds.length}건'),
          ),
      ],
    );
  }
}
