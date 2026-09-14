// apps/admin의 AdminLoginScreen.tsx 모바일판. 개인 실험이라 실제 구글 로그인은
// 연동하지 않는다 — 웹 쪽도 아직 GOOGLE_OAUTH_CLIENT_ID가 없어 같은 처지다
// (jekyll/open-items.markdown). 버튼을 누르면 바로 들어가는 자리채움이다.
import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class LoginScreen extends StatelessWidget {
  final void Function(String name) onLogin;

  const LoginScreen({super.key, required this.onLogin});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 36),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'CallGuard 관리자',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '구글 계정으로 로그인한다. 회원가입은 없다 — 관리자로 등록된 계정만 들어올 수 있다.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: c.muted, fontSize: 13, height: 1.5),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'VITE_GOOGLE_OAUTH_CLIENT_ID가 아직 없어(웹도 동일) 실제 구글\n로그인은 이 개인 실험에 연동하지 않았다 — 버튼은 데모용 통과다.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: c.warnFg, fontSize: 12),
                  ),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: () => onLogin('개발자(모바일 데모)'),
                    icon: const Icon(Icons.login),
                    label: const Text('Google로 로그인 (데모)'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
