"use client";

import { useEffect, useRef, useState } from "react";
import { InteractiveDuck } from "@/features/home/interactive-duck";
import styles from "./focus-mode.module.css";

const FOCUS_SECONDS = 25 * 60;

function clock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

interface FocusModeProps {
  taskTitle?: string;
}

export function FocusMode({ taskTitle }: FocusModeProps) {
  const [open, setOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [remaining, setRemaining] = useState(FOCUS_SECONDS);
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!running) return;
    const interval = window.setInterval(() => {
      setRemaining((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [running]);

  useEffect(() => {
    if (!remaining) setRunning(false);
  }, [remaining]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  function reset(): void {
    setRunning(false);
    setRemaining(FOCUS_SECONDS);
  }

  function toggleRunning(): void {
    if (!remaining) {
      setRemaining(FOCUS_SECONDS);
      setRunning(true);
      return;
    }
    setRunning((current) => !current);
  }

  return (
    <>
      <button
        className={styles.launch}
        onClick={() => setOpen(true)}
        type="button"
      >
        Focus with Duky
      </button>
      {open ? (
        <section
          aria-labelledby="focus-heading"
          aria-modal="true"
          className={styles.overlay}
          role="dialog"
        >
          <button
            className={styles.close}
            onClick={() => {
              setOpen(false);
              setRunning(false);
            }}
            ref={closeButton}
            type="button"
          >
            Leave focus
          </button>
          <div className={styles.copy}>
            <p>One thing at a time</p>
            <h2 id="focus-heading">{taskTitle ?? "Choose your next step"}</h2>
          </div>
          <div className={styles.duckStage}>
            <InteractiveDuck />
          </div>
          <time dateTime={`PT${remaining}S`}>{clock(remaining)}</time>
          <div className={styles.actions}>
            <button onClick={toggleRunning} type="button">
              {running ? "Pause" : remaining ? "Begin" : "Again"}
            </button>
            <button onClick={reset} type="button">
              Reset
            </button>
          </div>
          <p className={styles.note}>Duky will stay here with you.</p>
        </section>
      ) : null}
    </>
  );
}
