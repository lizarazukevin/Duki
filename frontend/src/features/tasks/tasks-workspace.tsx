"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import { AudioDebrief } from "@/features/duck-sessions/audio-debrief";
import { createApiClient } from "@/lib/api/client";
import { createTaskApi } from "./task-api";
import styles from "./tasks.module.css";
import type {
  FlatTask,
  Goal,
  Task,
  TaskCategory,
  TaskDraft,
  TaskNode,
} from "./types";

type Filter = "open" | "today" | TaskCategory | `goal:${string}`;

const emptyDraft: TaskDraft = {
  parent_task_id: null,
  title: "",
  description: null,
  category: "work",
  estimated_minutes: null,
  initial_easiness_score: null,
  easiness_source: null,
  scheduled_date: null,
  due_at: null,
  position: 0,
};

function flatten(nodes: TaskNode[], depth = 0): FlatTask[] {
  return nodes.flatMap(({ task, children }) => [
    { task, depth },
    ...flatten(children, depth + 1),
  ]);
}

function localDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function localDateFromIso(timestamp: string | null): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

export function TasksWorkspace() {
  const api = useMemo(() => {
    const session = new SupabaseSessionProvider();
    return createTaskApi(createApiClient(session));
  }, []);
  const [tasks, setTasks] = useState<FlatTask[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [filter, setFilter] = useState<Filter>("open");
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState<TaskDraft>(emptyDraft);
  const [selectedGoalIds, setSelectedGoalIds] = useState<string[]>([]);
  const [newGoalTitle, setNewGoalTitle] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [completing, setCompleting] = useState<Task | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const titleInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [taskTree, goalList] = await Promise.all([
        api.list(),
        api.listGoals(),
      ]);
      setTasks(flatten(taskTree));
      setGoals(goalList.filter((goal) => goal.status === "active"));
    } catch {
      setError("Tasks could not be loaded. Try again in a moment.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = tasks.filter(({ task }) => {
    if (["completed", "archived"].includes(task.status)) return false;
    const matchesQuery = [task.title, task.description]
      .filter(Boolean)
      .some((value) => value?.toLowerCase().includes(query.toLowerCase()));
    if (query && !matchesQuery) return false;
    if (filter === "open") return true;
    if (filter === "today") return task.scheduled_date === localDate();
    if (filter.startsWith("goal:")) {
      return task.goal_ids.includes(filter.slice(5));
    }
    return task.category === filter;
  });
  const filterHeading = filter.startsWith("goal:")
    ? (goals.find((goal) => goal.id === filter.slice(5))?.title ?? "Goal")
    : filter === "open"
      ? "Open work"
      : filter;

  function startCreate(): void {
    setEditing(null);
    setDraft(emptyDraft);
    setSelectedGoalIds([]);
    setComposerOpen(true);
    requestAnimationFrame(() => {
      titleInput.current?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
      titleInput.current?.focus();
    });
  }

  function startEdit(task: Task): void {
    setEditing(task);
    setDraft({
      parent_task_id: task.parent_task_id,
      title: task.title,
      description: task.description,
      category: task.category,
      estimated_minutes: task.estimated_minutes,
      initial_easiness_score: task.initial_easiness_score,
      easiness_source: task.easiness_source,
      scheduled_date: task.scheduled_date,
      due_at: task.due_at,
      position: task.position,
    });
    setSelectedGoalIds(task.goal_ids);
    setComposerOpen(true);
    requestAnimationFrame(() => titleInput.current?.focus());
  }

  function closeComposer(): void {
    setEditing(null);
    setComposerOpen(false);
    setDraft(emptyDraft);
    setSelectedGoalIds([]);
  }

  async function saveTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.title.trim()) return;
    setBusy(true);
    setError(null);
    let calendarWarning = false;
    try {
      const normalized = { ...draft, title: draft.title.trim() };
      const savedTask = editing
        ? await api.update(editing, normalized)
        : await api.create(normalized);
      if (editing) {
        try {
          await api.syncCalendar(savedTask.id);
        } catch {
          calendarWarning = true;
        }
      }
      const previousGoalIds = new Set(editing?.goal_ids ?? []);
      const nextGoalIds = new Set(selectedGoalIds);
      await Promise.all([
        ...selectedGoalIds
          .filter((goalId) => !previousGoalIds.has(goalId))
          .map((goalId) => api.attachGoal(savedTask.id, goalId)),
        ...(editing?.goal_ids ?? [])
          .filter((goalId) => !nextGoalIds.has(goalId))
          .map((goalId) => api.detachGoal(savedTask.id, goalId)),
      ]);
      closeComposer();
      await load();
      if (calendarWarning) {
        setError(
          "The task was saved, but its Google Calendar time could not be updated.",
        );
      }
    } catch {
      setError(
        "That task could not be saved. Check its details and try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createGoal(): Promise<void> {
    const title = newGoalTitle.trim();
    if (!title) return;
    setBusy(true);
    try {
      const goal = await api.createGoal(title);
      setGoals((current) => [...current, goal]);
      setSelectedGoalIds((current) => [...current, goal.id]);
      setNewGoalTitle("");
    } catch {
      setError("That goal could not be created. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function moveToToday(task: Task): Promise<void> {
    setBusy(true);
    setError(null);
    let calendarWarning = false;
    try {
      const savedTask = await api.update(task, { scheduled_date: localDate() });
      try {
        await api.syncCalendar(savedTask.id);
      } catch {
        calendarWarning = true;
      }
      await load();
      if (calendarWarning) {
        setError(
          "The task moved to today, but its Google Calendar time could not be updated.",
        );
      }
    } catch {
      setError("That task could not be moved to today.");
    } finally {
      setBusy(false);
    }
  }

  async function finishTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!completing) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await api.complete(completing.id, {
        actual_minutes: Number(form.get("actualMinutes")),
        actual_easiness_score: Number(form.get("actualEasiness")),
      });
      setCompleting(null);
      await load();
    } catch {
      setError(
        "Completion could not be recorded. Check the feedback and retry.",
      );
    } finally {
      setBusy(false);
    }
  }

  const period =
    new Date().getHours() >= 7 && new Date().getHours() < 19 ? "day" : "night";

  return (
    <main className={styles.page} data-period={period}>
      <header className={styles.header}>
        <div>
          <p>Your commitments</p>
          <h1>Tasks</h1>
        </div>
        <button
          className={styles.addButton}
          onClick={startCreate}
          type="button"
        >
          + Add task
        </button>
      </header>

      <nav className={styles.filters} aria-label="Filter tasks">
        {(["open", "today", "work", "chore", "personal"] as Filter[]).map(
          (item) => (
            <button
              aria-pressed={filter === item}
              key={item}
              onClick={() => setFilter(item)}
              type="button"
            >
              {item === "open" ? "All open" : item}
            </button>
          ),
        )}
        {goals.map((goal) => (
          <button
            aria-pressed={filter === `goal:${goal.id}`}
            key={goal.id}
            onClick={() => setFilter(`goal:${goal.id}`)}
            type="button"
          >
            {goal.title}
          </button>
        ))}
      </nav>

      <label className={styles.search}>
        <span>Search tasks</span>
        <input
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Find a task…"
          type="search"
          value={query}
        />
      </label>

      <AudioDebrief
        mode="capture"
        onComplete={load}
        taskTitles={Object.fromEntries(
          tasks.map(({ task }) => [task.id, task.title]),
        )}
      />

      {composerOpen ? (
        <section
          className={styles.composer}
          aria-label={editing ? "Edit task" : "Create a task"}
        >
          <form onSubmit={saveTask}>
            <input
              aria-label="Task title"
              maxLength={500}
              onChange={(event) =>
                setDraft({ ...draft, title: event.target.value })
              }
              placeholder="What needs doing?"
              ref={titleInput}
              required
              value={draft.title}
            />
            <div className={styles.formRow}>
              <label>
                <span>Category</span>
                <select
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      category: event.target.value as TaskCategory,
                    })
                  }
                  value={draft.category}
                >
                  <option value="work">Work</option>
                  <option value="chore">Chore</option>
                  <option value="personal">Personal</option>
                </select>
              </label>
              <label>
                <span>Estimate</span>
                <input
                  min="1"
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      estimated_minutes: event.target.value
                        ? Number(event.target.value)
                        : null,
                    })
                  }
                  placeholder="Minutes"
                  type="number"
                  value={draft.estimated_minutes ?? ""}
                />
              </label>
              <label>
                <span>Expected ease</span>
                <select
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      initial_easiness_score: event.target.value
                        ? Number(event.target.value)
                        : null,
                      easiness_source: event.target.value ? "user" : null,
                    })
                  }
                  value={draft.initial_easiness_score ?? ""}
                >
                  <option value="">Choose</option>
                  <option value="1">1 — Very hard</option>
                  <option value="2">2 — Hard</option>
                  <option value="3">3 — As expected</option>
                  <option value="4">4 — Easy</option>
                  <option value="5">5 — Very easy</option>
                </select>
              </label>
              <label>
                <span>Available from</span>
                <input
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      scheduled_date: event.target.value || null,
                    })
                  }
                  type="date"
                  value={draft.scheduled_date ?? ""}
                />
              </label>
              <label>
                <span>Deadline</span>
                <input
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      due_at: event.target.value
                        ? new Date(
                            `${event.target.value}T23:59:59`,
                          ).toISOString()
                        : null,
                    })
                  }
                  type="date"
                  value={localDateFromIso(draft.due_at)}
                />
              </label>
            </div>
            <fieldset className={styles.goalPicker}>
              <legend>Goal tags</legend>
              <div>
                {goals.map((goal) => (
                  <label key={goal.id}>
                    <input
                      checked={selectedGoalIds.includes(goal.id)}
                      onChange={(event) =>
                        setSelectedGoalIds((current) =>
                          event.target.checked
                            ? [...current, goal.id]
                            : current.filter((id) => id !== goal.id),
                        )
                      }
                      type="checkbox"
                    />
                    {goal.title}
                  </label>
                ))}
                <div className={styles.newGoal}>
                  <span>New goal</span>
                  <input
                    aria-label="New goal name"
                    maxLength={500}
                    onChange={(event) => setNewGoalTitle(event.target.value)}
                    placeholder="e.g. Launch"
                    value={newGoalTitle}
                  />
                  <button
                    disabled={busy || !newGoalTitle.trim()}
                    onClick={() => void createGoal()}
                    type="button"
                  >
                    Add
                  </button>
                </div>
              </div>
            </fieldset>
            <div className={styles.formActions}>
              <button onClick={closeComposer} type="button">
                Cancel
              </button>
              <button disabled={busy} type="submit">
                {editing ? "Save changes" : "Create task"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <section
        className={styles.list}
        aria-busy={loading}
        aria-label="Open tasks"
      >
        <div className={styles.listHeading}>
          <h2>{filterHeading}</h2>
          <span>{visible.length}</span>
        </div>
        {loading ? (
          <p className={styles.empty}>Gathering your tasks…</p>
        ) : visible.length === 0 ? (
          <p className={styles.empty}>
            Nothing here right now. Leave the space open or add one honest next
            step.
          </p>
        ) : (
          <ol>
            {visible.map(({ task, depth }) => (
              <li
                className={styles.task}
                key={task.id}
                style={{ "--depth": Math.min(depth, 3) } as React.CSSProperties}
              >
                <button
                  aria-label={`Complete ${task.title}`}
                  className={styles.check}
                  onClick={() => setCompleting(task)}
                  type="button"
                />
                <div className={styles.taskCopy}>
                  <strong>{task.title}</strong>
                  <span>
                    {task.category}
                    {task.estimated_minutes
                      ? ` · ${task.estimated_minutes} min`
                      : ""}
                    {task.due_at
                      ? ` · due ${new Date(task.due_at).toLocaleDateString()}`
                      : ""}
                  </span>
                  {task.goal_ids.length ? (
                    <small>
                      {task.goal_ids
                        .map((goalId) =>
                          goals.find((goal) => goal.id === goalId),
                        )
                        .filter((goal): goal is Goal => Boolean(goal))
                        .map((goal) => goal.title)
                        .join(" · ")}
                    </small>
                  ) : null}
                </div>
                <div className={styles.taskActions}>
                  {task.scheduled_date !== localDate() && (
                    <button
                      disabled={busy}
                      onClick={() => void moveToToday(task)}
                      type="button"
                    >
                      Today
                    </button>
                  )}
                  <button onClick={() => startEdit(task)} type="button">
                    Edit
                  </button>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {completing && (
        <div className={styles.overlay} role="presentation">
          <form className={styles.completion} onSubmit={finishTask}>
            <p>Finished</p>
            <h2>{completing.title}</h2>
            <div className={styles.baseline}>
              <span>
                Planned
                <strong>
                  {completing.estimated_minutes
                    ? `${completing.estimated_minutes} min`
                    : "Not estimated"}
                </strong>
              </span>
              <span>
                Expected ease
                <strong>
                  {completing.initial_easiness_score
                    ? `${completing.initial_easiness_score} / 5`
                    : "Not set"}
                </strong>
              </span>
            </div>
            <div className={styles.feedbackFields}>
              <label>
                <span>Actual minutes</span>
                <input
                  defaultValue={completing.estimated_minutes ?? 30}
                  min="1"
                  name="actualMinutes"
                  required
                  type="number"
                />
              </label>
              <label>
                <span>Actual easiness</span>
                <select
                  defaultValue={completing.initial_easiness_score ?? 3}
                  name="actualEasiness"
                >
                  <option value="1">1 — Very hard</option>
                  <option value="2">2 — Hard</option>
                  <option value="3">3 — As expected</option>
                  <option value="4">4 — Easy</option>
                  <option value="5">5 — Very easy</option>
                </select>
              </label>
            </div>
            <div className={styles.formActions}>
              <button onClick={() => setCompleting(null)} type="button">
                Not yet
              </button>
              <button disabled={busy} type="submit">
                Mark complete
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
