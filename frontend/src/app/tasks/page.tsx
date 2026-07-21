import { AppNavigation } from "@/features/navigation/app-navigation";
import { TasksWorkspace } from "@/features/tasks";

export default function TasksPage() {
  return (
    <>
      <TasksWorkspace />
      <AppNavigation active="tasks" />
    </>
  );
}
