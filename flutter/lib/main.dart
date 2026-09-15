// 개인 실험 — 관리자 화면(apps/admin) 모바일판. `_project/decisions/405` 참고.
// 팀 스코프 산출물이 아니다. CI·배포에 엮지 않는다.
import 'package:flutter/material.dart';

import 'screens/admin_shell.dart';
import 'screens/login_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const AdminMobileApp());
}

class AdminMobileApp extends StatefulWidget {
  const AdminMobileApp({super.key});

  @override
  State<AdminMobileApp> createState() => _AdminMobileAppState();
}

class _AdminMobileAppState extends State<AdminMobileApp> {
  ThemeMode _themeMode = ThemeMode.light;
  bool _loggedIn = false;
  String _adminName = '';

  void _toggleTheme() {
    setState(() {
      _themeMode = _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  void _login(String name) {
    setState(() {
      _loggedIn = true;
      _adminName = name;
    });
  }

  void _logout() {
    setState(() {
      _loggedIn = false;
      _adminName = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CallGuard 관리자',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: buildAppTheme(AppColors.light, Brightness.light),
      darkTheme: buildAppTheme(AppColors.dark, Brightness.dark),
      home: _loggedIn
          ? AdminShell(
              adminName: _adminName,
              isDark: _themeMode == ThemeMode.dark,
              onToggleTheme: _toggleTheme,
              onLogout: _logout,
            )
          : LoginScreen(onLogin: _login),
    );
  }
}
