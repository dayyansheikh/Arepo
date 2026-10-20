// Security-key (WebAuthn / passkey) step-up client. The server (py_webauthn) sends options as
// JSON with base64url strings; the browser API wants ArrayBuffers, and the server wants the
// result back as base64url JSON. Everything here is pure or takes injectable fetch/credentials so
// it can be unit tested without a browser. Endpoints live under /api/lab/webauthn and use the
// same HttpOnly session cookie as the rest of the account area (`credentials: "include"`).

import { API_BASE } from "./api";

export const WEBAUTHN_BASE = "/api/lab/webauthn";
export { LOCKED_CODE, LOCKED_EVENT, announceLocked, lockedDetail, type LockedDetail } from "./stepup-events";

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;
const defaultFetch: FetchLike = (i, init) => fetch(i, init);

export interface CredentialsLike {
  create(options: CredentialCreationOptions): Promise<Credential | null>;
  get(options: CredentialRequestOptions): Promise<Credential | null>;
}

// -- base64url ------------------------------------------------------------------------------

export function bufferToBase64url(input: ArrayBuffer | ArrayBufferView): string {
  const bytes =
    input instanceof ArrayBuffer ? new Uint8Array(input) : new Uint8Array(input.buffer, input.byteOffset, input.byteLength);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function base64urlToBuffer(value: string): ArrayBuffer {
  const b64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  const bin = atob(padded);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

// -- option / credential conversion ---------------------------------------------------------

interface DescriptorJSON {
  id: string;
  type: "public-key";
  transports?: string[];
}

type OptionsJSON = { challenge: string; excludeCredentials?: unknown; allowCredentials?: unknown } & Record<string, unknown>;

function descriptors(list: unknown): PublicKeyCredentialDescriptor[] | undefined {
  if (!Array.isArray(list)) return undefined;
  return (list as DescriptorJSON[]).map((d) => ({
    id: base64urlToBuffer(d.id),
    type: "public-key",
    ...(d.transports ? { transports: d.transports as AuthenticatorTransport[] } : {}),
  }));
}

/** py_webauthn registration options JSON -> navigator.credentials.create() options. */
export function toCreationOptions(json: { publicKey: Record<string, unknown> }): CredentialCreationOptions {
  const pk = json.publicKey as OptionsJSON & { user: { id: string; name: string; displayName: string } };
  return {
    publicKey: {
      ...pk,
      challenge: base64urlToBuffer(pk.challenge),
      user: { ...pk.user, id: base64urlToBuffer(pk.user.id) },
      excludeCredentials: descriptors(pk.excludeCredentials) ?? [],
    } as PublicKeyCredentialCreationOptions,
  };
}

/** py_webauthn authentication options JSON -> navigator.credentials.get() options. */
export function toRequestOptions(json: { publicKey: Record<string, unknown> }): CredentialRequestOptions {
  const pk = json.publicKey as OptionsJSON;
  return {
    publicKey: {
      ...pk,
      challenge: base64urlToBuffer(pk.challenge),
      allowCredentials: descriptors(pk.allowCredentials) ?? [],
    } as PublicKeyCredentialRequestOptions,
  };
}

interface PublicKeyCredentialLike {
  id: string;
  rawId: ArrayBuffer;
  type: string;
  authenticatorAttachment?: string | null;
  response: {
    clientDataJSON: ArrayBuffer;
    attestationObject?: ArrayBuffer;
    authenticatorData?: ArrayBuffer;
    signature?: ArrayBuffer;
    userHandle?: ArrayBuffer | null;
    getTransports?: () => string[];
  };
  getClientExtensionResults?: () => unknown;
}

/** A PublicKeyCredential (registration or assertion) -> the JSON py_webauthn parses. */
export function credentialToJSON(cred: Credential): Record<string, unknown> {
  const c = cred as unknown as PublicKeyCredentialLike;
  const r = c.response;
  const response: Record<string, unknown> = { clientDataJSON: bufferToBase64url(r.clientDataJSON) };
  if (r.attestationObject) {
    response.attestationObject = bufferToBase64url(r.attestationObject);
    if (typeof r.getTransports === "function") {
      try {
        response.transports = r.getTransports();
      } catch {
        // some browsers throw; transports are optional
      }
    }
  }
  if (r.authenticatorData) response.authenticatorData = bufferToBase64url(r.authenticatorData);
  if (r.signature) response.signature = bufferToBase64url(r.signature);
  if (r.userHandle) response.userHandle = bufferToBase64url(r.userHandle);
  return {
    id: c.id,
    rawId: bufferToBase64url(c.rawId),
    type: c.type,
    response,
    authenticatorAttachment: c.authenticatorAttachment ?? undefined,
    clientExtensionResults: typeof c.getClientExtensionResults === "function" ? c.getClientExtensionResults() : {},
  };
}

// -- responses ------------------------------------------------------------------------------

function messageOf(body: unknown, fallback: string): string {
  const d = (body as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && "message" in d) return String((d as { message: unknown }).message);
  return fallback;
}

export type Outcome<T> = { ok: true; data: T } | { ok: false; status: number; message: string; code?: string };

async function call<T>(
  path: string,
  method: "GET" | "POST" | "PATCH" | "DELETE",
  body: unknown,
  fetchImpl: FetchLike,
): Promise<Outcome<T>> {
  let res: Response;
  try {
    res = await fetchImpl(`${API_BASE}${WEBAUTHN_BASE}${path}`, {
      method,
      credentials: "include",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    return { ok: false, status: 0, message: "Can't reach the Arepo API right now. Try again in a moment." };
  }
  let parsed: unknown = null;
  if (res.status !== 204) {
    try {
      parsed = await res.json();
    } catch {
      parsed = null;
    }
  }
  if (!res.ok) {
    const code = ((parsed as { detail?: { code?: unknown } } | null)?.detail?.code as string | undefined) ?? undefined;
    const fallback = res.status >= 502 ? "Can't reach the Arepo API right now. Try again in a moment." : `Request failed (${res.status}).`;
    return { ok: false, status: res.status, message: messageOf(parsed, fallback), code };
  }
  return { ok: true, data: parsed as T };
}

// -- API ------------------------------------------------------------------------------------

export interface StepUpStatus {
  enforcement: "auto" | "always" | "off";
  required: boolean;
  keys: number;
  step_up: { active: boolean; expires_at: string | null; method: string | null };
  recovery_codes_remaining: number;
  rp_id: string;
  stepup_hours: number;
}

export interface SecurityKey {
  id: number;
  nickname: string;
  created_at: string | null;
  last_used_at: string | null;
  transports: string[];
  synced: boolean;
}

export function getStepUpStatus(fetchImpl: FetchLike = defaultFetch) {
  return call<StepUpStatus>("/status", "GET", undefined, fetchImpl);
}

export function listKeys(fetchImpl: FetchLike = defaultFetch) {
  return call<{ keys: SecurityKey[]; recovery_codes_remaining: number }>("/keys", "GET", undefined, fetchImpl);
}

export function renameKey(id: number, nickname: string, fetchImpl: FetchLike = defaultFetch) {
  return call<SecurityKey>(`/keys/${id}`, "PATCH", { nickname }, fetchImpl);
}

export function removeKey(id: number, fetchImpl: FetchLike = defaultFetch) {
  return call<{ deleted: number; remaining: number }>(`/keys/${id}`, "DELETE", undefined, fetchImpl);
}

export function regenerateRecoveryCodes(fetchImpl: FetchLike = defaultFetch) {
  return call<{ recovery_codes: string[] }>("/recovery-codes", "POST", undefined, fetchImpl);
}

export function lockNow(fetchImpl: FetchLike = defaultFetch) {
  return call<null>("/lock", "POST", undefined, fetchImpl);
}

export function redeemRecoveryCode(code: string, fetchImpl: FetchLike = defaultFetch) {
  return call<{ recovery_codes_remaining: number }>("/recovery", "POST", { code }, fetchImpl);
}

export function webauthnSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential === "function" &&
    typeof navigator !== "undefined" &&
    !!navigator.credentials
  );
}

/** Friendly wording for a browser-side WebAuthn failure (cancel, timeout, wrong key...). */
export function browserErrorMessage(err: unknown): string {
  const name = err && typeof err === "object" && "name" in err ? String((err as { name: unknown }).name) : "";
  if (name === "NotAllowedError" || name === "AbortError") return "Cancelled or timed out. Try again when you're ready.";
  if (name === "InvalidStateError") return "This key is already registered.";
  if (name === "SecurityError") return "This browser refused the request for this site address.";
  if (name === "NotSupportedError") return "This browser or key doesn't support what's needed.";
  return "Your browser couldn't use the key. Try again.";
}

function browserCredentials(): CredentialsLike | null {
  return typeof navigator !== "undefined" && navigator.credentials ? navigator.credentials : null;
}

/** Full unlock ceremony: options -> navigator.credentials.get -> verify (sets the step-up cookie). */
export async function unlockWithKey(
  fetchImpl: FetchLike = defaultFetch,
  creds: CredentialsLike | null = browserCredentials(),
): Promise<Outcome<{ expires_at: string | null }>> {
  if (!creds) return { ok: false, status: 0, message: "This browser can't use security keys or passkeys." };
  const opts = await call<{ publicKey: Record<string, unknown> }>("/authentication/options", "POST", undefined, fetchImpl);
  if (!opts.ok) return opts;
  let cred: Credential | null;
  try {
    cred = await creds.get(toRequestOptions(opts.data));
  } catch (err) {
    return { ok: false, status: 0, message: browserErrorMessage(err), code: "browser" };
  }
  if (!cred) return { ok: false, status: 0, message: "No key was used.", code: "browser" };
  const res = await call<{ step_up: { expires_at: string | null } }>(
    "/authentication/verify",
    "POST",
    { credential: credentialToJSON(cred) },
    fetchImpl,
  );
  if (!res.ok) return res;
  return { ok: true, data: { expires_at: res.data?.step_up?.expires_at ?? null } };
}

/** Full registration ceremony. Returns the new key and, for a first key, the recovery codes. */
export async function registerKey(
  nickname: string,
  fetchImpl: FetchLike = defaultFetch,
  creds: CredentialsLike | null = browserCredentials(),
): Promise<Outcome<{ key: SecurityKey; recovery_codes: string[] | null }>> {
  if (!creds) return { ok: false, status: 0, message: "This browser can't use security keys or passkeys." };
  const opts = await call<{ publicKey: Record<string, unknown> }>("/registration/options", "POST", undefined, fetchImpl);
  if (!opts.ok) return opts;
  let cred: Credential | null;
  try {
    cred = await creds.create(toCreationOptions(opts.data));
  } catch (err) {
    return { ok: false, status: 0, message: browserErrorMessage(err), code: "browser" };
  }
  if (!cred) return { ok: false, status: 0, message: "No key was created.", code: "browser" };
  return call("/registration/verify", "POST", { credential: credentialToJSON(cred), nickname }, fetchImpl);
}

/** "Touch ID", "USB key"... a short plain label for how a key connects. */
export function keyKindLabel(k: Pick<SecurityKey, "transports" | "synced">): string {
  const t = new Set(k.transports);
  if (t.has("internal")) return k.synced ? "Passkey on this device (synced)" : "Built-in (Touch ID / Windows Hello)";
  if (t.has("hybrid") && !t.has("usb")) return "Phone passkey";
  if (t.has("usb") || t.has("nfc")) return "Hardware security key";
  if (k.synced) return "Synced passkey";
  return "Security key";
}

/** Plain text for the recovery-code copy button / download. */
export function recoveryCodesText(codes: string[]): string {
  return ["Arepo recovery codes (each works once)", "", ...codes].join("\n");
}
