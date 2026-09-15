// 개인 실험(decisions/405) 스모크 테스트 — 로그인 화면이 뜨고, 데모 로그인 버튼을 누르면
// 관리자 화면(현황판)으로 넘어가는지만 확인한다.
import 'package:flutter_test/flutter_test.dart';

import 'package:admin_mobile/main.dart';

void main() {
  testWidgets('로그인 화면 -> 데모 로그인 -> 관리자 화면(현황판)', (WidgetTester tester) async {
    await tester.pumpWidget(const AdminMobileApp());

    expect(find.text('CallGuard 관리자'), findsOneWidget);
    expect(find.text('Google로 로그인 (데모)'), findsOneWidget);

    await tester.tap(find.text('Google로 로그인 (데모)'));
    await tester.pumpAndSettle();

    expect(find.text('관리자 화면'), findsOneWidget);
    expect(find.text('완료 통화 누적'), findsOneWidget);
  });
}
