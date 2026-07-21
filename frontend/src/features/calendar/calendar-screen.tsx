"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import { ApiError, createApiClient } from "@/lib/api/client";
import styles from "./calendar.module.css";
import {
  CalendarApi,
  type CalendarEvent,
  type SchedulePlan,
} from "./calendar-api";

type LoadState = "loading" | "ready" | "error";

function dayKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dayWindow(selectedDay: string) {
  const start = new Date(`${selectedDay}T00:00:00`);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return { endTime: end.toISOString(), startTime: start.toISOString() };
}

function shiftDay(selectedDay: string, amount: number): string {
  const date = new Date(`${selectedDay}T12:00:00`);
  date.setDate(date.getDate() + amount);
  return dayKey(date);
}

function localTimestamp(day: string, time: string): string {
  const local = new Date(`${day}T${time}:00`);
  const offset = -local.getTimezoneOffset();
  const sign = offset >= 0 ? "+" : "-";
  const hours = String(Math.floor(Math.abs(offset) / 60)).padStart(2, "0");
  const minutes = String(Math.abs(offset) % 60).padStart(2, "0");
  return `${day}T${time}:00${sign}${hours}:${minutes}`;
}

function eventTime(
  event: Pick<CalendarEvent, "end_time" | "is_all_day" | "start_time">,
): string {
  if (event.is_all_day) return "All day";
  const format = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${format.format(new Date(event.start_time))} – ${format.format(new Date(event.end_time))}`;
}

function eventDuration(event: CalendarEvent): string {
  const minutes = Math.max(
    0,
    Math.round(
      (new Date(event.end_time).getTime() -
        new Date(event.start_time).getTime()) /
        60_000,
    ),
  );
  if (minutes >= 60) {
    const hours = minutes / 60;
    return `${Number.isInteger(hours) ? hours : hours.toFixed(1)}h`;
  }
  return `${minutes}m`;
}

function readableError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "invalid_session") {
      return "Your session expired. Sign in again.";
    }
    if (error.code === "calendar_authorization_failed") {
      return "Google Calendar needs permission again. Sign out, then reconnect Google.";
    }
    if (error.code === "calendar_rate_limited") {
      return "Google Calendar is busy. Wait a moment, then try again.";
    }
  }
  return "The calendar could not be refreshed. What you already see is unchanged.";
}

export function CalendarScreen() {
  const router = useRouter();
  const sessionProvider = useMemo(() => new SupabaseSessionProvider(), []);
  const calendarApi = useMemo(
    () => new CalendarApi(createApiClient(sessionProvider)),
    [sessionProvider],
  );
  const latestRequest = useRef(0);
  const [selectedDay, setSelectedDay] = useState(() => dayKey(new Date()));
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [hasSynced, setHasSynced] = useState(false);
  const [workdayStart, setWorkdayStart] = useState("09:00");
  const [workdayEnd, setWorkdayEnd] = useState("17:00");
  const [plan, setPlan] = useState<SchedulePlan | null>(null);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [savingTaskId, setSavingTaskId] = useState<string | null>(null);
  const [savedTaskIds, setSavedTaskIds] = useState<Set<string>>(
    () => new Set(),
  );

  const loadEvents = useCallback(
    async (cursor?: string) => {
      const request = ++latestRequest.current;
      if (!cursor) setLoadState("loading");
      setErrorMessage(null);
      try {
        const page = await calendarApi.listEvents(
          dayWindow(selectedDay),
          cursor,
        );
        if (request !== latestRequest.current) return;
        setEvents((current) =>
          cursor ? [...current, ...page.items] : page.items,
        );
        setNextCursor(page.next_cursor);
        setLoadState("ready");
      } catch (error) {
        if (request !== latestRequest.current) return;
        if (error instanceof ApiError && error.code === "invalid_session") {
          router.replace("/");
          return;
        }
        setErrorMessage(readableError(error));
        setLoadState("error");
      }
    },
    [calendarApi, router, selectedDay],
  );

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  async function syncCalendar(): Promise<void> {
    setSyncing(true);
    setErrorMessage(null);
    try {
      await calendarApi.syncEvents(dayWindow(selectedDay));
      setHasSynced(true);
      await loadEvents();
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_session") {
        router.replace("/");
        return;
      }
      setErrorMessage(readableError(error));
    } finally {
      setSyncing(false);
    }
  }

  async function planDay(): Promise<void> {
    if (workdayEnd <= workdayStart) {
      setPlanError("The day must end after it starts.");
      return;
    }
    setPlanning(true);
    setPlanError(null);
    try {
      setPlan(
        await calendarApi.buildPlan(
          selectedDay,
          localTimestamp(selectedDay, workdayStart),
          localTimestamp(selectedDay, workdayEnd),
        ),
      );
    } catch (error) {
      if (error instanceof ApiError && error.code === "mood_not_found") {
        setPlanError("Check in with Duky on Home before planning this day.");
      } else {
        setPlanError("Duky could not plan this day yet. Please try again.");
      }
    } finally {
      setPlanning(false);
    }
  }

  async function addTaskToCalendar(
    item: SchedulePlan["items"][number],
  ): Promise<void> {
    setSavingTaskId(item.task_id);
    setPlanError(null);
    try {
      await calendarApi.saveTaskEvent(
        item.task_id,
        item.start_time,
        item.end_time,
      );
      setSavedTaskIds((current) => new Set(current).add(item.task_id));
      await loadEvents();
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_session") {
        router.replace("/");
        return;
      }
      setPlanError(
        error instanceof ApiError &&
          error.code === "calendar_authorization_failed"
          ? "Google Calendar needs permission again. Sign out, then reconnect Google."
          : "That task could not be added to Google Calendar. Please try again.",
      );
    } finally {
      setSavingTaskId(null);
    }
  }

  const visibleEvents = events.filter((event) => event.status !== "cancelled");
  const allDayEvents = visibleEvents.filter((event) => event.is_all_day);
  const timedEvents = visibleEvents.filter((event) => !event.is_all_day);
  const busyMinutes = timedEvents
    .filter((event) => event.transparency === "opaque")
    .reduce(
      (sum, event) =>
        sum +
        Math.max(
          0,
          (new Date(event.end_time).getTime() -
            new Date(event.start_time).getTime()) /
            60_000,
        ),
      0,
    );
  const displayDate = new Date(`${selectedDay}T12:00:00`);
  const period =
    new Date().getHours() >= 7 && new Date().getHours() < 19 ? "day" : "night";

  return (
    <main className={styles.page} data-period={period}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Primary calendar</p>
          <h1>Your day, with room to breathe.</h1>
        </div>
        <button
          className={styles.syncButton}
          disabled={syncing}
          onClick={syncCalendar}
          type="button"
        >
          {syncing ? "Syncing…" : "Sync Google"}
        </button>
      </header>

      <section className={styles.dayPicker} aria-label="Choose calendar day">
        <button
          aria-label="Previous day"
          onClick={() => setSelectedDay(shiftDay(selectedDay, -1))}
          type="button"
        >
          ←
        </button>
        <label>
          <span>
            {displayDate.toLocaleDateString(undefined, { weekday: "long" })}
          </span>
          <input
            aria-label="Selected day"
            onChange={(event) => {
              if (event.target.value) setSelectedDay(event.target.value);
            }}
            type="date"
            value={selectedDay}
          />
        </label>
        <button
          aria-label="Next day"
          onClick={() => setSelectedDay(shiftDay(selectedDay, 1))}
          type="button"
        >
          →
        </button>
      </section>

      <section className={styles.summary} aria-label="Calendar summary">
        <div>
          <strong>{visibleEvents.length}</strong>
          <span>events</span>
        </div>
        <div>
          <strong>
            {busyMinutes ? `${(busyMinutes / 60).toFixed(1)}h` : "—"}
          </strong>
          <span>busy</span>
        </div>
        <p>Leave breathing room, or give an important task a place today.</p>
      </section>

      {errorMessage ? (
        <div className={styles.error} role="alert">
          <p>{errorMessage}</p>
          <button onClick={() => void loadEvents()} type="button">
            Try again
          </button>
        </div>
      ) : null}

      <section className={styles.planner} aria-labelledby="planner-heading">
        <div className={styles.plannerHeading}>
          <div>
            <p>Plan around real space</p>
            <h2 id="planner-heading">Let Duky suggest the day</h2>
          </div>
          <button disabled={planning} onClick={planDay} type="button">
            {planning ? "Planning…" : "Suggest my day"}
          </button>
        </div>
        <p className={styles.planLogic}>
          Duky looks at gaps in your primary calendar. Overdue work comes first,
          then tasks that fit today’s energy; the closest deadlines break ties.
          Tasks need a time estimate, and “Available from” keeps future work out
          of today’s plan.
        </p>
        <div className={styles.workday}>
          <label>
            Day starts
            <input
              onChange={(event) => setWorkdayStart(event.target.value)}
              type="time"
              value={workdayStart}
            />
          </label>
          <label>
            Day ends
            <input
              onChange={(event) => setWorkdayEnd(event.target.value)}
              type="time"
              value={workdayEnd}
            />
          </label>
        </div>
        {planError ? (
          <p className={styles.planError} role="alert">
            {planError}
          </p>
        ) : null}
        {plan ? (
          <div className={styles.planResult}>
            <p>A focused plan shaped around your open time and energy.</p>
            {plan.items.length ? (
              <>
                <ol>
                  {plan.items.map((item) => (
                    <li key={item.task_id}>
                      <time>
                        {eventTime({
                          start_time: item.start_time,
                          end_time: item.end_time,
                          is_all_day: false,
                        })}
                      </time>
                      <strong>{item.title}</strong>
                      <button
                        disabled={
                          savingTaskId === item.task_id ||
                          savedTaskIds.has(item.task_id)
                        }
                        onClick={() => void addTaskToCalendar(item)}
                        type="button"
                      >
                        {savingTaskId === item.task_id
                          ? "Adding…"
                          : savedTaskIds.has(item.task_id)
                            ? "Added"
                            : "Add to Google"}
                      </button>
                    </li>
                  ))}
                </ol>
                <small>
                  Added tasks appear in this timeline and your primary Google
                  Calendar.
                </small>
              </>
            ) : (
              <p>No estimated task fits the open time yet.</p>
            )}
            {plan.unscheduled.length ? (
              <small>
                {plan.unscheduled.length} task
                {plan.unscheduled.length === 1 ? "" : "s"} still need an
                estimate or a larger opening.
              </small>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className={styles.timeline} aria-labelledby="timeline-heading">
        <div className={styles.sectionHeading}>
          <p>
            {displayDate.toLocaleDateString(undefined, {
              month: "long",
              day: "numeric",
            })}
          </p>
          <h2 id="timeline-heading">Timeline</h2>
        </div>

        {loadState === "loading" ? (
          <p className={styles.status} aria-live="polite">
            Reading your calendar…
          </p>
        ) : visibleEvents.length === 0 ? (
          <div className={styles.empty}>
            <strong>
              {hasSynced ? "The day is clear." : "Nothing saved for this day."}
            </strong>
            <p>
              {hasSynced
                ? "Protect the open space or give one task a home."
                : "Sync Google Calendar to check the latest schedule."}
            </p>
          </div>
        ) : (
          <>
            {allDayEvents.length ? (
              <div className={styles.allDay}>
                <span>All day</span>
                <ul>
                  {allDayEvents.map((event) => (
                    <li key={event.id}>{event.title}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <ol className={styles.eventList}>
              {timedEvents.map((event) => (
                <li key={event.id}>
                  <time dateTime={event.start_time}>{eventTime(event)}</time>
                  <article data-free={event.transparency === "transparent"}>
                    <div>
                      <strong>{event.title}</strong>
                      <span>
                        {eventDuration(event)} ·{" "}
                        {event.transparency === "opaque" ? "Busy" : "Free"}
                      </span>
                    </div>
                    {event.location ? <p>{event.location}</p> : null}
                    {event.status === "tentative" ? (
                      <small>Tentative</small>
                    ) : null}
                  </article>
                </li>
              ))}
            </ol>
            {nextCursor ? (
              <button
                className={styles.moreButton}
                onClick={() => void loadEvents(nextCursor)}
                type="button"
              >
                Load more events
              </button>
            ) : null}
          </>
        )}
      </section>
    </main>
  );
}
