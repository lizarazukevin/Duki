import assert from "node:assert/strict";
import test from "node:test";
import { derivePkceChallenge } from "./pkce.ts";

test("derives the RFC 7636 S256 challenge", async () => {
  const verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";

  assert.equal(
    await derivePkceChallenge(verifier),
    "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
  );
});
