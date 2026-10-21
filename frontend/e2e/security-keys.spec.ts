import { expect, test, type Page, type Route } from "@playwright/test";

/**
 * Security keys UI against a mocked API and a stubbed navigator.credentials (no real
 * authenticator in headless Chromium): the calm unlock chooser passes the chosen method to the
 * API and WebAuthn hints to the browser, remembers the method that worked, shows a browser tip
 * only after a failure, and Lab > Security shows keys + devices with per-device trust.
 * Set KEYS_SHOTS=<dir> to also write desktop + mobile screenshots.
 */

const SHOTS = process.env.KEYS_SHOTS;
const OWNER = {
  id: "owner-1",
  email: "dayyan@example.com",
  first_name: "Dayyan",
  last_name: "Sheikh",
  is_active: true,
  is_verified: true,
  is_superuser: true,
  auth_provider: "local",
  consent_at: null,
};

const KEY = {
  id: 1,
  nickname: "Dayyan's Personal MacBook Touch ID",
  created_at: "2026-10-20T18:02:00+00:00",
  last_used_at: "2026-10-21T08:15:00+00:00",
  transports: ["hybrid", "internal"],
  synced: true,
};

function devices(trusted: boolean) {
  return [
    {
      id: 7,
      nickname: "Mac · Safari",
      first_seen_at: "2026-10-20T18:02:00+00:00",
      last_seen_at: "2026-10-21T08:15:00+00:00",
      trusted,
      trusted_at: trusted ? "2026-10-21T08:20:00+00:00" : null,
      trusted_until: trusted ? "2026-11-20T08:20:00+00:00" : null,
      current: true,
    },
    {
      id: 8,
      nickname: "iPhone · Safari",
      first_seen_at: "2026-10-20T19:40:00+00:00",
      last_seen_at: "2026-10-20T21:05:00+00:00",
      trusted: false,
      trusted_at: null,
      trusted_until: null,
      current: false,
    },
  ];
}

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

interface State {
  unlocked: boolean;
  trusted: boolean;
  bodies: Record<string, unknown[]>;
}

async function mockApi(page: Page, state: State) {
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const key = `${req.method()} ${path}`;
    (state.bodies[key] ??= []).push(req.postData() ? req.postDataJSON() : null);
    const W = "/api/lab/webauthn";
    if (path === "/api/users/me") return json(route, 200, OWNER);
    if (path === `${W}/status`) {
      return json(route, 200, {
        enforcement: "auto",
        required: true,
        unlocked: state.unlocked || state.trusted,
        keys: 1,
        step_up: { active: state.unlocked, expires_at: state.unlocked ? "2026-10-21T12:15:00+00:00" : null, method: "key" },
        device: devices(state.trusted)[0],
        trusted_device_days: 30,
        recovery_codes_remaining: 10,
        rp_id: "localhost",
        stepup_hours: 4,
      });
    }
    if (path === `${W}/authentication/options`) {
      return json(route, 200, {
        publicKey: {
          challenge: "AQID",
          rpId: "localhost",
          timeout: 120000,
          userVerification: "preferred",
          allowCredentials: [{ id: "AQ", type: "public-key", transports: ["hybrid"] }],
          hints: ["hybrid"],
        },
      });
    }
    if (path === `${W}/authentication/verify`) {
      state.unlocked = true;
      return json(route, 200, { step_up: { active: true, expires_at: "2026-10-21T12:15:00+00:00", method: "key" } });
    }
    if (path === `${W}/keys`) return json(route, 200, { keys: [KEY], recovery_codes_remaining: 10 });
    if (path === `${W}/devices`) return json(route, 200, { devices: devices(state.trusted), trusted_device_days: 30, stepup_hours: 4 });
    if (path === `${W}/devices/current/trust`) {
      state.trusted = true;
      return json(route, 200, { device: devices(true)[0] });
    }
    if (path === `${W}/devices/7/trust` && req.method() === "DELETE") {
      state.trusted = false;
      return json(route, 200, { device: devices(false)[0] });
    }
    return json(route, 404, { detail: "Not found" });
  });
}

/** Stub WebAuthn: record every get() call's publicKey, optionally fail, report a platform authenticator. */
async function stubWebAuthn(page: Page, { fail = false } = {}) {
  await page.addInitScript((shouldFail: boolean) => {
    const w = window as unknown as { __webauthn: unknown[] };
    w.__webauthn = [];
    const buf = (...xs: number[]) => new Uint8Array(xs).buffer;
    const fake = {
      id: "AQ",
      rawId: buf(1),
      type: "public-key",
      authenticatorAttachment: "cross-platform",
      response: { clientDataJSON: buf(123, 125), authenticatorData: buf(1), signature: buf(3, 3), userHandle: null },
      getClientExtensionResults: () => ({}),
    };
    const record = (o: CredentialRequestOptions | CredentialCreationOptions) => {
      const pk = o.publicKey as unknown as { hints?: string[]; allowCredentials?: Array<{ transports?: string[] }> };
      w.__webauthn.push({ hints: pk.hints, transports: pk.allowCredentials?.map((c) => c.transports) });
    };
    Object.defineProperty(navigator, "credentials", {
      configurable: true,
      value: {
        get: async (o: CredentialRequestOptions) => {
          record(o);
          if (shouldFail) throw Object.assign(new Error("cancelled"), { name: "NotAllowedError" });
          return fake;
        },
        create: async (o: CredentialCreationOptions) => {
          record(o);
          return fake;
        },
      },
    });
    const pkc = (window as unknown as { PublicKeyCredential?: { isUserVerifyingPlatformAuthenticatorAvailable?: unknown } })
      .PublicKeyCredential;
    if (pkc) pkc.isUserVerifyingPlatformAuthenticatorAvailable = async () => true;
  }, fail);
}

async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(450); // let the rise animation settle
  await page.screenshot({ path: `${SHOTS}/keys-${name}-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${SHOTS}/keys-${name}-mobile.png`, fullPage: true });
  await page.setViewportSize({ width: 1280, height: 800 });
}

test.use({ viewport: { width: 1280, height: 800 } });

test("unlock chooser: calm default, phone link sends method + hints and is remembered", async ({ page }) => {
  const state: State = { unlocked: false, trusted: false, bodies: {} };
  await mockApi(page, state);
  await stubWebAuthn(page);
  await page.goto("/lab/security");

  const screen = page.getByTestId("unlock-screen");
  await expect(screen.getByRole("heading", { name: "Unlock your account" })).toBeVisible();
  const primary = screen.getByRole("button", { name: "Use Touch ID / Face ID" });
  await expect(primary).toBeVisible();
  await expect(screen.getByRole("button", { name: "Phone (QR code)" })).toBeVisible();
  await expect(screen.getByRole("button", { name: "Security key" })).toBeVisible();
  await expect(screen.getByRole("button", { name: "Recovery code" })).toBeVisible();
  await expect(page.getByTestId("unlock-tip")).toHaveCount(0); // no walls of text up front
  await shot(page, "unlock");

  // Keyboard: Enter on the focused phone link starts the phone flow.
  await screen.getByRole("button", { name: "Phone (QR code)" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Security" })).toBeVisible();
  expect(state.bodies["POST /api/lab/webauthn/authentication/options"]).toEqual([{ method: "phone" }]);
  const calls = await page.evaluate(() => (window as unknown as { __webauthn: unknown[] }).__webauthn);
  expect(calls).toEqual([{ hints: ["hybrid"], transports: [["hybrid"]] }]);
  expect(await page.evaluate(() => localStorage.getItem("arepo.unlock.method"))).toBe("phone");

  // Next time the remembered method is the primary button.
  state.unlocked = false;
  await page.reload();
  await expect(page.getByTestId("unlock-screen").getByRole("button", { name: "Use my phone" })).toBeVisible();
});

test("a failed attempt shows one browser tip for that method", async ({ page }) => {
  const state: State = { unlocked: false, trusted: false, bodies: {} };
  await mockApi(page, state);
  await stubWebAuthn(page, { fail: true });
  await page.goto("/lab/security");
  const screen = page.getByTestId("unlock-screen");
  await screen.getByRole("button", { name: "Security key" }).click();
  await expect(screen.getByRole("status")).toContainText("Cancelled");
  await expect(page.getByTestId("unlock-tip")).toContainText("security key");
  const calls = await page.evaluate(() => (window as unknown as { __webauthn: unknown[] }).__webauthn);
  expect(calls).toEqual([{ hints: ["security-key"], transports: [["hybrid"]] }]);
  await shot(page, "unlock-tip");
});

test("Lab > Security shows the key and devices; trust is one click plus a key tap, and revocable", async ({ page }) => {
  const state: State = { unlocked: true, trusted: false, bodies: {} };
  await mockApi(page, state);
  await stubWebAuthn(page);
  await page.goto("/lab/security");

  await expect(page.getByText("Dayyan's Personal MacBook Touch ID")).toBeVisible();
  const list = page.getByRole("list", { name: "Devices" });
  await expect(list.getByTestId("device-row")).toHaveCount(2);
  await expect(list.getByText("This device", { exact: true })).toBeVisible();
  await expect(list.getByText("Key every 4 h").first()).toBeVisible();
  await expect(page.getByTestId("this-device")).toContainText("Don't ask for my key on Mac · Safari");
  await shot(page, "devices");

  await page.getByTestId("this-device").getByRole("button", { name: "Trust this device" }).click();
  await expect(page.getByRole("status").filter({ hasText: "won't ask for your key" })).toBeVisible();
  expect(state.bodies["POST /api/lab/webauthn/devices/current/trust"]).toHaveLength(1);
  const sent = state.bodies["POST /api/lab/webauthn/devices/current/trust"]![0] as { credential: { id: string } };
  expect(sent.credential.id).toBe("AQ");
  await expect(list.getByText(/No key until/)).toBeVisible();
  await expect(page.getByTestId("this-device")).toHaveCount(0);
  await shot(page, "devices-trusted");

  await list.getByRole("button", { name: "Ask for my key again" }).click();
  await expect(page.getByRole("status").filter({ hasText: "will ask for your key again" })).toBeVisible();
  expect(state.bodies["DELETE /api/lab/webauthn/devices/7/trust"]).toHaveLength(1);
});

test("add-key offers the three methods and steers creation", async ({ page }) => {
  const state: State = { unlocked: true, trusted: false, bodies: {} };
  await mockApi(page, state);
  await stubWebAuthn(page);
  await page.route("**/api/lab/webauthn/registration/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/options")) {
      state.bodies.reg = [route.request().postDataJSON()];
      return json(route, 200, {
        publicKey: {
          rp: { name: "Arepo Lab", id: "localhost" },
          user: { id: "AQ", name: "o", displayName: "o" },
          challenge: "AQID",
          pubKeyCredParams: [{ type: "public-key", alg: -7 }],
          authenticatorSelection: { authenticatorAttachment: "cross-platform", residentKey: "preferred", userVerification: "preferred" },
          excludeCredentials: [],
          hints: ["security-key"],
        },
      });
    }
    return json(route, 201, { key: { ...KEY, id: 2, nickname: "YubiKey", transports: ["usb"], synced: false }, recovery_codes: null });
  });
  await page.goto("/lab/security");
  const group = page.getByRole("group", { name: "Add a key with" });
  await expect(group.getByRole("button")).toHaveText([
    "This device (Touch ID / Face ID)",
    "My phone (scan a QR code)",
    "Security key (YubiKey)",
  ]);
  await group.getByRole("button", { name: "Security key (YubiKey)" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Added" })).toBeVisible();
  expect(state.bodies.reg).toEqual([{ method: "security_key" }]);
  const calls = await page.evaluate(() => (window as unknown as { __webauthn: Array<{ hints: string[] }> }).__webauthn);
  expect(calls[0].hints).toEqual(["security-key"]);
});
