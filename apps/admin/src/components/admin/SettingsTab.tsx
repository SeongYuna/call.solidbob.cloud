import type { ReactElement } from "react";

/**
 * 설정. Twilio Flex의 "라우팅 설정"류를 본떴다 — 코드에 상수로 굳히지 않고
 * 화면에서 조정하게 뺀 값을 노출한다. J-5 베테랑 배정 기준(근속 연차)은
 * `_project/decisions/204`가 "조직마다 다르고 3년이 옳다는 근거가 없어
 * 설정으로 뺀다"고 정한 값인데, 실제 UI는 지금까지 없었다.
 *
 * ⚠ `server/apps/blacklist/domain/services/routing.py`(J-5 배정 로직)에는
 * 아직 안 꽂혀 있다 — 화면 표시·조정만 먼저 만들고, 서버 연동은 별도다.
 */
export function SettingsTab({
  veteranThresholdYears,
  onChangeVeteranThresholdYears,
}: {
  veteranThresholdYears: number;
  onChangeVeteranThresholdYears: (years: number) => void;
}): ReactElement {
  return (
    <section aria-label="설정">
      <div className="wrapup-card admin-settings-card">
        <div className="wrapup-card-head">
          <h3>J-5 베테랑 배정 기준</h3>
        </div>
        <label className="admin-settings-field">
          <span>근속 연차 (년) 이상이면 베테랑으로 배정</span>
          <input
            type="number"
            min={0}
            max={30}
            value={veteranThresholdYears}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next) && next >= 0) {
                onChangeVeteranThresholdYears(next);
              }
            }}
          />
        </label>
        <p className="admin-help">
          이 화면에서 바꿔도 실제 배정 로직(서버)에는 아직 연결돼 있지 않습니다
          — 값이 어떻게 보일지 먼저 확인하는 화면입니다.
        </p>
      </div>
    </section>
  );
}
