export interface SessionProvider {
  getAccessToken(): Promise<string | null>;
  signOut(): Promise<void>;
}
