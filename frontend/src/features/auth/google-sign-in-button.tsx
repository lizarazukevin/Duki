"use client";

import { useState } from "react";
import { BackendIdentityAuthorizationAdapter } from "@/features/auth/backend-auth-adapter";
import { AUTH_CODE_VERIFIER_KEY, createPkcePair } from "@/features/auth/pkce";

export function GoogleSignInButton() {
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function signIn(): Promise<void> {
    setMessage(null);
    setPending(true);
    try {
      const { challenge, verifier } = await createPkcePair();
      sessionStorage.setItem(AUTH_CODE_VERIFIER_KEY, verifier);
      const redirectTo = new URL("/auth/callback", window.location.origin);
      const url =
        await new BackendIdentityAuthorizationAdapter().getGoogleAuthorizationUrl(
          redirectTo.toString(),
          challenge,
        );
      window.location.assign(url);
    } catch {
      sessionStorage.removeItem(AUTH_CODE_VERIFIER_KEY);
      setMessage(
        "Sign-in could not start. Check that the Duky API is running.",
      );
      setPending(false);
    }
  }

  return (
    <div className="sign-in-action">
      <button
        className="google-button"
        disabled={pending}
        onClick={signIn}
        type="button"
      >
        <span aria-hidden="true" className="google-mark">
          G
        </span>
        <span>{pending ? "Opening Google…" : "Continue with Google"}</span>
        <span aria-hidden="true" className="button-arrow">
          ↗
        </span>
      </button>
      <p aria-live="polite" className="auth-message">
        {message}
      </p>
    </div>
  );
}
