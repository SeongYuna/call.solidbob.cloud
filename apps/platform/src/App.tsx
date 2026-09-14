import type { ReactElement } from "react";
import { ClosingCTA } from "./components/ClosingCTA";
import { DemoScenario } from "./components/DemoScenario";
import { FeatureGrid } from "./components/FeatureGrid";
import { Hero } from "./components/Hero";
import { Nav } from "./components/Nav";
import { PrivacySection } from "./components/PrivacySection";
import { ValueComparison } from "./components/ValueComparison";

// 2026-09-14 — 다크/라이트 토글을 뺐다(사용자 지시). 라이트 하나만 쓴다 —
// index.css의 :root가 그 값이고, 테마 전환 상태를 들고 있던 ThemeProvider도
// 같이 뺐다.
export function App(): ReactElement {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <ValueComparison />
        <DemoScenario />
        <FeatureGrid />
        <PrivacySection />
        <ClosingCTA />
      </main>
    </>
  );
}
