# Security keys and passkeys (owner step-up)

Once the owner registers a security key or passkey, the password alone no longer opens the
account. Every signed-in page and endpoint that acts as that account also needs a recent
**unlock** with one of the registered keys. That covers the Lab, Members, Security, the account
page, alerts, saved markets, `/api/users/*` and Lab commands. Accounts with no key are unaffected.

## How it works

1. **Sign in** with email and password as usual (fastapi-users cookie session). Login still works
   with the password alone.
2. Any request that acts as an account with a registered key and has no live unlock (and does not
   come from a trusted device, see below) gets
   `403 {"detail": {"code": "hardware_key_required", "message": ..., "keys": N}}`. The site shows a
   small padlock screen, **Unlock your account**, with one button for the most likely method and
   the others as small links underneath (see "Choosing how to unlock").
3. The browser runs a WebAuthn assertion (`navigator.credentials.get`). The API checks it with
   [`py_webauthn`](https://github.com/duo-labs/py_webauthn), which verifies the RP ID, origin,
   single-use challenge, signature, user presence and sign counter. If it passes, the API sets
   the unlock cookie `arepo_lab_stepup`: random, `HttpOnly`, `Secure` in production,
   `SameSite=Strict`, `Path=/api`. The server keeps only its SHA-256, in
   `admin_stepup_sessions`, bound to the user id.
4. The unlock lasts **`LAB_STEPUP_HOURS` (default 4 h)**. It is revocable: **Lab › Security › Lock
   now** revokes it server-side (and also ends trust on this device, if it was trusted).

## Choosing how to unlock

The unlock screen shows one primary button and three small links:

| Choice | What the browser is asked for |
|---|---|
| **Touch ID / Face ID** (this device) | WebAuthn hint `client-device`; credential transports set to `internal`. |
| **Phone (QR code)** | Hint `hybrid`; transports `hybrid`. The browser shows a QR code; scan it with the phone that holds the passkey (Bluetooth must be on, on both devices). |
| **Security key** (YubiKey) | Hint `security-key`; transports `usb`, `nfc`, `ble`. Plug the key in (or tap it on NFC) and touch it. |
| **Recovery code** | One-time code (see Recovery). |

The primary button is the method that last worked in this browser (kept in `localStorage` under
`arepo.unlock.method`; it is only a UI preference, not a secret), otherwise Touch ID / Face ID when
the device has a built-in authenticator, otherwise the phone.

The API side: `POST /api/lab/webauthn/authentication/options` takes an optional body
`{"method": "device" | "phone" | "security_key" | "any"}`. Every registered credential id stays in
`allowCredentials` whatever the method; only the transports change. That is what lets a synced
iCloud passkey registered on a Mac (transports `internal`, `hybrid`) be used from the iPhone over
hybrid on a computer that does not have it. `any`, or no body, keeps the old behaviour (stored
transports, no hints). The client sets `publicKey.hints` too.

**Browsers that ignore hints.** Hints are new (WebAuthn Level 3). Chrome follows them. Safari may
still show its Touch ID sheet first. After a failed or cancelled attempt the screen shows one line
for the browser in use, for example:

- Safari on a Mac, phone: choose **Other options** → **iPhone, iPad or Android device**, then scan
  the QR code.
- Safari on a Mac, security key: **Other options** → **Security key**.
- Chrome: **Use a different device** (or **Use a phone or tablet** / **USB security key**).

### Signing in on a different computer with your phone

On a computer that does not have your passkey (for example a borrowed MacBook):

1. Sign in with email and password.
2. On the unlock screen choose **Phone (QR code)**. If the browser still offers Touch ID, follow
   the tip above to pick the phone option.
3. Scan the QR code with the iPhone camera, approve with Face ID. The phone and the computer talk
   over Bluetooth, so Bluetooth must be on for both.

This works with the iCloud Keychain passkey ("Dayyan's Personal MacBook Touch ID"): it is synced
to the iPhone, so the phone can answer for it. Nothing is added to the other computer. Do not
choose "Trust this device" on a computer that is not yours.

### YubiKey

Add it in **Lab › Security › Add a key › Security key (YubiKey)** (this asks the browser for a
cross-platform authenticator with the `security-key` hint). To unlock, choose **Security key** and
plug in or tap the key. A YubiKey 5C NFC works over USB-C on a Mac and over NFC on an iPhone.

## Trusted devices (per-device "don't ask for my key")

Every browser a key holder uses gets a device cookie, `arepo_device`: random, `HttpOnly`, `Secure`
in production, `SameSite=Strict`, `Path=/api`, kept for up to 400 days. The server stores only its
SHA-256, in `admin_trusted_devices`, with a nickname taken from the user agent (for example
"Mac · Safari"), first seen and last seen. Devices are listed in **Lab › Security › Devices**,
where you can rename or forget them.

Each device is in one of two states:

- **Key every 4 hours** (default): the normal unlock rule.
- **Trusted, no key until <date>**: press **Trust this device** in Lab › Security on that device.
  It asks for one key tap there, then that browser counts as unlocked for this account for
  `LAB_TRUSTED_DEVICE_DAYS` days (default 30, capped at 30; `0` turns the feature off). After that
  it asks again.

Rules:

- Turning trust on needs a fresh key assertion made on that device
  (`POST /api/lab/webauthn/devices/current/trust` with a credential from `authentication/options`).
  A password, a recovery code or another trusted device is not enough. You can only trust the
  device you are using.
- You can end trust on any device at any time: **Ask for my key again**
  (`DELETE /api/lab/webauthn/devices/{id}/trust`), **Forget**, or **Lock now** on that device.
- Trust is bound to the account and the device cookie. Another account in the same browser, or the
  same account in another browser, is not trusted.
- A trusted device can browse everything, but adding a key, removing a key or making new recovery
  codes still needs a fresh key tap. Those actions could otherwise turn "password + trusted device"
  into a way to replace your keys.
- Audit rows in `lab_admin_audit`: `device_trusted` (device, days, until) and
  `device_trust_revoked` (device, reason `owner` / `lock_now` / `forgotten`).

Only trust computers and phones you own and keep locked. Anyone who has your password and your
trusted, unlocked device can use the account without a key until the trust ends.

Where it is enforced:

- `accounts/stepup_gate.py`. A custom JWT strategy resolves every session cookie. For a locked
  account it acts as if no user were signed in, so optional-user endpoints show the signed-out
  view and leak nothing. A small ASGI middleware then turns the resulting 401 into the 403
  `hardware_key_required` above.
- `api/routes/lab.py::owner()` checks again for every Lab, Members, command and key-management
  endpoint.

Always reachable without an unlock: `POST /api/auth/logout`, login, password reset, and the
unlock endpoints under `/api/lab/webauthn/*`. Machine-signed `/api/lab/agent/*` endpoints use
Ed25519 request signing, never the session cookie, so keys do not affect them.

### Settings (all optional, no new secrets)

| Setting | Default | Meaning |
|---|---|---|
| `LAB_REQUIRE_HARDWARE_KEY` | `auto` | `auto`: required for any account that has at least one key, so it switches on by itself after the first key is registered and nobody is locked out before that. `always`: superusers need a key even before registering one (they can still register a first key). `off`: emergency escape hatch, password alone suffices. An unknown value is treated as `auto`. |
| `LAB_STEPUP_HOURS` | `4` | How long one unlock lasts. |
| `LAB_TRUSTED_DEVICE_DAYS` | `30` | How long a trusted device skips the key prompt. Capped at 30; `0` turns trusted devices off (existing trust stops counting at once). |
| `LAB_WEBAUTHN_RP_ID` | `arepolabs.com` in production, otherwise the host of `APP_BASE_URL` (`localhost`) | WebAuthn relying-party ID. |
| `LAB_WEBAUTHN_ORIGINS` | production: `https://www.arepolabs.com`, `https://arepolabs.com`, plus any `CORS_ORIGINS`/`APP_BASE_URL` origin on the RP ID's domain | Page origins accepted in `clientDataJSON`. |
| `LAB_WEBAUTHN_RP_NAME` | `Arepo Lab` | Name shown in the browser prompt. |

**Why the RP ID is `arepolabs.com`.** The site is served at `https://www.arepolabs.com`, and the
apex redirects to `www`. The browser calls the API same-origin through the Next `/api` rewrite, so
`clientDataJSON.origin` is always the page origin `https://www.arepolabs.com` and never the
Render host. An RP ID must be the page's host or a registrable suffix of it. `arepolabs.com` works
on `www` today and keeps working if the canonical host ever moves to the apex. The server still
accepts only the listed origins, so another subdomain cannot use the keys.

**Do not change the RP ID after keys exist.** A key is bound to the RP ID it was registered under.
After a change, every existing key stops working and you have to recover (see below). Vercel
preview deployments (`*.vercel.app`) and `localhost` cannot use production keys. Browse the
production site to unlock.

## Registering keys (Lab › Security, `/lab/security`)

1. Sign in, then open **Lab › Security**.
2. Optionally name the key, then press one of the three buttons:
   - **This device (Touch ID / Face ID):** asks for a platform authenticator (`authenticatorAttachment:
     platform`, hint `client-device`). Touch the sensor.
   - **My phone (scan a QR code):** cross-platform, hint `hybrid`. Scan the QR code with the iPhone
     camera. You can also open the site on the iPhone and use "This device" there.
   - **Security key (YubiKey):** cross-platform, hint `security-key`. Plug it in and touch it when
     it blinks.
3. **First key only:** you get 10 one-time **recovery codes**. They are shown once, with a copy
   button, and you must tick "I have saved these" before continuing. Store them offline (a
   password manager or paper). Registering the first key also unlocks the current browser. From
   then on `auto` enforcement is on.
4. Adding more keys needs a live unlock. Add at least one backup, for example Touch ID plus your
   iPhone, and later a YubiKey. Any one key unlocks the account.

`POST /registration/options` takes the same optional `{"method": ...}` body as the unlock options.
With `any` (or no body) the options do not restrict `authenticatorAttachment`, so both roaming keys
(USB/NFC) and platform passkeys work. They always set `residentKey: preferred` (discoverable where supported),
`userVerification: preferred` and `attestation: none`. Up to 10 keys per account. You can rename
and remove keys, but **not the last one** while enforcement is on. Add another key first.

All key events are written to `lab_admin_audit`: key added, removed or renamed; recovery code
used or wrong; recovery codes regenerated. They appear in Lab › Members › Recent admin activity.

## Recovery

In order of preference:

1. **Another registered key.** This is why a backup key matters.
2. **A recovery code.** On the unlock screen, choose "Lost your key? Use a recovery code". Each code
   works once. Codes are Argon2-hashed (`admin_recovery_codes`). After 5 wrong codes in an hour,
   recovery pauses for that hour. When you have access again, remove the lost key and press
   **Make new codes**, which cancels the old set.
3. **Operator escape hatch, no database access needed.** On Render set
   `LAB_REQUIRE_HARDWARE_KEY=off` (this restarts the service). Sign in with your password, open Lab
   › Security, remove the lost key, register a new one, then set the variable back to `auto`.
   Changing a production env var is a protected action: the owner does it.
4. **Database reset (Supabase SQL editor)**, if nothing else is possible. This removes every key,
   unlock, challenge and recovery code for one account. Enforcement then turns off for that account
   until a new key is registered.

   ```sql
   -- 1. Find the account id.
   select id, email from users where email = 'OWNER_EMAIL';

   -- 2. Reset its security keys (replace OWNER_ID with the uuid from step 1).
   begin;
   delete from admin_stepup_sessions      where user_id = 'OWNER_ID';
   delete from admin_trusted_devices      where user_id = 'OWNER_ID';
   delete from admin_webauthn_challenges  where user_id = 'OWNER_ID';
   delete from admin_recovery_codes       where user_id = 'OWNER_ID';
   delete from admin_webauthn_credentials where user_id = 'OWNER_ID';
   insert into lab_admin_audit (at, actor_user_id, actor_email, action, target_user_id, target_email, detail)
   values (now(), 'OWNER_ID', 'OWNER_EMAIL', 'security_keys_reset_sql', 'OWNER_ID', 'OWNER_EMAIL',
           '{"via": "supabase sql editor"}');
   commit;

   -- 3. Check: should return 0.
   select count(*) from admin_webauthn_credentials where user_id = 'OWNER_ID';
   ```

   Then sign in, register a new key and save the new recovery codes. To remove just one lost key,
   delete only its row: `delete from admin_webauthn_credentials where id = <id>;` (list them with
   `select id, nickname, created_at, last_used_at from admin_webauthn_credentials where user_id = 'OWNER_ID';`).

## Choosing and buying a key

Any FIDO2 / WebAuthn authenticator works:

- **Built-in passkeys (free):** Touch ID on a Mac (Safari or Chrome), Face ID / Touch ID on iPhone
  and iPad (synced through iCloud Keychain), Windows Hello, Android.
- **Hardware keys:** YubiKey 5 series (5C NFC for USB-C laptops and iPhone NFC; 5Ci has USB-C and
  Lightning). The cheaper Yubico **Security Key** series (FIDO-only) is also enough here. Google
  Titan, Feitian, SoloKeys and Nitrokey work too. Buy from the manufacturer or an authorised
  reseller, and ideally buy two: keep one somewhere safe as a backup.

A hardware key is the strongest choice because it cannot be phished and is never synced. Synced
passkeys (iCloud Keychain) are convenient, and losing one device does not lose them.

## Tables (schema versions 16 and 17, additive, RLS enabled on Postgres)

`admin_webauthn_credentials` (public keys only), `admin_webauthn_challenges` (single use, 5 min),
`admin_stepup_sessions` (SHA-256 of the unlock token, expiry, revoked_at) and
`admin_recovery_codes` (Argon2 hashes, used_at). Version 17 adds `admin_trusted_devices`
(SHA-256 of the device cookie, nickname, user agent, first/last seen, trusted_at, trusted_until). Deleting an account also deletes its rows in
these tables.
