import type { ReactElement } from "react";
import { ClosingCTA } from "./components/ClosingCTA";
import { DemoScenario } from "./components/DemoScenario";
import { FeatureGrid } from "./components/FeatureGrid";
import { Hero } from "./components/Hero";
import { Nav } from "./components/Nav";
import { PrivacySection } from "./components/PrivacySection";
import { ValueComparison } from "./components/ValueComparison";
import { ThemeProvider } from "./theme";

export function App(): ReactElement {
  return (
    <ThemeProvider>
      <Nav />
      <main>
        <Hero />
        <ValueComparison />
        <DemoScenario />
        <FeatureGrid />
        <PrivacySection />
        <ClosingCTA />
      </main>
    </ThemeProvider>
  );
}
