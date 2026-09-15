import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../models/blacklist_models.dart';
import '../../theme/app_theme.dart';

class _AuditEntry {
  final DateTime at;
  final String actor;
  final String action;
  final String detail;

  _AuditEntry({required this.at, required this.actor, required this.action, required this.detail});
}

class AuditTab extends StatelessWidget {
  final List<BlacklistRequestItem> requests;
  final List<BlacklistEntryItem> entries;

  const AuditTab({super.key, required this.requests, required this.entries});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final rows = <_AuditEntry>[];
    for (final r in requests) {
      if (r.status == BlacklistStatus.pending || r.decidedAt == null) continue;
      rows.add(_AuditEntry(
        at: r.decidedAt!,
        actor: r.decidedBy ?? '알 수 없음',
        action: r.status == BlacklistStatus.approved ? '승인' : '반려',
        detail: r.displayHint,
      ));
    }
    for (final e in entries) {
      if (e.releasedAt == null) continue;
      rows.add(_AuditEntry(
        at: e.releasedAt!,
        actor: e.releasedBy ?? '알 수 없음',
        action: '해제',
        detail: e.releaseReason ?? '사유 없음',
      ));
    }
    rows.sort((a, b) => b.at.compareTo(a.at));

    if (rows.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(AppSpacing.cardPadding),
        child: Text('아직 승인·반려·해제 이력이 없습니다.', style: TextStyle(color: c.muted)),
      );
    }

    final fmt = DateFormat('yyyy.MM.dd HH:mm');
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      children: [
        for (final row in rows)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: CircleAvatar(
              backgroundColor: row.action == '승인' ? c.okBg : c.line,
              child: Text(row.action[0], style: TextStyle(color: row.action == '승인' ? c.okFg : c.text)),
            ),
            title: Text('${row.detail} · ${row.actor}'),
            subtitle: Text(fmt.format(row.at), style: GoogleFonts.jetBrainsMono()),
          ),
      ],
    );
  }
}
