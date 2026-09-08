import { useEffect, useId, useState, type ReactElement } from "react";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "#realtime-assist", label: "실시간 어시스트" },
  { href: "#features", label: "기능" },
  { href: "#privacy", label: "개인정보 보호" },
  { href: "#stats", label: "도입 효과" },
] as const;

const DESKTOP_NAV_PX = 1080;

export function Nav(): ReactElement {
  const [open, setOpen] = useState(false);
  const menuId = useId();

  useEffect(() => {
    function onKey(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onResize(): void {
      if (window.innerWidth >= DESKTOP_NAV_PX) {
        setOpen(false);
      }
    }
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-page/80 backdrop-blur-md">
      <div className="relative mx-auto flex h-[72px] max-w-[1180px] items-center justify-between gap-3 px-5">
        <a href="#hero" className="relative z-10 flex min-w-0 items-center gap-2.5">
          <span className="text-[18px] font-semibold tracking-tight">
            <span className="text-fg">Call</span>
            <span className="text-amber">Guard</span>
          </span>
          <span className="hidden truncate text-[12.5px] text-muted sm:inline">
            서울시 다산콜센터
          </span>
        </a>
        <nav
          className="pointer-events-none absolute inset-x-5 hidden justify-center min-[1080px]:flex"
          aria-label="바로가기"
        >
          <div className="pointer-events-auto flex items-center gap-7 text-[14px] text-muted">
            {LINKS.map((link) => (
              <a key={link.href} href={link.href} className="hover:text-fg">
                {link.label}
              </a>
            ))}
          </div>
        </nav>
        <div className="relative z-10 flex items-center justify-end gap-2">
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-full border border-line text-muted hover:text-fg min-[1080px]:hidden"
            aria-expanded={open}
            aria-controls={menuId}
            aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
            onClick={() => {
              setOpen((value) => !value);
            }}
          >
            <MenuIcon open={open} />
          </button>
          <ThemeToggle />
          <a
            href="#cta"
            className="rounded-full bg-amber-fill px-4 py-2 text-[13px] font-semibold text-[#1a1408]"
          >
            도입 문의
          </a>
        </div>
      </div>
      {open ? (
        <nav
          id={menuId}
          className="border-t border-line bg-page px-5 py-3 min-[1080px]:hidden"
          aria-label="바로가기"
        >
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="block rounded-[10px] px-2 py-2.5 text-[14px] text-muted hover:bg-card hover:text-fg"
                  onClick={() => {
                    setOpen(false);
                  }}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </header>
  );
}

function MenuIcon({ open }: { open: boolean }): ReactElement {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden="true"
    >
      {open ? (
        <path d="M6 6l12 12M18 6 6 18" />
      ) : (
        <path d="M5 7h14M5 12h14M5 17h14" />
      )}
    </svg>
  );
}
