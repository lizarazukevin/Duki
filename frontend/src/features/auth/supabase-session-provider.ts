import "client-only";

import type {
  SessionIdentity,
  SessionProvider,
  SessionTokens,
} from "@/features/auth/session-provider";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export class SupabaseSessionProvider implements SessionProvider {
  async getAccessToken(): Promise<string | null> {
    const { data, error } =
      await createSupabaseBrowserClient().auth.getSession();
    if (error) {
      throw new Error("The current session could not be loaded", {
        cause: error,
      });
    }
    return data.session?.access_token ?? null;
  }

  async getIdentity(): Promise<SessionIdentity | null> {
    const { data, error } = await createSupabaseBrowserClient().auth.getUser();
    if (error || !data.user?.email) {
      return null;
    }
    const displayName = data.user.user_metadata.full_name;
    return {
      displayName: typeof displayName === "string" ? displayName : null,
      email: data.user.email,
    };
  }

  async setSession(tokens: SessionTokens): Promise<void> {
    const { error } = await createSupabaseBrowserClient().auth.setSession({
      access_token: tokens.accessToken,
      refresh_token: tokens.refreshToken,
    });
    if (error) {
      throw new Error("The new session could not be saved", { cause: error });
    }
  }

  async signOut(): Promise<void> {
    const { error } = await createSupabaseBrowserClient().auth.signOut();
    if (error) {
      throw new Error("The current session could not be cleared", {
        cause: error,
      });
    }
  }
}
