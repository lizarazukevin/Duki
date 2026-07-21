import type { SessionProvider } from "@/features/auth/session-provider";
import { getPublicEnvironment } from "@/lib/environment";

interface ErrorEnvelope {
  code: string;
  details: Record<string, unknown>;
  error: string;
}

export class ApiError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly status: number;

  constructor(status: number, envelope: ErrorEnvelope) {
    super(envelope.error);
    this.name = "ApiError";
    this.status = status;
    this.code = envelope.code;
    this.details = envelope.details;
  }
}

export interface ApiClient {
  request<T>(path: string, init?: RequestInit): Promise<T>;
}

export function createApiClient(sessionProvider: SessionProvider): ApiClient {
  return {
    async request<T>(path: string, init: RequestInit = {}): Promise<T> {
      if (!path.startsWith("/")) {
        throw new Error("API paths must start with a slash");
      }

      const accessToken = await sessionProvider.getAccessToken();
      if (!accessToken) {
        throw new Error("An authenticated session is required");
      }

      const headers = new Headers(init.headers);
      headers.set("Authorization", `Bearer ${accessToken}`);
      const response = await fetch(
        `${getPublicEnvironment().apiBaseUrl}${path}`,
        { ...init, headers },
      );

      if (!response.ok) {
        throw new ApiError(response.status, await readErrorEnvelope(response));
      }
      if (response.status === 204) {
        return undefined as T;
      }
      return (await response.json()) as T;
    },
  };
}

async function readErrorEnvelope(response: Response): Promise<ErrorEnvelope> {
  try {
    const payload: unknown = await response.json();
    if (isErrorEnvelope(payload)) {
      return payload;
    }
  } catch {
    // A malformed upstream error is normalized below without exposing its body.
  }
  return {
    error: "The request could not be completed",
    code: "invalid_error_response",
    details: {},
  };
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ErrorEnvelope>;
  return (
    typeof candidate.error === "string" &&
    typeof candidate.code === "string" &&
    typeof candidate.details === "object" &&
    candidate.details !== null &&
    !Array.isArray(candidate.details)
  );
}
