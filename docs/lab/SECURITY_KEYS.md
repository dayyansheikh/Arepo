# Security keys and passkeys (owner step-up)

Once the owner registers a security key or passkey, the password alone no longer opens the
account. Every signed-in page and endpoint that acts as that account also needs a recent
**unlock** with one of the registered keys. That covers the Lab, Members, Security, the account
page, alerts, saved markets, `/api/users/*` and Lab commands. Accounts with no key are unaffected.

## How it works

1. **Sign in** with email and password as usual (fastapi-users cookie session). Login still works
   with the password alone.
2. Any request that acts as an account with a registered key and has no live unlock gets
   `403 {"detail": {"code": "hardware_key_required", "message": ..., "keys": N}}`. The site shows a
   padlock screen: **Unlock with Touch ID / passkey / key**.
3. The browser runs a WebAuthn assertion (`navigator.credentials.get`). The API checks it with
   [`py_webauthn`](https://github.com/duo-labs/py_webauthn), which verifies the RP ID, origin,
   single-use challenge, signature, user presence and sign counter. If it passes, the API sets
   the unlock cookie `arepo_lab_stepup`: random, `HttpOnly`, `Secure` in production,
   `SameSite=Strict`, `Path=/api`. The server keeps only its SHA-256, in
   `admin_stepup_sessions`, bound to the user id.
4. The unlock lasts **`LAB_STEPUP_HOURS` (default 4 h)**. It is revocable: **Lab › Security › Lock
   now** revokes it server-side.

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
2. Name the key (for example "MacBook Touch ID", "iPhone" or "YubiKey") and press **Add key**. In
   the browser prompt:
   - **This Mac (Touch ID):** choose this Mac / iCloud Keychain and touch the sensor.
   - **iPhone:** choose "iPhone, iPad or Android device" and scan the QR code with the iPhone camera
     (this is a cross-device, or "hybrid", passkey). You can also open the site on the iPhone and
     use Face ID.
   - **USB key (YubiKey):** choose "Security key", plug it in and touch it when it blinks.
3. **First key only:** you get 10 one-time **recovery codes**. They are shown once, with a copy
   button, and you must tick "I have saved these" before continuing. Store them offline (a
   password manager or paper). Registering the first key also unlocks the current browser. From
   then on `auto` enforcement is on.
4. Adding more keys needs a live unlock. Add at least one backup, for example Touch ID plus your
   iPhone, and later a YubiKey. Any one key unlocks the account.

The registration options do not restrict `authenticatorAttachment`, so both roaming keys (USB/NFC)
and platform passkeys work. They also set `residentKey: preferred` (discoverable where supported),
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

## Tables (schema version 16, additive, RLS enabled on Postgres)

`admin_webauthn_credentials` (public keys only), `admin_webauthn_challenges` (single use, 5 min),
`admin_stepup_sessions` (SHA-256 of the unlock token, expiry, revoked_at) and
`admin_recovery_codes` (Argon2 hashes, used_at). Deleting an account also deletes its rows in
these tables.
