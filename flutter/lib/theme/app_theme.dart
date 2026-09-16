/// apps/admin/src/index.css 의 :root 색 토큰을 옮겼다. 개인 실험(decisions/405).
library;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// apps/admin/src/index.css 의 치수 토큰(--radius-card·--pad-card·--radius-chip)을
/// 그대로 옮겼다. 색은 [AppColors]가 담당하고 이쪽은 라운드·여백만 다룬다.
class AppSpacing {
  const AppSpacing._();

  /// --radius-card (16px)
  static const double cardRadius = 16.0;

  /// --pad-card (24px)
  static const double cardPadding = 24.0;

  /// --radius-chip (10px)
  static const double chipRadius = 10.0;
}

class AppColors extends ThemeExtension<AppColors> {
  final Color bg;
  final Color text;
  final Color muted;
  final Color dim;
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
    required this.dim,
    required this.accent,
    required this.pii,
    required this.line,
    required this.shell,
    required this.okBg,
    required this.okFg,
    required this.warnBg,
    required this.warnFg,
  });

  // 화이트 + 블루 포인트 톤 (2026-09-16, 사용자 지시). bg/text/muted는 surface·기본/보조
  // 텍스트·기본/보조 아이콘을 겸한다(buildAppTheme의 iconTheme 참고). shell은 카드 배경 전용,
  // warnBg/warnFg는 "강조/포인트"(승인대기 등) 카드용 — accent(라벨용 옅은 톤)와 짝을 이룬다.
  static const light = AppColors(
    bg: Color(0xFFFFFFFF),
    text: Color(0xFF2C2C2A),
    muted: Color(0xFF5F5E5A),
    dim: Color(0xFF888780),
    accent: Color(0xFF185FA5),
    pii: Color(0xFFE24B4A),
    line: Color(0xFFE4E4E0),
    shell: Color(0xFFF7F7F3),
    okBg: Color(0xFFE7FBF8),
    okFg: Color(0xFF0F766E),
    warnBg: Color(0xFFE6F1FB),
    warnFg: Color(0xFF0C447C),
  );

  // 다크에서도 같은 화이트+블루 포인트 톤을 따른다(2026-09-16) — bg/text 등 중립 톤은
  // 그대로 두고, accent·warnBg·warnFg만 light와 같은 파란 계열로 옮겼다(teal·amber 대신).
  static const dark = AppColors(
    bg: Color(0xFF121410),
    text: Color(0xFFF3F0E8),
    muted: Color(0xFFA39E93),
    dim: Color(0xFF7A766C),
    accent: Color(0xFF4FA8E0),
    pii: Color(0xFFF0716E),
    line: Color(0xFF2E2C28),
    shell: Color(0xFF161512),
    okBg: Color(0xFF16332F),
    okFg: Color(0xFF7EE8D8),
    warnBg: Color(0xFF14283D),
    warnFg: Color(0xFF8EC6F5),
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
      dim: Color.lerp(dim, other.dim, t)!,
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
      surface: c.bg,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: c.bg,
      foregroundColor: c.text,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
    ),
    // 아이콘 기본 색 — 명시적으로 색을 지정하지 않은 Icon은 이 색을 따른다.
    iconTheme: IconThemeData(color: c.text),
    cardTheme: CardThemeData(
      color: c.shell,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
        side: BorderSide(color: c.line, width: 0.5),
      ),
    ),
    dividerColor: c.line,
    extensions: [c],
  );
}
