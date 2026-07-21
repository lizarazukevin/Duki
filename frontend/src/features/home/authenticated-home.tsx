"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { SessionIdentity } from "@/features/auth/session-provider";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import { createApiClient } from "@/lib/api/client";

interface TaskNode {
  children: TaskNode[];
  task: {
    estimated_minutes: number | null;
    id: string;
    status: "pending" | "in_progress" | "completed" | "archived";
    title: string;
  };
}

function flattenTasks(nodes: TaskNode[]): TaskNode["task"][] {
  return nodes.flatMap((node) => [node.task, ...flattenTasks(node.children)]);
}

export function AuthenticatedHome() {
  const router = useRouter();
  const sessionProvider = useMemo(() => new SupabaseSessionProvider(), []);
  const [identity, setIdentity] = useState<SessionIdentity | null>();
  const [tasks, setTasks] = useState<TaskNode["task"][]>([]);

  useEffect(() => {
    sessionProvider
      .getIdentity()
      .then((currentIdentity) => {
        if (!currentIdentity) {
          router.replace("/");
          return;
        }
        setIdentity(currentIdentity);
        createApiClient(sessionProvider)
          .request<{ items: TaskNode[] }>("/api/v1/tasks")
          .then((response) => setTasks(flattenTasks(response.items)))
          .catch(() => setTasks([]));
      })
      .catch(() => router.replace("/"));
  }, [router, sessionProvider]);

  if (!identity) {
    return <main className="home-loading">Waking up Duky…</main>;
  }

  const openTasks = tasks.filter((task) =>
    ["pending", "in_progress"].includes(task.status),
  );
  const immediateTasks = openTasks.slice(0, 2);
  const plannedMinutes = openTasks.reduce(
    (total, task) => total + (task.estimated_minutes ?? 0),
    0,
  );
  const firstName = identity.displayName?.split(" ")[0] ?? "there";
  const duckMessage = immediateTasks[0]
    ? `“${immediateTasks[0].title}” looks like the clearest place to begin.`
    : "Your day has room. Want to talk through what matters?";

  async function signOut(): Promise<void> {
    await sessionProvider.signOut();
    router.replace("/");
  }

  return (
    <main className="home-page">
      <header className="home-header">
        <div>
          <p className="home-kicker">
            Today /{" "}
            {new Date().toLocaleDateString(undefined, { weekday: "long" })}
          </p>
          <h1>Hello, {firstName}.</h1>
        </div>
        <button onClick={signOut} type="button">
          Sign out
        </button>
      </header>

      <section className="duck-dialogue" aria-label="Duky's daily note">
        <div className="thought-bubble">{duckMessage}</div>
        <div className="home-duck-stage">
          <Image
            alt="Duky, your rubber duck planning partner"
            className="home-duck"
            height={1402}
            priority
            src="/images/duky-editorial.png"
            width={1122}
          />
        </div>
        <p>One honest next step is enough.</p>
      </section>

      <section className="quick-stats" aria-label="Today's quick statistics">
        <div>
          <strong>{openTasks.length}</strong>
          <span>Open</span>
        </div>
        <div>
          <strong>{plannedMinutes || "—"}</strong>
          <span>Planned min</span>
        </div>
        <div>
          <strong>
            {tasks.filter((task) => task.status === "completed").length}
          </strong>
          <span>Done</span>
        </div>
      </section>

      <section className="immediate-work" aria-labelledby="immediate-heading">
        <div className="section-heading">
          <p>Up next</p>
          <h2 id="immediate-heading">Immediate work</h2>
        </div>
        {immediateTasks.length ? (
          <ol>
            {immediateTasks.map((task, index) => (
              <li key={task.id}>
                <span>0{index + 1}</span>
                <strong>{task.title}</strong>
                <small>
                  {task.estimated_minutes
                    ? `${task.estimated_minutes} min`
                    : "Unestimated"}
                </small>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty-tasks">
            Nothing is pressing. Add a task or start a debrief.
          </p>
        )}
      </section>

      <nav className="home-nav" aria-label="Primary navigation">
        <button disabled type="button">
          Tasks
        </button>
        <button disabled type="button">
          Calendar
        </button>
        <a aria-current="page" href="/home">
          Duky
        </a>
        <button disabled type="button">
          Insights
        </button>
        <button disabled type="button">
          Profile
        </button>
      </nav>
    </main>
  );
}
