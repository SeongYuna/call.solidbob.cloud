/// "상담원 계정 생성" 화면용 모델. 개인 실험(`_project/decisions/405`) —
/// 서버 계약과 동기화하지 않는다. 실제 붙일 땐 apps/admin 쪽을 정본으로 본다.
library;

class AgentAccountItem {
  final String id;
  final String name;
  final String loginId;
  final String tempPassword;
  final bool mustChangePassword;
  final DateTime createdAt;

  const AgentAccountItem({
    required this.id,
    required this.name,
    required this.loginId,
    required this.tempPassword,
    this.mustChangePassword = true,
    required this.createdAt,
  });

  AgentAccountItem copyWith({
    bool? mustChangePassword,
  }) {
    return AgentAccountItem(
      id: id,
      name: name,
      loginId: loginId,
      tempPassword: tempPassword,
      mustChangePassword: mustChangePassword ?? this.mustChangePassword,
      createdAt: createdAt,
    );
  }
}
