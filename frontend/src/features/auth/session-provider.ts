export interface SessionIdentity {
  displayName: string | null;
  email: string;
}

export interface SessionTokens {
  accessToken: string;
  refreshToken: string;
}

export interface SessionProvider {
  getAccessToken(): Promise<string | null>;
  getIdentity(): Promise<SessionIdentity | null>;
  setSession(tokens: SessionTokens): Promise<void>;
  signOut(): Promise<void>;
}
