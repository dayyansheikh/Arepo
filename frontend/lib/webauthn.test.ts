import { describe, expect, it } from "vitest";
import {
  base64urlToBuffer,
  browserErrorMessage,
  bufferToBase64url,
  credentialToJSON,
  keyKindLabel,
  lockedDetail,
  recoveryCodesText,
  registerKey,
  toCreationOptions,
  toRequestOptions,
  unlockWithKey,
  type CredentialsLike,
} from "./webauthn";
import { actionForResult, loadLabDashboard } from "./lab/api";
import { auditSentence, loadMembers } from "./lab/members";

const bytes = (...xs: number[]) => new Uint8Array(xs).buffer;
const arr = (b: ArrayBuffer | BufferSource) => Array.from(new Uint8Array(b as ArrayBuffer));

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("base64url", () => {
  it("encodes without padding or +/ and round-trips every length", () => {
    expect(bufferToBase64url(bytes(0xfb, 0xff))).toBe("-_8");
    expect(bufferToBase64url(bytes())).toBe("");
    for (let n = 0; n < 40; n++) {
      const src = new Uint8Array(n).map((_, i) => (i * 37 + n) % 256);
      const enc = bufferToBase64url(src);
      expect(enc).not.toMatch(/[+/=]/);
      expect(arr(base64urlToBuffer(enc))).toEqual(Array.from(src));
    }
  });

  it("accepts typed-array views (respecting offset)", () => {
    const big = new Uint8Array([9, 1, 2, 3, 9]);
    expect(bufferToBase64url(big.subarray(1, 4))).toBe(bufferToBase64url(bytes(1, 2, 3)));
  });
});

const regOptions = {
  publicKey: {
    rp: { name: "Arepo Lab", id: "arepolabs.com" },
    user: { id: bufferToBase64url(bytes(1, 2, 3, 4)), name: "o@x.com", displayName: "o@x.com" },
    challenge: bufferToBase64url(bytes(9, 9, 9)),
    pubKeyCredParams: [{ type: "public-key", alg: -7 }],
    timeout: 120000,
    excludeCredentials: [{ id: bufferToBase64url(bytes(7, 7)), type: "public-key", transports: ["usb"] }],
    authenticatorSelection: { residentKey: "preferred", userVerification: "preferred" },
    attestation: "none",
  },
};

describe("option conversion", () => {
  it("decodes registration options for navigator.credentials.create", () => {
    const pk = toCreationOptions(regOptions).publicKey!;
    expect(arr(pk.challenge)).toEqual([9, 9, 9]);
    expect(arr(pk.user.id)).toEqual([1, 2, 3, 4]);
    expect(arr(pk.excludeCredentials![0].id)).toEqual([7, 7]);
    expect(pk.excludeCredentials![0].transports).toEqual(["usb"]);
    // No authenticatorAttachment: USB keys and platform passkeys are both allowed.
    expect(pk.authenticatorSelection).toEqual({ residentKey: "preferred", userVerification: "preferred" });
    expect(pk.rp.id).toBe("arepolabs.com");
  });

  it("decodes authentication options for navigator.credentials.get", () => {
    const pk = toRequestOptions({
      publicKey: {
        challenge: bufferToBase64url(bytes(5)),
        rpId: "arepolabs.com",
        allowCredentials: [
          { id: bufferToBase64url(bytes(1)), type: "public-key" },
          { id: bufferToBase64url(bytes(2)), type: "public-key", transports: ["internal", "hybrid"] },
        ],
        userVerification: "preferred",
      },
    }).publicKey!;
    expect(arr(pk.challenge)).toEqual([5]);
    expect(pk.allowCredentials!.map((c) => arr(c.id))).toEqual([[1], [2]]);
    expect(pk.userVerification).toBe("preferred");
  });
});

function fakeAssertion(): Credential {
  return {
    id: bufferToBase64url(bytes(2)),
    rawId: bytes(2),
    type: "public-key",
    authenticatorAttachment: "platform",
    response: {
      clientDataJSON: bytes(123, 125),
      authenticatorData: bytes(1, 1),
      signature: bytes(3, 3),
      userHandle: bytes(1, 2, 3, 4),
    },
    getClientExtensionResults: () => ({}),
  } as unknown as Credential;
}

function fakeAttestation(): Credential {
  return {
    id: bufferToBase64url(bytes(8)),
    rawId: bytes(8),
    type: "public-key",
    response: { clientDataJSON: bytes(123, 125), attestationObject: bytes(160), getTransports: () => ["internal", "hybrid"] },
    getClientExtensionResults: () => ({}),
  } as unknown as Credential;
}

describe("credentialToJSON", () => {
  it("serialises an assertion", () => {
    const j = credentialToJSON(fakeAssertion()) as { response: Record<string, string>; rawId: string };
    expect(j.rawId).toBe("Ag");
    expect(j.response).toEqual({
      clientDataJSON: bufferToBase64url(bytes(123, 125)),
      authenticatorData: "AQE",
      signature: "AwM",
      userHandle: "AQIDBA",
    });
  });

  it("serialises a registration with transports", () => {
    const j = credentialToJSON(fakeAttestation()) as { response: Record<string, unknown> };
    expect(j.response.attestationObject).toBe("oA");
    expect(j.response.transports).toEqual(["internal", "hybrid"]);
  });
});

describe("locked detection", () => {
  it("recognises the 403 hardware_key_required body", () => {
    expect(lockedDetail({ detail: { code: "hardware_key_required", message: "Tap", keys: 2 } })).toEqual({
      code: "hardware_key_required",
      message: "Tap",
      keys: 2,
    });
    expect(lockedDetail({ detail: "origin not allowed" })).toBeNull();
    expect(lockedDetail(null)).toBeNull();
  });

  it("lab dashboard maps it to the unlock screen", async () => {
    const res = await loadLabDashboard(async () =>
      jsonResponse(403, { detail: { code: "hardware_key_required", message: "Tap", keys: 1 } }),
    );
    expect(res).toEqual({ kind: "locked", keys: 1 });
    expect(actionForResult(res)).toEqual({ type: "locked", keys: 1 });
    const plain = await loadLabDashboard(async () => jsonResponse(403, { detail: "origin not allowed" }));
    expect(plain.kind).toBe("error");
  });

  it("members page maps it to the unlock screen", async () => {
    const res = await loadMembers(async () =>
      jsonResponse(403, { detail: { code: "hardware_key_required", message: "Tap", keys: 3 } }),
    );
    expect(res).toEqual({ kind: "locked", keys: 3 });
  });
});

type Call = { url: string; init?: RequestInit };

function router(routes: Record<string, () => Response>, calls: Call[]) {
  return async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    const key = Object.keys(routes).find((k) => url.endsWith(k));
    if (!key) throw new Error(`unexpected ${url}`);
    return routes[key]();
  };
}

const creds = (over: Partial<CredentialsLike> = {}): CredentialsLike => ({
  create: async () => fakeAttestation(),
  get: async () => fakeAssertion(),
  ...over,
});

describe("unlock flow", () => {
  const authOptions = { publicKey: { challenge: bufferToBase64url(bytes(5)), rpId: "localhost", allowCredentials: [] } };

  it("gets options, asks the authenticator, verifies and reports success", async () => {
    const calls: Call[] = [];
    let passed: CredentialRequestOptions | null = null;
    const res = await unlockWithKey(
      router(
        {
          "/authentication/options": () => jsonResponse(200, authOptions),
          "/authentication/verify": () =>
            jsonResponse(200, { step_up: { active: true, expires_at: "2026-10-21T04:00:00+00:00" } }),
        },
        calls,
      ),
      creds({
        get: async (o) => {
          passed = o;
          return fakeAssertion();
        },
      }),
    );
    expect(res).toEqual({ ok: true, data: { expires_at: "2026-10-21T04:00:00+00:00" } });
    expect(arr(passed!.publicKey!.challenge)).toEqual([5]);
    expect(calls.map((c) => c.init?.method)).toEqual(["POST", "POST"]);
    expect(calls.every((c) => c.init?.credentials === "include")).toBe(true);
    const sent = JSON.parse(String(calls[1].init!.body));
    expect(sent.credential.id).toBe("Ag");
    expect(sent.credential.response.signature).toBe("AwM");
  });

  it("a cancelled prompt never reaches verify", async () => {
    const calls: Call[] = [];
    const res = await unlockWithKey(
      router({ "/authentication/options": () => jsonResponse(200, authOptions) }, calls),
      creds({
        get: async () => {
          throw Object.assign(new Error("x"), { name: "NotAllowedError" });
        },
      }),
    );
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.message).toMatch(/Cancelled/);
    expect(calls).toHaveLength(1);
  });

  it("surfaces the server's refusal", async () => {
    const res = await unlockWithKey(
      router(
        {
          "/authentication/options": () => jsonResponse(200, authOptions),
          "/authentication/verify": () =>
            jsonResponse(400, { detail: { code: "verification_failed", message: "Could not verify." } }),
        },
        [],
      ),
      creds(),
    );
    expect(res).toEqual({ ok: false, status: 400, message: "Could not verify.", code: "verification_failed" });
  });

  it("reports an unsupported browser", async () => {
    const res = await unlockWithKey(async () => jsonResponse(200, {}), null);
    expect(res.ok).toBe(false);
  });
});

describe("registration flow", () => {
  it("creates a credential and returns first-key recovery codes", async () => {
    const calls: Call[] = [];
    const res = await registerKey(
      "MacBook Touch ID",
      router(
        {
          "/registration/options": () => jsonResponse(200, regOptions),
          "/registration/verify": () =>
            jsonResponse(201, {
              key: { id: 1, nickname: "MacBook Touch ID", created_at: null, last_used_at: null, transports: ["internal"], synced: true },
              recovery_codes: ["abcde-fghjk"],
            }),
        },
        calls,
      ),
      creds(),
    );
    expect(res.ok && res.data.recovery_codes).toEqual(["abcde-fghjk"]);
    const sent = JSON.parse(String(calls[1].init!.body));
    expect(sent.nickname).toBe("MacBook Touch ID");
    expect(sent.credential.response.attestationObject).toBe("oA");
  });

  it("a key that needs a step-up first reports the locked code", async () => {
    const res = await registerKey(
      "YubiKey",
      router(
        {
          "/registration/options": () =>
            jsonResponse(403, { detail: { code: "hardware_key_required", message: "Tap", keys: 1 } }),
        },
        [],
      ),
      creds(),
    );
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.code).toBe("hardware_key_required");
  });
});

describe("labels", () => {
  it("names how a key connects", () => {
    expect(keyKindLabel({ transports: ["internal", "hybrid"], synced: true })).toMatch(/synced/);
    expect(keyKindLabel({ transports: ["hybrid"], synced: true })).toBe("Phone passkey");
    expect(keyKindLabel({ transports: ["usb", "nfc"], synced: false })).toBe("Hardware security key");
    expect(keyKindLabel({ transports: [], synced: false })).toBe("Security key");
  });

  it("explains browser errors", () => {
    expect(browserErrorMessage({ name: "InvalidStateError" })).toMatch(/already registered/);
    expect(browserErrorMessage(new Error("?"))).toMatch(/couldn't use the key/);
  });

  it("formats recovery codes for copying", () => {
    expect(recoveryCodesText(["a", "b"]).split("\n")).toEqual(["Arepo recovery codes (each works once)", "", "a", "b"]);
  });

  it("writes security-key audit rows as sentences", () => {
    const base = { id: 1, at: null, actor_user_id: "u", actor_email: "o@x.com", target_user_id: "u", target_email: "o@x.com" };
    expect(auditSentence({ ...base, action: "security_key_registered", detail: '{"nickname": "iPhone"}' })).toBe(
      "o@x.com added a security key (iPhone)",
    );
    expect(auditSentence({ ...base, action: "recovery_code_used", detail: null })).toBe(
      "o@x.com unlocked with a recovery code",
    );
  });
});
