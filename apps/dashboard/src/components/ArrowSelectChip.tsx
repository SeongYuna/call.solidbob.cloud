import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";

export interface ArrowSelectOption<T extends string = string> {
  value: T;
  label: string;
  color?: string;
}

interface ArrowSelectChipSelectProps<T extends string> {
  options: readonly ArrowSelectOption<T>[];
  value: T;
  onChange: (value: T) => void;
  "aria-label"?: string;
  label?: never;
  children?: never;
}

interface ArrowSelectChipPanelProps {
  label: string;
  children: ReactNode;
  "aria-label"?: string;
  options?: never;
  value?: never;
  onChange?: never;
}

type ArrowSelectChipProps<T extends string> =
  | ArrowSelectChipSelectProps<T>
  | ArrowSelectChipPanelProps;

const closers = new Map<symbol, () => void>();

function closeOthers(self: symbol): void {
  for (const [id, close] of closers) {
    if (id !== self) {
      close();
    }
  }
}

export function ArrowSelectChip<T extends string>(
  props: ArrowSelectChipProps<T>,
): ReactElement {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const self = useRef(Symbol("arrow-select"));
  const menuId = useId();
  const isPanel = props.children !== undefined;
  const selected =
    props.options === undefined
      ? undefined
      : props.options.find((option) => option.value === props.value);
  const triggerLabel =
    props.label !== undefined
      ? props.label
      : (selected?.label ?? props.value ?? "");

  useEffect(() => {
    const id = self.current;
    closers.set(id, () => {
      setOpen(false);
    });
    return () => {
      closers.delete(id);
    };
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: PointerEvent): void {
      const root = rootRef.current;
      if (root !== null && !root.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function toggle(): void {
    if (open) {
      setOpen(false);
      return;
    }
    closeOthers(self.current);
    setOpen(true);
  }

  return (
    <div className={`arrow-select${open ? " is-open" : ""}`} ref={rootRef}>
      <button
        type="button"
        className="arrow-select-trigger"
        aria-label={props["aria-label"]}
        aria-haspopup={isPanel ? "dialog" : "listbox"}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={toggle}
      >
        {!isPanel && selected?.color !== undefined ? (
          <span
            className="arrow-select-dot"
            style={{ background: selected.color }}
            aria-hidden="true"
          />
        ) : null}
        <span className="arrow-select-label">{triggerLabel}</span>
        <ChevronIcon />
      </button>
      {open && isPanel ? (
        <div className="arrow-select-panel" id={menuId} role="dialog">
          {props.children}
        </div>
      ) : null}
      {open && props.options !== undefined ? (
        <ul className="arrow-select-menu" id={menuId} role="listbox">
          {props.options.map((option) => {
            const active = option.value === props.value;
            return (
              <li key={option.value} role="presentation">
                <button
                  type="button"
                  className={`arrow-select-option${active ? " is-active" : ""}`}
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    props.onChange?.(option.value);
                    setOpen(false);
                  }}
                >
                  {option.color !== undefined ? (
                    <span
                      className="arrow-select-dot"
                      style={{ background: option.color }}
                      aria-hidden="true"
                    />
                  ) : null}
                  <span>{option.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

function ChevronIcon(): ReactElement {
  return (
    <svg
      className="arrow-select-chevron"
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2.4 4.4 6 8l3.6-3.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
