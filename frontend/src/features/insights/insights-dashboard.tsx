"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { type ApiClient, ApiError } from "@/lib/api/client";
import styles from "./insights-dashboard.module.css";

type TaskStatus = "pending" | "in_progress" | "completed" | "archived";

interface Task {
  completed_at: string | null;
  estimated_minutes: number | null;
  goal_ids: string[];
  id: string;
  status: TaskStatus;
}

interface TaskNode {
  children: TaskNode[];
  task: Task;
}

interface Goal {
  id: string;
  status: "active" | "completed" | "archived";
}

interface Mood {
  computed_mood_score: number;
  mood_date: string;
  reported_mood_score: number;
}

interface DaySummary {
  completed: number;
  date: Date;
  mood: Mood | null;
}

interface InsightsData {
  goals: Goal[];
  moods: Map<string, Mood>;
  tasks: Task[];
}

export interface InsightsDashboardProps {
  apiClient: ApiClient;
  onNavigate?: (destination: "home" | "tasks" | "calendar" | "profile") => void;
  referenceDate?: Date;
}

function flattenTasks(nodes: TaskNode[]): Task[] {
  return nodes.flatMap(({ children, task }) => [
    task,
    ...flattenTasks(children),
  ]);
}

function localDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getWeek(referenceDate: Date): Date[] {
  const end = new Date(
    referenceDate.getFullYear(),
    referenceDate.getMonth(),
    referenceDate.getDate(),
  );
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(end);
    date.setDate(end.getDate() - (6 - index));
    return date;
  });
}

async function loadMood(
  apiClient: ApiClient,
  date: Date,
): Promise<Mood | null> {
  try {
    return await apiClient.request<Mood>(`/api/v1/moods/${localDateKey(date)}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

async function loadInsights(
  apiClient: ApiClient,
  week: Date[],
): Promise<InsightsData> {
  const [taskTree, goalList, moodResults] = await Promise.all([
    apiClient.request<{ items: TaskNode[] }>("/api/v1/tasks"),
    apiClient.request<{ items: Goal[] }>("/api/v1/goals"),
    Promise.all(week.map((date) => loadMood(apiClient, date))),
  ]);
  return {
    tasks: flattenTasks(taskTree.items),
    goals: goalList.items,
    moods: new Map(
      moodResults.flatMap((mood) =>
        mood ? [[mood.mood_date, mood] as const] : [],
      ),
    ),
  };
}

export function InsightsDashboard({
  apiClient,
  onNavigate,
  referenceDate,
}: InsightsDashboardProps) {
  const [capturedReferenceDate] = useState(() => referenceDate ?? new Date());
  const week = useMemo(
    () => getWeek(capturedReferenceDate),
    [capturedReferenceDate],
  );
  const [data, setData] = useState<InsightsData | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  const refresh = useCallback(async () => {
    setLoadState("loading");
    try {
      setData(await loadInsights(apiClient, week));
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [apiClient, week]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const period =
    capturedReferenceDate.getHours() >= 7 &&
    capturedReferenceDate.getHours() < 19
      ? "day"
      : "night";

  if (loadState === "error") {
    return (
      <main className={styles.screen} data-period={period}>
        <section className={styles.errorPanel}>
          <p className={styles.errorMessage}>Insights are taking a breather.</p>
          <button type="button" onClick={() => void refresh()}>
            Try again
          </button>
        </section>
      </main>
    );
  }

  if (loadState === "loading" || !data) {
    return (
      <main className={styles.screen} data-period={period}>
        <p className={styles.status} aria-live="polite">
          Reading your week…
        </p>
      </main>
    );
  }

  const openTasks = data.tasks.filter(
    ({ status }) => status === "pending" || status === "in_progress",
  );
  const estimatedTasks = openTasks.filter(
    ({ estimated_minutes }) => estimated_minutes !== null,
  );
  const plannedMinutes = estimatedTasks.reduce(
    (total, task) => total + (task.estimated_minutes ?? 0),
    0,
  );
  const unestimatedCount = openTasks.length - estimatedTasks.length;
  const activeGoals = data.goals.filter(({ status }) => status === "active");
  const goalTaggedCount = openTasks.filter(
    ({ goal_ids }) => goal_ids.length > 0,
  ).length;
  const goalCoverage = openTasks.length
    ? Math.round((goalTaggedCount / openTasks.length) * 100)
    : 0;
  const summaries: DaySummary[] = week.map((date) => {
    const key = localDateKey(date);
    return {
      date,
      mood: data.moods.get(key) ?? null,
      completed: data.tasks.filter(
        ({ completed_at }) =>
          completed_at && localDateKey(new Date(completed_at)) === key,
      ).length,
    };
  });
  const completedThisWeek = summaries.reduce(
    (total, day) => total + day.completed,
    0,
  );
  const recordedMoods = summaries.flatMap(({ mood }) =>
    mood ? [mood.reported_mood_score] : [],
  );
  const averageMood = recordedMoods.length
    ? (
        recordedMoods.reduce((total, score) => total + score, 0) /
        recordedMoods.length
      ).toFixed(1)
    : "—";

  return (
    <main className={styles.screen} data-period={period}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Your patterns</p>
          <h1>Insights</h1>
        </div>
        <p className={styles.dateRange}>
          {week[0].toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
          –
          {week[6].toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
        </p>
      </header>

      <section className={styles.lead} aria-labelledby="week-heading">
        <div>
          <p className={styles.label}>This week</p>
          <h2 id="week-heading">
            {completedThisWeek
              ? `${completedThisWeek} task${completedThisWeek === 1 ? "" : "s"} moved forward.`
              : "A quiet week is still a week worth noticing."}
          </h2>
        </div>
        <div className={styles.moodSummary}>
          <strong>{averageMood}</strong>
          <span>avg. check-in</span>
          <small>{recordedMoods.length} of 7 days recorded</small>
        </div>
      </section>

      <section className={styles.week} aria-label="Seven-day quickview">
        {summaries.map(({ completed, date, mood }) => (
          <article className={styles.day} key={localDateKey(date)}>
            <span>
              {date.toLocaleDateString(undefined, { weekday: "narrow" })}
            </span>
            <div
              className={styles.moodMark}
              data-recorded={mood ? "true" : "false"}
              style={
                {
                  "--mood": mood?.reported_mood_score ?? 0,
                } as React.CSSProperties
              }
              title={
                mood
                  ? `Mood ${mood.reported_mood_score} of 5`
                  : "No mood check-in"
              }
            />
            <strong>{completed}</strong>
            <small>done</small>
          </article>
        ))}
      </section>

      <section className={styles.metrics} aria-label="Current workload">
        <article className={styles.metricPrimary}>
          <p className={styles.label}>Open workload</p>
          <strong>{plannedMinutes || "—"}</strong>
          <span>estimated minutes</span>
          <small>
            Based on {estimatedTasks.length} estimated task
            {estimatedTasks.length === 1 ? "" : "s"}
            {unestimatedCount ? ` · ${unestimatedCount} not estimated` : ""}
          </small>
        </article>
        <article className={styles.metric}>
          <p className={styles.label}>Goal connection</p>
          <strong>{goalCoverage}%</strong>
          <span>of open tasks tagged</span>
          <small>
            {activeGoals.length} active goal
            {activeGoals.length === 1 ? "" : "s"}
          </small>
        </article>
      </section>

      <section className={styles.future} aria-labelledby="deeper-heading">
        <div>
          <p className={styles.kicker}>Deeper patterns</p>
          <h2 id="deeper-heading">Patterns need time</h2>
        </div>
        <ul>
          <li>
            <span>Estimate accuracy</span>
            <small>Appears as you complete more tasks</small>
          </li>
          <li>
            <span>Mood interpretation</span>
            <small>Appears as your check-ins add up</small>
          </li>
          <li>
            <span>Break effectiveness</span>
            <small>Appears as Duky learns your rhythm</small>
          </li>
        </ul>
      </section>

      {onNavigate ? (
        <nav className={styles.nav} aria-label="Primary navigation">
          {(["tasks", "calendar", "home", "insights", "profile"] as const).map(
            (item) =>
              item === "insights" ? (
                <span aria-current="page" key={item}>
                  Insights
                </span>
              ) : (
                <button
                  key={item}
                  type="button"
                  onClick={() => onNavigate(item === "home" ? "home" : item)}
                >
                  {item === "home"
                    ? "Duky"
                    : `${item[0].toUpperCase()}${item.slice(1)}`}
                </button>
              ),
          )}
        </nav>
      ) : null}
    </main>
  );
}
