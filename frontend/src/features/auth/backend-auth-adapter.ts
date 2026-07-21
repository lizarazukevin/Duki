import type { SessionTokens } from "@/features/auth/session-provider";
import { getPublicEnvironment } from "@/lib/environment";

export class BackendIdentityAuthorizationAdapter {
  async getGoogleAuthorizationUrl(
    redirectTo: string,
    codeChallenge: string,
  ): Promise<string> {
    const response = await this.post<{ authorization_url: string }>(
      "/api/v1/auth/google/authorize",
      { redirect_to: redirectTo, code_challenge: codeChallenge },
    );
    return response.authorization_url;
  }

  async exchangeSession(
    authCode: string,
    authCodeVerifier: string,
  ): Promise<SessionTokens> {
    const response = await this.post<{
      access_token: string;
      refresh_token: string;
    }>("/api/v1/auth/sessions", {
      auth_code: authCode,
      auth_code_verifier: authCodeVerifier,
    });
    return {
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
    };
  }

  private async post<T>(path: string, body: object): Promise<T> {
    const response = await fetch(
      `${getPublicEnvironment().apiBaseUrl}${path}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      throw new Error("Authentication request failed");
    }
    return (await response.json()) as T;
  }
}
