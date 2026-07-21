import { CalendarScreen } from "@/features/calendar";
import { AppNavigation } from "@/features/navigation/app-navigation";

export default function CalendarPage() {
  return (
    <>
      <CalendarScreen />
      <AppNavigation active="calendar" />
    </>
  );
}
