import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "./theme";
import { App } from "./App";
import "./index.css";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("root 요소를 찾지 못했습니다.");
}

createRoot(root).render(
  <StrictMode>
    <ThemeProvider fallback="light">
      <App />
    </ThemeProvider>
  </StrictMode>,
);
