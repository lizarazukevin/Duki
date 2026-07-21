export const AUTH_CODE_VERIFIER_KEY = "duky.auth_code_verifier";

function encodeBase64Url(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join(
    "",
  );
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

export async function derivePkceChallenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier),
  );
  return encodeBase64Url(new Uint8Array(digest));
}

export async function createPkcePair(): Promise<{
  challenge: string;
  verifier: string;
}> {
  const verifier = encodeBase64Url(crypto.getRandomValues(new Uint8Array(32)));
  return { verifier, challenge: await derivePkceChallenge(verifier) };
}
