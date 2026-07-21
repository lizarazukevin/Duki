"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { SessionIdentity } from "@/features/auth/session-provider";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import styles from "./profile-screen.module.css";

function getInitials(identity: SessionIdentity): string {
  const source = identity.displayName?.trim() || identity.email;
  return source
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function ProfileScreen() {
  const router = useRouter();
  const sessionProvider = useMemo(() => new SupabaseSessionProvider(), []);
  const [identity, setIdentity] = useState<SessionIdentity | null>();
  const [signOutError, setSignOutError] = useState<string | null>(null);

  useEffect(() => {
    sessionProvider
      .getIdentity()
      .then((currentIdentity) => {
        if (!currentIdentity) {
          router.replace("/");
          return;
        }
        setIdentity(currentIdentity);
      })
      .catch(() => router.replace("/"));
  }, [router, sessionProvider]);

  async function signOut(): Promise<void> {
    setSignOutError(null);
    try {
      await sessionProvider.signOut();
      router.replace("/");
    } catch {
      setSignOutError("Sign-out did not complete. Please try again.");
    }
  }

  if (!identity) {
    return <main className={styles.loading}>Loading your profile…</main>;
  }

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p>Account / private</p>
        <h1>Profile</h1>
      </header>

      <section className={styles.identity} aria-labelledby="identity-heading">
        <span className={styles.monogram} aria-hidden="true">
          {getInitials(identity)}
        </span>
        <div>
          <p id="identity-heading">Signed in as</p>
          <h2>{identity.displayName ?? "Duky member"}</h2>
          <span>{identity.email}</span>
        </div>
      </section>

      <section className={styles.details} aria-labelledby="details-heading">
        <div className={styles.sectionHeading}>
          <p>Daily defaults</p>
          <h2 id="details-heading">Your working rhythm</h2>
        </div>
        <dl>
          <div>
            <dt>Timezone</dt>
            <dd>{timezone || "Browser default"}</dd>
          </div>
          <div>
            <dt>Working hours</dt>
            <dd>Not configured</dd>
          </div>
          <div>
            <dt>Calendar selection</dt>
            <dd>Uses connected calendars</dd>
          </div>
        </dl>
        <p className={styles.note}>
          Soon, you’ll be able to shape Duky around your usual day.
        </p>
      </section>

      <section className={styles.security} aria-labelledby="security-heading">
        <div>
          <p>Access</p>
          <h2 id="security-heading">Google account connected</h2>
          <span>Your session and calendar access remain private to you.</span>
        </div>
        <button onClick={signOut} type="button">
          Sign out
        </button>
      </section>
      {signOutError ? (
        <p className={styles.error} role="alert">
          {signOutError}
        </p>
      ) : null}
    </main>
  );
}
