import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../models/blacklist_models.dart';
import '../../theme/app_theme.dart';

class RequestsTab extends StatelessWidget {
  final List<BlacklistRequestItem> requests;
  final int defaultExpiryMonths;
  final void Function(String requestId, int expiryMonths) onApprove;
  final void Function(String requestId) onReject;

  const RequestsTab({
    super.key,
    required this.requests,
    required this.defaultExpiryMonths,
    required this.onApprove,
    required this.onReject,
  });

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final pending = requests.where((r) => r.status == BlacklistStatus.pending).toList();
    final decided = requests.where((r) => r.status != BlacklistStatus.pending).toList();

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      children: [
        if (pending.isEmpty)
          Text('대기 중인 요청이 없습니다.', style: TextStyle(color: c.muted))
        else
          ...pending.map(
            (r) => _RequestCard(
              request: r,
              defaultExpiryMonths: defaultExpiryMonths,
              onApprove: (months) => onApprove(r.requestId, months),
              onReject: () => onReject(r.requestId),
            ),
          ),
        if (decided.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text('처리된 요청', style: TextStyle(fontWeight: FontWeight.w700, color: c.text)),
          const SizedBox(height: 8),
          for (final r in decided)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                r.status == BlacklistStatus.approved ? Icons.check_circle : Icons.cancel,
                color: r.status == BlacklistStatus.approved ? c.okFg : c.muted,
              ),
              title: Text(r.displayHint, style: GoogleFonts.jetBrainsMono()),
              subtitle: Text('${r.status == BlacklistStatus.approved ? '승인' : '반려'} · ${r.decidedBy ?? ''}'),
            ),
        ],
      ],
    );
  }
}

class _RequestCard extends StatefulWidget {
  final BlacklistRequestItem request;
  final int defaultExpiryMonths;
  final void Function(int months) onApprove;
  final VoidCallback onReject;

  const _RequestCard({
    required this.request,
    required this.defaultExpiryMonths,
    required this.onApprove,
    required this.onReject,
  });

  @override
  State<_RequestCard> createState() => _RequestCardState();
}

class _RequestCardState extends State<_RequestCard> {
  late int _months = widget.defaultExpiryMonths;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final r = widget.request;
    final abuse = r.evidence.abuseTotal;
    final minutes = (r.evidence.callDurationS / 60).round();

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.cardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(r.displayHint, style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.w700)),
                Text('${r.requestedBy} · 통화 $minutes분', style: TextStyle(color: c.muted, fontSize: 12)),
              ],
            ),
            if (r.evidence.hasDistress) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: c.warnBg, borderRadius: BorderRadius.circular(10)),
                child: Text(
                  '⚠ 이 통화에 위기 신호 ${r.evidence.distressCount}건이 있습니다. '
                  '폭언과 다른 상황일 수 있어 전환 근거에서 제외했습니다 — 전문 상담 기관 연결을 먼저 검토해 주세요.',
                  style: TextStyle(color: c.warnFg, fontSize: 12),
                ),
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                _EvidenceStat(label: '폭언·위협', value: '$abuse건'),
                _EvidenceStat(label: '통화 온도 이상', value: '${r.evidence.temperatureOutliers}건'),
                _EvidenceStat(label: '통화 시간', value: '$minutes분'),
              ],
            ),
            const SizedBox(height: 12),
            Text('상담원 사유', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: c.muted)),
            Text(r.reason),
            const SizedBox(height: 8),
            Text('대화 맥락', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: c.muted)),
            Text(r.contextExcerpt, style: const TextStyle(fontStyle: FontStyle.italic)),
            const SizedBox(height: 12),
            Row(
              children: [
                Text('승인 시 등록 기간(개월)', style: TextStyle(color: c.muted, fontSize: 12)),
                const SizedBox(width: 8),
                SizedBox(
                  width: 64,
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
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(onPressed: widget.onReject, child: const Text('반려')),
                const SizedBox(width: 8),
                FilledButton(onPressed: () => widget.onApprove(_months), child: const Text('승인')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _EvidenceStat extends StatelessWidget {
  final String label;
  final String value;

  const _EvidenceStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(color: c.muted, fontSize: 11)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
      ],
    );
  }
}
