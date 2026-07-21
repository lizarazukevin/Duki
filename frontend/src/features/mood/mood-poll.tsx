"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import { ApiError, createApiClient } from "@/lib/api/client";
import styles from "./mood-poll.module.css";

interface DailyMood {
  computed_mood_score: number;
  mood_date: string;
  reported_mood_score: number;
}

interface MoodPollProps {
  onRecorded?: (mood: DailyMood) => void;
}

function localDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export function MoodPoll({ onRecorded }: MoodPollProps) {
  const apiClient = useMemo(
    () => createApiClient(new SupabaseSessionProvider()),
    [],
  );
  const [mood, setMood] = useState<DailyMood | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const current = await apiClient.request<DailyMood>(
        `/api/v1/moods/${localDate()}`,
      );
      setMood(current);
      onRecorded?.(current);
    } catch (loadError) {
      if (!(loadError instanceof ApiError && loadError.status === 404)) {
        setError("Your mood check-in is taking a breather.");
      }
    }
  }, [apiClient, onRecorded]);

  useEffect(() => {
    void load();
  }, [load]);

  async function record(score: number): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const current = await apiClient.request<DailyMood>("/api/v1/moods", {
        body: JSON.stringify({
          mood_date: localDate(),
          reported_mood_score: score,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      setMood(current);
      onRecorded?.(current);
    } catch {
      setError("That check-in did not save. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.poll} aria-labelledby="mood-heading">
      <div>
        <p>Right now</p>
        <h2 id="mood-heading">How’s your energy?</h2>
      </div>
      <div className={styles.scaleLabels} aria-hidden="true">
        <span>Drained</span>
        <span>Ready</span>
      </div>
      <fieldset className={styles.scores}>
        <legend>Choose energy from one, drained, to five, ready</legend>
        {[1, 2, 3, 4, 5].map((score) => (
          <button
            aria-label={`${score} out of 5`}
            aria-pressed={mood?.reported_mood_score === score}
            disabled={busy}
            key={score}
            onClick={() => void record(score)}
            type="button"
          >
            {score}
          </button>
        ))}
      </fieldset>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
