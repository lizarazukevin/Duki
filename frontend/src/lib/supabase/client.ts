import "client-only";

import { createBrowserClient } from "@supabase/ssr";
import { getPublicEnvironment } from "@/lib/environment";

let browserClient: ReturnType<typeof createBrowserClient> | undefined;

export function createSupabaseBrowserClient(): ReturnType<
  typeof createBrowserClient
> {
  if (!browserClient) {
    const environment = getPublicEnvironment();
    browserClient = createBrowserClient(
      environment.supabaseUrl,
      environment.supabasePublishableKey,
    );
  }
  return browserClient;
}
