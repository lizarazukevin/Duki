import Link from "next/link";
import styles from "./app-navigation.module.css";

export type AppDestination =
  | "tasks"
  | "calendar"
  | "home"
  | "insights"
  | "profile";

interface AppNavigationProps {
  active: AppDestination;
  period?: "day" | "night";
}

const destinations: ReadonlyArray<{
  href: string;
  id: AppDestination;
  label: string;
}> = [
  { href: "/tasks", id: "tasks", label: "Tasks" },
  { href: "/calendar", id: "calendar", label: "Calendar" },
  { href: "/home", id: "home", label: "Duky" },
  { href: "/insights", id: "insights", label: "Insights" },
  { href: "/profile", id: "profile", label: "Profile" },
];

export function AppNavigation({ active, period }: AppNavigationProps) {
  return (
    <nav
      className={styles.navigation}
      aria-label="Primary navigation"
      data-period={period}
    >
      {destinations.map((destination) => (
        <Link
          aria-current={destination.id === active ? "page" : undefined}
          className={destination.id === active ? styles.active : undefined}
          href={destination.href}
          key={destination.id}
        >
          {destination.label}
        </Link>
      ))}
    </nav>
  );
}
