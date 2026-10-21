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

// -- method steering ------------------------------------------------------------------------

/** How the owner wants to prove it's them. "any" = let the browser decide (old behaviour). */
export type KeyMethod = "device" | "phone" | "security_key";
export type MethodChoice = KeyMethod | "any";
export const KEY_METHODS: KeyMethod[] = ["device", "phone", "security_key"];

/** WebAuthn Level 3 `hints` per method (the server sends the same; we set them here as well). */
export const METHOD_HINTS: Record<KeyMethod, string[]> = {
  device: ["client-device"],
  phone: ["hybrid"],
  security_key: ["security-key"],
};

export const METHOD_LABELS: Record<KeyMethod, { button: string; link: string; add: string }> = {
  device: { button: "Use Touch ID / Face ID", link: "This device (Touch ID / Face ID)", add: "This device (Touch ID / Face ID)" },
  phone: { button: "Use my phone", link: "My phone (QR code / nearby)", add: "My phone (scan a QR code)" },
  security_key: { button: "Use my security key", link: "Security key (YubiKey)", add: "Security key (YubiKey)" },
};

/** Puts `hints` on the publicKey options for the chosen method (browsers that predate them ignore them). */
export function withHints<T extends CredentialRequestOptions | CredentialCreationOptions>(opts: T, method: MethodChoice): T {
  const pk = opts.publicKey as (Record<string, unknown> & { hints?: string[] }) | undefined;
  if (!pk) return opts;
  const next: Record<string, unknown> = { ...pk };
  if (method === "any") delete next.hints;
  else next.hints = [...METHOD_HINTS[method]];
  return { ...opts, publicKey: next } as T;
}

const METHOD_STORAGE_KEY = "arepo.unlock.method";
type StorageLike = Pick<Storage, "getItem" | "setItem">;

function localStore(): StorageLike | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

/** The method that last worked on this browser (non-sensitive; just a UI preference). */
export function rememberedMethod(store: StorageLike | null = localStore()): KeyMethod | null {
  try {
    const v = store?.getItem(METHOD_STORAGE_KEY);
    return v && (KEY_METHODS as string[]).includes(v) ? (v as KeyMethod) : null;
  } catch {
    return null;
  }
}

export function rememberMethod(method: KeyMethod, store: StorageLike | null = localStore()): void {
  try {
    store?.setItem(METHOD_STORAGE_KEY, method);
  } catch {
    // private mode / blocked storage: the chooser simply falls back to its default
  }
}

/** Primary method for the unlock screen: the remembered one, else this device if it has a
 * built-in authenticator (Touch ID, Face ID, Windows Hello), else the phone. */
export function primaryMethod(remembered: KeyMethod | null, platformAuthenticator: boolean): KeyMethod {
  return remembered ?? (platformAuthenticator ? "device" : "phone");
}

export type BrowserFamily = "safari-mac" | "ios" | "chrome" | "firefox" | "other";

export function browserFamily(ua: string): BrowserFamily {
  if (/iPhone|iPad|iPod/.test(ua)) return "ios";
  if (/Firefox\//.test(ua)) return "firefox";
  if (/Chrome\/|Chromium\/|Edg\//.test(ua)) return "chrome";
  if (/Macintosh/.test(ua) && /Safari\//.test(ua)) return "safari-mac";
  return "other";
}

/** One short line on what to do when the browser doesn't follow the chosen method (some ignore
 * hints and show Touch ID anyway). Shown only after a failed or cancelled attempt. */
export function methodTip(method: KeyMethod, family: BrowserFamily): string {
  if (method === "device") {
    if (family === "ios") return "Use Face ID or Touch ID when asked. No passkey on this device? Try “My phone” from your computer instead.";
    return "Touch the fingerprint sensor when asked. No passkey on this computer? Choose “My phone”.";
  }
  if (method === "phone") {
    if (family === "safari-mac") return "If Safari shows Touch ID, choose “Other options” → “iPhone, iPad or Android device”, then scan the QR code with your phone.";
    if (family === "chrome") return "If Chrome shows Touch ID, choose “Use a different device” or “Use a phone or tablet”, then scan the QR code.";
    if (family === "ios") return "On the iPhone itself, “This device” is simpler. To use another phone, choose “Other options” and scan the QR code.";
    return "Choose the phone / “other device” option in the browser prompt, then scan the QR code with your phone. Bluetooth must be on.";
  }
  if (family === "safari-mac") return "If Safari shows Touch ID, choose “Other options” → “Security key”, then plug in or tap your YubiKey.";
  if (family === "chrome") return "If Chrome shows Touch ID, choose “Use a different device” → “USB security key”, then touch the key when it blinks.";
  if (family === "ios") return "Hold the YubiKey to the top of the iPhone (NFC), or plug it in, when asked.";
  return "Plug in your security key and touch it when it blinks (or hold an NFC key to the phone).";
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

export interface Device {
  id: number;
  nickname: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
  trusted: boolean;
  trusted_at: string | null;
  trusted_until: string | null;
  current: boolean;
}

export interface StepUpStatus {
  enforcement: "auto" | "always" | "off";
  required: boolean;
  /** True when this browser may act now: not required, a live unlock, or a trusted device. */
  unlocked?: boolean;
  device?: Device | null;
  trusted_device_days?: number;
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

/** One assertion for `method`: options (steered by the server) -> navigator.credentials.get. */
async function assertWith(
  method: MethodChoice,
  fetchImpl: FetchLike,
  creds: CredentialsLike | null,
): Promise<Outcome<Credential>> {
  if (!creds) return { ok: false, status: 0, message: "This browser can't use security keys or passkeys." };
  const opts = await call<{ publicKey: Record<string, unknown> }>(
    "/authentication/options",
    "POST",
    { method },
    fetchImpl,
  );
  if (!opts.ok) return opts;
  let cred: Credential | null;
  try {
    cred = await creds.get(withHints(toRequestOptions(opts.data), method));
  } catch (err) {
    return { ok: false, status: 0, message: browserErrorMessage(err), code: "browser" };
  }
  if (!cred) return { ok: false, status: 0, message: "No key was used.", code: "browser" };
  return { ok: true, data: cred };
}

/** Full unlock ceremony: options -> navigator.credentials.get -> verify (sets the step-up cookie). */
export async function unlockWithKey(
  method: MethodChoice = "any",
  fetchImpl: FetchLike = defaultFetch,
  creds: CredentialsLike | null = browserCredentials(),
): Promise<Outcome<{ expires_at: string | null }>> {
  const got = await assertWith(method, fetchImpl, creds);
  if (!got.ok) return got;
  const res = await call<{ step_up: { expires_at: string | null } }>(
    "/authentication/verify",
    "POST",
    { credential: credentialToJSON(got.data) },
    fetchImpl,
  );
  if (!res.ok) return res;
  return { ok: true, data: { expires_at: res.data?.step_up?.expires_at ?? null } };
}

/** "Don't ask for my key on this device": a fresh key tap here, then the server marks it trusted. */
export async function trustThisDevice(
  method: MethodChoice = "any",
  fetchImpl: FetchLike = defaultFetch,
  creds: CredentialsLike | null = browserCredentials(),
): Promise<Outcome<{ device: Device }>> {
  const got = await assertWith(method, fetchImpl, creds);
  if (!got.ok) return got;
  return call("/devices/current/trust", "POST", { credential: credentialToJSON(got.data) }, fetchImpl);
}

export function listDevices(fetchImpl: FetchLike = defaultFetch) {
  return call<{ devices: Device[]; trusted_device_days: number; stepup_hours: number }>(
    "/devices",
    "GET",
    undefined,
    fetchImpl,
  );
}

/** Ask for the key again on that device (ends its trust now). */
export function untrustDevice(id: number, fetchImpl: FetchLike = defaultFetch) {
  return call<{ device: Device }>(`/devices/${id}/trust`, "DELETE", undefined, fetchImpl);
}

export function renameDevice(id: number, nickname: string, fetchImpl: FetchLike = defaultFetch) {
  return call<{ device: Device }>(`/devices/${id}`, "PATCH", { nickname }, fetchImpl);
}

export function forgetDevice(id: number, fetchImpl: FetchLike = defaultFetch) {
  return call<{ deleted: number }>(`/devices/${id}`, "DELETE", undefined, fetchImpl);
}

/** Full registration ceremony. Returns the new key and, for a first key, the recovery codes. */
export async function registerKey(
  nickname: string,
  method: MethodChoice = "any",
  fetchImpl: FetchLike = defaultFetch,
  creds: CredentialsLike | null = browserCredentials(),
): Promise<Outcome<{ key: SecurityKey; recovery_codes: string[] | null }>> {
  if (!creds) return { ok: false, status: 0, message: "This browser can't use security keys or passkeys." };
  const opts = await call<{ publicKey: Record<string, unknown> }>(
    "/registration/options",
    "POST",
    { method },
    fetchImpl,
  );
  if (!opts.ok) return opts;
  let cred: Credential | null;
  try {
    cred = await creds.create(withHints(toCreationOptions(opts.data), method));
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
