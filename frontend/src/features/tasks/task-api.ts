import type { ApiClient } from "@/lib/api/client";
import type {
  CompletionFeedback,
  Goal,
  Task,
  TaskDraft,
  TaskNode,
} from "./types";

export interface TaskApi {
  attachGoal(taskId: string, goalId: string): Promise<void>;
  complete(taskId: string, feedback: CompletionFeedback): Promise<void>;
  create(draft: TaskDraft): Promise<Task>;
  createGoal(title: string): Promise<Goal>;
  detachGoal(taskId: string, goalId: string): Promise<void>;
  list(): Promise<TaskNode[]>;
  listGoals(): Promise<Goal[]>;
  syncCalendar(taskId: string): Promise<boolean>;
  update(task: Task, changes: Partial<TaskDraft>): Promise<Task>;
}

const jsonHeaders = { "Content-Type": "application/json" };

export function createTaskApi(client: ApiClient): TaskApi {
  return {
    async list() {
      return (await client.request<{ items: TaskNode[] }>("/api/v1/tasks"))
        .items;
    },
    async create(draft) {
      return client.request<Task>("/api/v1/tasks", {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify(draft),
      });
    },
    async listGoals() {
      return (await client.request<{ items: Goal[] }>("/api/v1/goals")).items;
    },
    async createGoal(title) {
      return client.request<Goal>("/api/v1/goals", {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ title, description: null, target_date: null }),
      });
    },
    async update(task, changes) {
      return client.request<Task>(`/api/v1/tasks/${task.id}`, {
        method: "PUT",
        headers: jsonHeaders,
        body: JSON.stringify({
          parent_task_id: task.parent_task_id,
          title: task.title,
          description: task.description,
          category: task.category,
          status: task.status,
          estimated_minutes: task.estimated_minutes,
          initial_easiness_score: task.initial_easiness_score,
          easiness_source: task.easiness_source,
          scheduled_date: task.scheduled_date,
          due_at: task.due_at,
          position: task.position,
          ...changes,
        }),
      });
    },
    async complete(taskId, feedback) {
      await client.request(`/api/v1/tasks/${taskId}/complete`, {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify(feedback),
      });
    },
    async syncCalendar(taskId) {
      const result = await client.request<{ linked: boolean }>(
        `/api/v1/tasks/${taskId}/calendar-event`,
        {
          method: "PUT",
          headers: jsonHeaders,
          body: JSON.stringify({ end_time: null, start_time: null }),
        },
      );
      return result.linked;
    },
    async attachGoal(taskId, goalId) {
      await client.request(`/api/v1/tasks/${taskId}/goals/${goalId}`, {
        method: "PUT",
      });
    },
    async detachGoal(taskId, goalId) {
      await client.request(`/api/v1/tasks/${taskId}/goals/${goalId}`, {
        method: "DELETE",
      });
    },
  };
}
