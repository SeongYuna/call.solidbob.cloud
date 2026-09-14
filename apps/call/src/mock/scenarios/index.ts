import { LANGUAGE_META } from "../../lib/language/languageMeta";
import { accentKoScenario } from "./accentKo";
import { adminThScenario } from "./adminTh";
import { callGuardKoScenario } from "./callGuardKo";
import { covidZhScenario } from "./covidZh";
import { dasanScenario, maskingKoScenario } from "./dasan";
import { grantDelayKoScenario } from "./grantDelayKo";
import { sewerJaScenario } from "./sewerJa";
import { transitEnScenario } from "./transitEn";
import type { MockScenario } from "./types";

export type { MockScenario } from "./types";

/** mock 재생용. 게이트웨이 계약이 아니다. */
export type MockScenarioId =
  | "vi-deungbon"
  | "en-transit"
  | "ja-sewer"
  | "zh-covid"
  | "th-admin"
  | "ko-masking"
  | "ko-callguard"
  | "ko-grant-delay"
  | "ko-accent";

const BY_ID: Record<MockScenarioId, MockScenario> = {
  "vi-deungbon": dasanScenario,
  "en-transit": transitEnScenario,
  "ja-sewer": sewerJaScenario,
  "zh-covid": covidZhScenario,
  "th-admin": adminThScenario,
  "ko-masking": maskingKoScenario,
  "ko-callguard": callGuardKoScenario,
  "ko-grant-delay": grantDelayKoScenario,
  "ko-accent": accentKoScenario,
};

let selectedId: MockScenarioId = "vi-deungbon";

export function setSelectedMockScenarioId(id: MockScenarioId): void {
  selectedId = id;
}

export function getScenario(): MockScenario {
  return BY_ID[selectedId];
}

export function getScenarioById(id: MockScenarioId): MockScenario {
  return BY_ID[id];
}

export const MOCK_SCENARIO_FLAG: Record<MockScenarioId, string> = {
  "vi-deungbon": LANGUAGE_META.VI.flag,
  "en-transit": LANGUAGE_META.EN.flag,
  "ja-sewer": LANGUAGE_META.JA.flag,
  "zh-covid": LANGUAGE_META.ZH.flag,
  "th-admin": LANGUAGE_META.TH.flag,
  "ko-masking": "🇰🇷",
  "ko-callguard": "🇰🇷",
  "ko-grant-delay": "🇰🇷",
  "ko-accent": "🇰🇷",
};
