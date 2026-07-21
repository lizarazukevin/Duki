"use client";

import { useMemo } from "react";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import { InsightsDashboard } from "@/features/insights";
import { AppNavigation } from "@/features/navigation/app-navigation";
import { createApiClient } from "@/lib/api/client";

export default function InsightsPage() {
  const sessionProvider = useMemo(() => new SupabaseSessionProvider(), []);
  const apiClient = useMemo(
    () => createApiClient(sessionProvider),
    [sessionProvider],
  );

  return (
    <>
      <InsightsDashboard apiClient={apiClient} />
      <AppNavigation active="insights" />
    </>
  );
}
