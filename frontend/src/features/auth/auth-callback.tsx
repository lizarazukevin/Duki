"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { BackendIdentityAuthorizationAdapter } from "@/features/auth/backend-auth-adapter";
import { AUTH_CODE_VERIFIER_KEY } from "@/features/auth/pkce";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";

export function AuthCallback() {
  const router = useRouter();
  const parameters = useSearchParams();
  const [message, setMessage] = useState("Finishing sign-in…");

  useEffect(() => {
    const code = parameters.get("code");
    const providerError = parameters.get("error_description");
    const verifier = sessionStorage.getItem(AUTH_CODE_VERIFIER_KEY);
    if (providerError || !code || !verifier) {
      setMessage(
        providerError ??
          "This sign-in attempt is incomplete. Return home and try again.",
      );
      return;
    }
    sessionStorage.removeItem(AUTH_CODE_VERIFIER_KEY);
    new BackendIdentityAuthorizationAdapter()
      .exchangeSession(code, verifier)
      .then((session) => new SupabaseSessionProvider().setSession(session))
      .then(() => router.replace("/home"))
      .catch(() => setMessage("Sign-in expired. Return home and try again."));
  }, [parameters, router]);

  return (
    <main className="callback-page">
      <p className="eyebrow">Duky / Secure handoff</p>
      <h1>{message}</h1>
      <a href="/">Return home</a>
    </main>
  );
}
