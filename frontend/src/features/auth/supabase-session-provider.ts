import "client-only";

import type { SessionProvider } from "@/features/auth/session-provider";
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

  async signOut(): Promise<void> {
    const { error } = await createSupabaseBrowserClient().auth.signOut();
    if (error) {
      throw new Error("The current session could not be cleared", {
        cause: error,
      });
    }
  }
}
