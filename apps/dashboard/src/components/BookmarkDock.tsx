import type { ReactElement } from "react";
import { useCallStore } from "../store/callStore";

interface BookmarkDockProps {
  onJump: (index: number) => void;
}

export function BookmarkDock({ onJump }: BookmarkDockProps): ReactElement | null {
  const cards = useCallStore((state) =>
    state.viewMode === "history" ? state.historyCards : state.cards,
  );
  const tabs = cards
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => item.closure !== null && !item.settled);

  if (tabs.length === 0) {
    return null;
  }

  return (
    <div className="progress-tabs" role="tablist" aria-label="진행 중인 필요서류">
      {tabs.map(({ item, index }) => {
        const type = item.closure?.closure_type ?? "";
        return (
          <button
            key={`${type}-${index}`}
            type="button"
            role="tab"
            className="progress-tab"
            onClick={() => {
              onJump(index);
            }}
          >
            {`${type} · 진행중`}
            {item.closure?.is_example === true ? " · 예시" : ""}
          </button>
        );
      })}
    </div>
  );
}
