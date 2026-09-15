import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

class SettingsTab extends StatelessWidget {
  final int veteranThresholdYears;
  final void Function(int years) onChangeVeteranThresholdYears;
  final int blacklistExpiryMonths;
  final void Function(int months) onChangeBlacklistExpiryMonths;

  const SettingsTab({
    super.key,
    required this.veteranThresholdYears,
    required this.onChangeVeteranThresholdYears,
    required this.blacklistExpiryMonths,
    required this.onChangeBlacklistExpiryMonths,
  });

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('J-5 베테랑 배정 기준', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 10),
                _NumberField(
                  label: '근속 연차(년) 이상이면 베테랑으로 배정',
                  value: veteranThresholdYears,
                  onChanged: onChangeVeteranThresholdYears,
                ),
                const SizedBox(height: 8),
                Text(
                  '이 화면에서 바꿔도 실제 배정 로직(서버)에는 아직 연결돼 있지 않습니다.',
                  style: TextStyle(color: c.muted, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('J-4 블랙리스트 등록 만료 기간 — 기본값', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 10),
                _NumberField(
                  label: '승인 후 (개월) 뒤 자동 만료',
                  value: blacklistExpiryMonths,
                  onChanged: onChangeBlacklistExpiryMonths,
                ),
                const SizedBox(height: 8),
                Text(
                  '만료가 없으면 영구 표시가 됩니다. 이건 기본값일 뿐입니다 — 실제 기간은 '
                  '승인 카드나 블랙리스트 탭에서 건마다 조정합니다.',
                  style: TextStyle(color: c.muted, fontSize: 12, height: 1.4),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _NumberField extends StatelessWidget {
  final String label;
  final int value;
  final void Function(int) onChanged;

  const _NumberField({required this.label, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Row(
      children: [
        Expanded(child: Text(label, style: TextStyle(color: c.muted, fontSize: 13))),
        SizedBox(
          width: 64,
          child: TextFormField(
            initialValue: '$value',
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(isDense: true, contentPadding: EdgeInsets.all(8)),
            onChanged: (v) {
              final n = int.tryParse(v);
              if (n != null && n >= 0) onChanged(n);
            },
          ),
        ),
      ],
    );
  }
}
