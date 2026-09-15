/// apps/admin/src/index.css 의 :root 색 토큰을 옮겼다. 개인 실험(decisions/405).
library;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// apps/admin/src/index.css 의 치수 토큰(--radius-card·--pad-card·--radius-chip)을
/// 그대로 옮겼다. 색은 [AppColors]가 담당하고 이쪽은 라운드·여백만 다룬다.
class AppSpacing {
  const AppSpacing._();

  /// --radius-card (24px)
  static const double cardRadius = 24.0;

  /// --pad-card (24px)
  static const double cardPadding = 24.0;

  /// --radius-chip (10px)
  static const double chipRadius = 10.0;
}

class AppColors extends ThemeExtension<AppColors> {
  final Color bg;
  final Color text;
  final Color muted;
  final Color accent;
  final Color pii;
  final Color line;
  final Color shell;
  final Color okBg;
  final Color okFg;
  final Color warnBg;
  final Color warnFg;

  const AppColors({
    required this.bg,
    required this.text,
    required this.muted,
    required this.accent,
    required this.pii,
    required this.line,
    required this.shell,
    required this.okBg,
    required this.okFg,
    required this.warnBg,
    required this.warnFg,
  });

  static const light = AppColors(
    bg: Color(0xFFFAFAF9),
    text: Color(0xFF1A1A18),
    muted: Color(0xFF68675F),
    accent: Color(0xFF2DD4BF),
    pii: Color(0xFFE24B4A),
    line: Color(0xFFECECE7),
    shell: Color(0xFFFFFFFF),
    okBg: Color(0xFFE7FBF8),
    okFg: Color(0xFF0F766E),
    warnBg: Color(0xFFFFF4E0),
    warnFg: Color(0xFF92400E),
  );

  static const dark = AppColors(
    bg: Color(0xFF121410),
    text: Color(0xFFF3F0E8),
    muted: Color(0xFFA39E93),
    accent: Color(0xFF2DD4BF),
    pii: Color(0xFFF0716E),
    line: Color(0xFF2E2C28),
    shell: Color(0xFF161512),
    okBg: Color(0xFF16332F),
    okFg: Color(0xFF7EE8D8),
    warnBg: Color(0xFF3A2A10),
    warnFg: Color(0xFFF5B860),
  );

  @override
  AppColors copyWith() => this;

  @override
  AppColors lerp(ThemeExtension<AppColors>? other, double t) {
    if (other is! AppColors) return this;
    return AppColors(
      bg: Color.lerp(bg, other.bg, t)!,
      text: Color.lerp(text, other.text, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      pii: Color.lerp(pii, other.pii, t)!,
      line: Color.lerp(line, other.line, t)!,
      shell: Color.lerp(shell, other.shell, t)!,
      okBg: Color.lerp(okBg, other.okBg, t)!,
      okFg: Color.lerp(okFg, other.okFg, t)!,
      warnBg: Color.lerp(warnBg, other.warnBg, t)!,
      warnFg: Color.lerp(warnFg, other.warnFg, t)!,
    );
  }
}

extension AppColorsContext on BuildContext {
  AppColors get colors => Theme.of(this).extension<AppColors>() ?? AppColors.light;
}

ThemeData buildAppTheme(AppColors c, Brightness brightness) {
  return ThemeData(
    brightness: brightness,
    scaffoldBackgroundColor: c.bg,
    // apps/admin의 --font: "Inter" 대응. 밝기별 기본 TextTheme 위에 Inter를 입힌다.
    textTheme: GoogleFonts.interTextTheme(
      brightness == Brightness.dark ? ThemeData.dark().textTheme : ThemeData.light().textTheme,
    ),
    colorScheme: ColorScheme.fromSeed(
      seedColor: c.accent,
      brightness: brightness,
      primary: c.accent,
      surface: c.shell,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: c.shell,
      foregroundColor: c.text,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
    ),
    cardTheme: CardThemeData(
      color: c.shell,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
        side: BorderSide(color: c.line),
      ),
    ),
    dividerColor: c.line,
    extensions: [c],
  );
}
