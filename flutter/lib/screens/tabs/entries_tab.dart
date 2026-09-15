// apps/admin의 EntriesTab.tsx 모바일판 — 오늘 만든 "신규/기존(재범)" 필터를 그대로 옮겼다.
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../models/blacklist_models.dart';
import '../../theme/app_theme.dart';

enum _EntryFilter { all, isNew, repeat }

bool _isRepeatOffender(BlacklistEntryItem entry, List<BlacklistEntryItem> all) {
  return all.any((e) => e.entryId != entry.entryId && e.customerRef == entry.customerRef);
}

class EntriesTab extends StatefulWidget {
  final List<BlacklistEntryItem> entries;
  final List<BlacklistRequestItem> requests;
  final int defaultExpiryMonths;
  final void Function(String entryId) onRelease;
  final void Function(String entryId, int months) onExtend;

  const EntriesTab({
    super.key,
    required this.entries,
    required this.requests,
    required this.defaultExpiryMonths,
    required this.onRelease,
    required this.onExtend,
  });

  @override
  State<EntriesTab> createState() => _EntriesTabState();
}

class _EntriesTabState extends State<EntriesTab> {
  _EntryFilter _filter = _EntryFilter.all;

  String _displayHint(BlacklistEntryItem entry) {
    final match = widget.requests.where((r) => r.requestId == entry.requestId);
    return match.isEmpty ? '****' : match.first.displayHint;
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final active = widget.entries.where((e) => e.releasedAt == null).toList();
    final released = widget.entries.where((e) => e.releasedAt != null).toList();

    final newCount = active.where((e) => !_isRepeatOffender(e, widget.entries)).length;
    final repeatCount = active.length - newCount;
    final filtered = active.where((e) {
      if (_filter == _EntryFilter.all) return true;
      final repeat = _isRepeatOffender(e, widget.entries);
      return _filter == _EntryFilter.repeat ? repeat : !repeat;
    }).toList();

    final dateFmt = DateFormat('yyyy.MM.dd');

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      children: [
        Text(
          '등록된 고객의 전화도 정상적으로 받습니다. 바뀌는 것은 근속 3년 이상 상담사에게 배정된다는 점 하나입니다.',
          style: TextStyle(color: c.muted, fontSize: 13, height: 1.5),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          children: [
            _FilterChip(label: '전체', count: active.length, selected: _filter == _EntryFilter.all,
                onTap: () => setState(() => _filter = _EntryFilter.all)),
            _FilterChip(label: '신규', count: newCount, selected: _filter == _EntryFilter.isNew,
                onTap: () => setState(() => _filter = _EntryFilter.isNew)),
            _FilterChip(label: '기존(재범)', count: repeatCount, selected: _filter == _EntryFilter.repeat,
                onTap: () => setState(() => _filter = _EntryFilter.repeat)),
          ],
        ),
        const SizedBox(height: 16),
        if (active.isEmpty)
          Text('등록된 고객이 없습니다.', style: TextStyle(color: c.muted))
        else if (filtered.isEmpty)
          Text(
            _filter == _EntryFilter.isNew ? '신규 등록된 고객이 없습니다.' : '기존(재범) 등록된 고객이 없습니다.',
            style: TextStyle(color: c.muted),
          )
        else
          ...filtered.map((entry) {
            final repeat = _isRepeatOffender(entry, widget.entries);
            return _EntryRow(
              entry: entry,
              displayHint: _displayHint(entry),
              isRepeat: repeat,
              defaultExpiryMonths: widget.defaultExpiryMonths,
              dateFmt: dateFmt,
              onRelease: () => widget.onRelease(entry.entryId),
              onExtend: (m) => widget.onExtend(entry.entryId, m),
            );
          }),
        if (released.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text('해제된 기록', style: TextStyle(fontWeight: FontWeight.w700, color: c.text)),
          const SizedBox(height: 8),
          for (final e in released)
            Opacity(
              opacity: 0.6,
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(_displayHint(e), style: GoogleFonts.jetBrainsMono()),
                subtitle: Text('${e.releasedBy ?? ''} · ${e.releaseReason ?? '사유 없음'}'),
              ),
            ),
        ],
      ],
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final int count;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip({required this.label, required this.count, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text('$label $count'),
      selected: selected,
      onSelected: (_) => onTap(),
    );
  }
}

class _EntryRow extends StatefulWidget {
  final BlacklistEntryItem entry;
  final String displayHint;
  final bool isRepeat;
  final int defaultExpiryMonths;
  final DateFormat dateFmt;
  final VoidCallback onRelease;
  final void Function(int months) onExtend;

  const _EntryRow({
    required this.entry,
    required this.displayHint,
    required this.isRepeat,
    required this.defaultExpiryMonths,
    required this.dateFmt,
    required this.onRelease,
    required this.onExtend,
  });

  @override
  State<_EntryRow> createState() => _EntryRowState();
}

class _EntryRowState extends State<_EntryRow> {
  late int _months = widget.defaultExpiryMonths;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.cardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(widget.displayHint, style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.w700)),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: widget.isRepeat ? c.warnBg : c.line.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    widget.isRepeat ? '기존(재범)' : '신규',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: widget.isRepeat ? c.warnFg : c.muted),
                  ),
                ),
                const Spacer(),
                Text(
                  '${widget.dateFmt.format(widget.entry.approvedAt)} 등록',
                  style: GoogleFonts.jetBrainsMono(color: c.muted, fontSize: 11),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${widget.dateFmt.format(widget.entry.expiresAt)} 만료',
              style: GoogleFonts.jetBrainsMono(color: c.muted, fontSize: 12),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                SizedBox(
                  width: 56,
                  child: TextFormField(
                    initialValue: '$_months',
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(isDense: true, contentPadding: EdgeInsets.all(8)),
                    onChanged: (v) {
                      final n = int.tryParse(v);
                      if (n != null && n >= 1) setState(() => _months = n);
                    },
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton(onPressed: () => widget.onExtend(_months), child: const Text('재설정')),
                const SizedBox(width: 8),
                OutlinedButton(onPressed: widget.onRelease, child: const Text('해제')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
