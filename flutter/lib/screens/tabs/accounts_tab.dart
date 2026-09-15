// "상담원 계정 생성" 탭 — requests_tab.dart 의 폼+목록 패턴을 그대로 따른다.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../models/account_models.dart';
import '../../theme/app_theme.dart';

class AccountsTab extends StatelessWidget {
  final List<AgentAccountItem> accounts;
  final String Function(String name, String loginId) onCreateAccount;

  const AccountsTab({
    super.key,
    required this.accounts,
    required this.onCreateAccount,
  });

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final sorted = List.of(accounts)..sort((a, b) => b.createdAt.compareTo(a.createdAt));

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _CreateAccountForm(onCreateAccount: onCreateAccount),
        const SizedBox(height: 20),
        Text('계정 목록', style: TextStyle(fontWeight: FontWeight.w700, color: c.text)),
        const SizedBox(height: 8),
        if (sorted.isEmpty)
          Text('생성된 계정이 없습니다.', style: TextStyle(color: c.muted))
        else
          ...sorted.map((a) => _AccountCard(account: a)),
      ],
    );
  }
}

class _CreateAccountForm extends StatefulWidget {
  final String Function(String name, String loginId) onCreateAccount;

  const _CreateAccountForm({required this.onCreateAccount});

  @override
  State<_CreateAccountForm> createState() => _CreateAccountFormState();
}

class _CreateAccountFormState extends State<_CreateAccountForm> {
  final _nameController = TextEditingController();
  final _loginIdController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _loginIdController.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _nameController.text.trim();
    final loginId = _loginIdController.text.trim();
    if (name.isEmpty || loginId.isEmpty) return;
    final password = widget.onCreateAccount(name, loginId);
    _nameController.clear();
    _loginIdController.clear();
    _showPasswordDialog(password);
  }

  void _showPasswordDialog(String password) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('임시 비밀번호 발급됨'),
          content: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Expanded(
                child: SelectableText(
                  password,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                ),
              ),
              IconButton(
                tooltip: '복사',
                icon: const Icon(Icons.copy_outlined),
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: password));
                  if (!dialogContext.mounted) return;
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    const SnackBar(content: Text('임시 비밀번호를 복사했습니다.')),
                  );
                },
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('닫기')),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('상담원 계정 생성', style: TextStyle(fontWeight: FontWeight.w700, color: c.text)),
            const SizedBox(height: 12),
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: '상담원 이름'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _loginIdController,
              decoration: const InputDecoration(labelText: '로그인 ID (이메일 또는 사번)'),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                FilledButton(onPressed: _submit, child: const Text('임시 비밀번호 생성')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _AccountCard extends StatelessWidget {
  final AgentAccountItem account;

  const _AccountCard({required this.account});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final fmt = DateFormat('yyyy.MM.dd HH:mm');
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(account.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(account.loginId, style: TextStyle(color: c.muted, fontSize: 12)),
                  const SizedBox(height: 4),
                  Text('생성 ${fmt.format(account.createdAt)}', style: TextStyle(color: c.muted, fontSize: 11)),
                ],
              ),
            ),
            const SizedBox(width: 12),
            _StatusBadge(mustChangePassword: account.mustChangePassword),
          ],
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final bool mustChangePassword;

  const _StatusBadge({required this.mustChangePassword});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final bg = mustChangePassword ? c.warnBg : c.okBg;
    final fg = mustChangePassword ? c.warnFg : c.okFg;
    final label = mustChangePassword ? '비밀번호 미변경' : '정상 사용 중';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Text(label, style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.w600)),
    );
  }
}
