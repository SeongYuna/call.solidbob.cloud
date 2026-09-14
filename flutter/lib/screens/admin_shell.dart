// apps/admin의 AdminPanel.tsx 모바일판. 개인 실험(decisions/405).
import 'package:flutter/material.dart';

import '../data/admin_fixtures.dart';
import '../models/blacklist_models.dart';
import '../theme/app_theme.dart';
import 'tabs/audit_tab.dart';
import 'tabs/entries_tab.dart';
import 'tabs/gaps_tab.dart';
import 'tabs/qa_tab.dart';
import 'tabs/requests_tab.dart';
import 'tabs/settings_tab.dart';
import 'tabs/wallboard_tab.dart';

enum AdminTab { wallboard, requests, entries, qa, gaps, audit, settings }

const _tabLabels = {
  AdminTab.wallboard: '현황판',
  AdminTab.requests: '승인요청',
  AdminTab.entries: '블랙리스트',
  AdminTab.qa: 'QA 리뷰',
  AdminTab.gaps: '지식베이스 갭',
  AdminTab.audit: '감사 로그',
  AdminTab.settings: '설정',
};

const _tabIcons = {
  AdminTab.wallboard: Icons.dashboard_outlined,
  AdminTab.requests: Icons.inbox_outlined,
  AdminTab.entries: Icons.block_outlined,
  AdminTab.qa: Icons.fact_check_outlined,
  AdminTab.gaps: Icons.search_off_outlined,
  AdminTab.audit: Icons.history_outlined,
  AdminTab.settings: Icons.settings_outlined,
};

class AdminShell extends StatefulWidget {
  final String adminName;
  final bool isDark;
  final VoidCallback onToggleTheme;
  final VoidCallback onLogout;

  const AdminShell({
    super.key,
    required this.adminName,
    required this.isDark,
    required this.onToggleTheme,
    required this.onLogout,
  });

  @override
  State<AdminShell> createState() => _AdminShellState();
}

class _AdminShellState extends State<AdminShell> {
  AdminTab _tab = AdminTab.wallboard;

  final List<BlacklistRequestItem> _requests = List.of(seedRequests);
  late List<BlacklistEntryItem> _entries = List.of(seedEntries);
  int _veteranThresholdYears = 3;
  int _blacklistExpiryMonths = 6;

  int get _pendingCount => _requests.where((r) => r.status == BlacklistStatus.pending).length;
  int get _activeEntryCount => _entries.where((e) => e.releasedAt == null).length;

  void _decide(String requestId, bool approve, {int? expiryMonths}) {
    setState(() {
      final index = _requests.indexWhere((r) => r.requestId == requestId);
      if (index == -1) return;
      final target = _requests[index];
      _requests[index] = target.copyWith(
        status: approve ? BlacklistStatus.approved : BlacklistStatus.rejected,
        decidedBy: widget.adminName,
        decidedAt: DateTime.now(),
      );
      if (approve) {
        final months = expiryMonths ?? _blacklistExpiryMonths;
        final now = DateTime.now();
        _entries = [
          ..._entries,
          BlacklistEntryItem(
            entryId: 'ent-${target.requestId}',
            customerRef: target.customerRef,
            requestId: target.requestId,
            approvedAt: now,
            expiresAt: DateTime(now.year, now.month + months, now.day),
          ),
        ];
      }
    });
  }

  void _release(String entryId) {
    setState(() {
      final index = _entries.indexWhere((e) => e.entryId == entryId);
      if (index == -1) return;
      _entries[index] = _entries[index].copyWith(
        releasedAt: DateTime.now(),
        releasedBy: widget.adminName,
        releaseReason: '관리자 해제',
      );
    });
  }

  void _extend(String entryId, int months) {
    setState(() {
      final index = _entries.indexWhere((e) => e.entryId == entryId);
      if (index == -1) return;
      final now = DateTime.now();
      _entries[index] = _entries[index].copyWith(
        expiresAt: DateTime(now.year, now.month + months, now.day),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Scaffold(
      appBar: AppBar(
        title: const Text('관리자 화면'),
        actions: [
          IconButton(
            tooltip: widget.isDark ? '라이트 모드로 전환' : '다크 모드로 전환',
            icon: Icon(widget.isDark ? Icons.wb_sunny_outlined : Icons.nightlight_round),
            onPressed: widget.onToggleTheme,
          ),
          IconButton(
            tooltip: '${widget.adminName} 로그아웃',
            icon: const Icon(Icons.logout),
            onPressed: widget.onLogout,
          ),
          const SizedBox(width: 4),
        ],
      ),
      drawer: Drawer(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
                child: Text(
                  'CallGuard 관리자',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: c.text),
                ),
              ),
              const Divider(height: 1),
              for (final tab in AdminTab.values)
                ListTile(
                  leading: Icon(_tabIcons[tab]),
                  title: Text(_tabLabels[tab]!),
                  selected: _tab == tab,
                  trailing: _badgeFor(tab),
                  onTap: () {
                    setState(() => _tab = tab);
                    Navigator.of(context).pop();
                  },
                ),
            ],
          ),
        ),
      ),
      body: SafeArea(child: _buildBody()),
    );
  }

  Widget? _badgeFor(AdminTab tab) {
    final count = switch (tab) {
      AdminTab.requests => _pendingCount,
      AdminTab.entries => _activeEntryCount,
      _ => 0,
    };
    if (count == 0) return null;
    return CircleAvatar(radius: 11, child: Text('$count', style: const TextStyle(fontSize: 11)));
  }

  Widget _buildBody() {
    return switch (_tab) {
      AdminTab.wallboard => WallboardTab(
          completedCallsTotal: seedCompletedCallsTotal,
          callGuardTotal: seedCallGuardLog.length,
          pendingRequestCount: _pendingCount,
          activeEntryCount: _activeEntryCount,
        ),
      AdminTab.requests => RequestsTab(
          requests: _requests,
          defaultExpiryMonths: _blacklistExpiryMonths,
          onApprove: (id, months) => _decide(id, true, expiryMonths: months),
          onReject: (id) => _decide(id, false),
        ),
      AdminTab.entries => EntriesTab(
          entries: _entries,
          requests: _requests,
          defaultExpiryMonths: _blacklistExpiryMonths,
          onRelease: _release,
          onExtend: _extend,
        ),
      AdminTab.qa => const QaTab(),
      AdminTab.gaps => GapsTab(log: seedKnowledgeGapLog),
      AdminTab.audit => AuditTab(requests: _requests, entries: _entries),
      AdminTab.settings => SettingsTab(
          veteranThresholdYears: _veteranThresholdYears,
          onChangeVeteranThresholdYears: (v) => setState(() => _veteranThresholdYears = v),
          blacklistExpiryMonths: _blacklistExpiryMonths,
          onChangeBlacklistExpiryMonths: (v) => setState(() => _blacklistExpiryMonths = v),
        ),
    };
  }
}
