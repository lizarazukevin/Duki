import type { ApiClient } from "@/lib/api/client";

export interface CalendarEvent {
  description: string | null;
  end_time: string;
  id: string;
  is_all_day: boolean;
  location: string | null;
  start_time: string;
  status: "confirmed" | "tentative" | "cancelled";
  title: string;
  transparency: "opaque" | "transparent";
}

interface CalendarEventPage {
  items: CalendarEvent[];
  next_cursor: string | null;
}

interface CalendarSyncResult {
  events_cancelled: number;
  events_upserted: number;
}

interface TaskCalendarEventResult {
  end_time: string | null;
  linked: boolean;
  provider_event_id: string | null;
  start_time: string | null;
  task_id: string;
}

export interface SchedulePlan {
  available_minutes: number;
  computed_mood_score: number;
  items: Array<{
    end_time: string;
    estimated_minutes: number;
    ranking_reason: "low_energy" | "balanced_energy" | "high_energy";
    start_time: string;
    task_id: string;
    title: string;
  }>;
  plan_date: string;
  scheduled_minutes: number;
  unscheduled: Array<{
    reason: "missing_estimate" | "no_fitting_block";
    task_id: string;
    title: string;
  }>;
}

export interface CalendarWindow {
  endTime: string;
  startTime: string;
}

export class CalendarApi {
  constructor(private readonly apiClient: ApiClient) {}

  listEvents(
    window: CalendarWindow,
    cursor?: string,
  ): Promise<CalendarEventPage> {
    const query = new URLSearchParams({
      end_time: window.endTime,
      limit: "100",
      start_time: window.startTime,
    });
    if (cursor) {
      query.set("cursor", cursor);
    }
    return this.apiClient.request<CalendarEventPage>(
      `/api/v1/calendar-events?${query.toString()}`,
    );
  }

  syncEvents(window: CalendarWindow): Promise<CalendarSyncResult> {
    return this.apiClient.request<CalendarSyncResult>(
      "/api/v1/calendar-events/sync",
      {
        body: JSON.stringify({
          end_time: window.endTime,
          start_time: window.startTime,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      },
    );
  }

  buildPlan(
    planDate: string,
    startTime: string,
    endTime: string,
  ): Promise<SchedulePlan> {
    return this.apiClient.request<SchedulePlan>("/api/v1/schedule-plans", {
      body: JSON.stringify({
        plan_date: planDate,
        start_time: startTime,
        end_time: endTime,
        minimum_block_minutes: 15,
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
  }

  saveTaskEvent(
    taskId: string,
    startTime?: string,
    endTime?: string,
  ): Promise<TaskCalendarEventResult> {
    return this.apiClient.request<TaskCalendarEventResult>(
      `/api/v1/tasks/${taskId}/calendar-event`,
      {
        body: JSON.stringify({
          end_time: endTime ?? null,
          start_time: startTime ?? null,
        }),
        headers: { "Content-Type": "application/json" },
        method: "PUT",
      },
    );
  }
}
