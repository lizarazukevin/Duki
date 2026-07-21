export type TaskCategory = "work" | "chore" | "personal";
export type TaskStatus = "pending" | "in_progress" | "completed" | "archived";

export interface Task {
  id: string;
  parent_task_id: string | null;
  title: string;
  description: string | null;
  category: TaskCategory;
  status: TaskStatus;
  estimated_minutes: number | null;
  initial_easiness_score: number | null;
  easiness_source: "user" | "inferred" | null;
  scheduled_date: string | null;
  due_at: string | null;
  position: number;
  completed_at: string | null;
  goal_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface TaskNode {
  task: Task;
  children: TaskNode[];
}

export interface TaskDraft {
  parent_task_id: string | null;
  title: string;
  description: string | null;
  category: TaskCategory;
  estimated_minutes: number | null;
  initial_easiness_score: number | null;
  easiness_source: "user" | "inferred" | null;
  scheduled_date: string | null;
  due_at: string | null;
  position: number;
}

export interface CompletionFeedback {
  actual_minutes: number;
  actual_easiness_score: number;
}

export interface FlatTask {
  task: Task;
  depth: number;
}

export interface Goal {
  id: string;
  status: "active" | "completed" | "archived";
  title: string;
}
