import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

class QaTab extends StatelessWidget {
  const QaTab({super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          '상담 분위기가 "주의 필요"였거나 콜가드 경고가 뜬 통화입니다. '
          '상담원 평가가 아니라 다시 들어볼 통화를 고르는 목록입니다.',
          style: TextStyle(color: c.muted, fontSize: 13, height: 1.5),
        ),
        const SizedBox(height: 16),
        Text('리뷰가 필요한 통화가 없습니다.', style: TextStyle(color: c.muted)),
      ],
    );
  }
}
