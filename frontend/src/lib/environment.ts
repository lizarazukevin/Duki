export interface PublicEnvironment {
  apiBaseUrl: string;
  supabasePublishableKey: string;
  supabaseUrl: string;
}

function requiredUrl(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(`${name} is required`);
  }

  const parsedUrl = new URL(value);
  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    throw new Error(`${name} must use HTTP or HTTPS`);
  }
  return parsedUrl.toString().replace(/\/$/, "");
}

function requiredValue(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

export function getPublicEnvironment(): PublicEnvironment {
  return {
    apiBaseUrl: requiredUrl(
      process.env.NEXT_PUBLIC_API_BASE_URL,
      "NEXT_PUBLIC_API_BASE_URL",
    ),
    supabaseUrl: requiredUrl(
      process.env.NEXT_PUBLIC_SUPABASE_URL,
      "NEXT_PUBLIC_SUPABASE_URL",
    ),
    supabasePublishableKey: requiredValue(
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    ),
  };
}
