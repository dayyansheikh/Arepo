"""Hardware-security-key (WebAuthn / FIDO2 / passkey) step-up for the owner-only Lab.

Model
-----
* The owner signs in with their normal password session (fastapi-users cookie). When step-up is
  enforced, every owner Lab endpoint additionally needs a valid *step-up*: a random token in an
  HttpOnly, SameSite=strict cookie whose SHA-256 is stored in ``admin_stepup_sessions`` bound to
  the user id, valid for ``LAB_STEPUP_HOURS`` and revocable.
* A step-up is granted by a verified WebAuthn assertion from one of the owner's registered keys,
  by registering the owner's FIRST key (which proves possession), or once per one-time recovery
  code.
* Per-device trust: every browser a key holder uses gets an HttpOnly device cookie (random; only
  its SHA-256 is stored in ``admin_trusted_devices``). The owner may mark the CURRENT device as
  trusted ("don't ask for my key here") for at most ``LAB_TRUSTED_DEVICE_DAYS`` (cap 30) days,
  which needs a fresh key assertion on that device; a trusted, unexpired device counts as unlocked.
  Trust can be ended for any device at any time, and every change is audited.
* Method steering: options endpoints take ``method`` (device | phone | security_key | any) and set
  WebAuthn Level 3 ``hints`` plus credential transports / authenticator attachment accordingly.
* Enforcement (``LAB_REQUIRE_HARDWARE_KEY``): ``auto`` = on for an owner as soon as they have a
  registered key; ``always`` = on even with none (a first key can still be registered); ``off`` =
  operator escape hatch.

Verification of every WebAuthn ceremony is delegated to ``py_webauthn`` (RP ID, origin,
challenge, signature, user presence, sign-count regression); nothing cryptographic is hand-rolled.
Challenges are stored server-side and are single-use: the row is deleted before verification, so
a failed or replayed response can never be retried against the same challenge.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..accounts.models import User
from ..config import Settings, get_settings
from .models import LabAdminAudit
from .security_models import (
    AdminRecoveryCode,
    AdminStepUpSession,
    AdminTrustedDevice,
    AdminWebAuthnChallenge,
    AdminWebAuthnCredential,
)

STEPUP_COOKIE = "arepo_lab_stepup"
STEPUP_COOKIE_PATH_ROOT = "/api"  # sent to every API call (the gate is site-wide)
CHALLENGE_TTL = timedelta(minutes=5)
MAX_OPEN_CHALLENGES = 5
MAX_KEYS = 10
RECOVERY_CODE_COUNT = 10
MAX_RECOVERY_FAILURES_PER_HOUR = 5
NICKNAME_MAX = 60
# Unambiguous lowercase alphabet (no 0/o/1/l/i); 10 chars ~ 50 bits per code.
_CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
_KNOWN_TRANSPORTS = {t.value for t in AuthenticatorTransport}

# ---- method steering (WebAuthn Level 3 hints) -------------------------------------------------
# "device": this computer/phone's own passkey (Touch ID, Face ID, Windows Hello);
# "phone": another device over hybrid (QR code / nearby); "security_key": a roaming FIDO key.
KEY_METHODS = ("device", "phone", "security_key", "any")
METHOD_HINTS: dict[str, list[str]] = {
    "device": ["client-device"],
    "phone": ["hybrid"],
    "security_key": ["security-key"],
}
METHOD_TRANSPORTS: dict[str, list[str]] = {
    "device": ["internal"],
    "phone": ["hybrid"],
    "security_key": ["usb", "nfc", "ble"],
}
METHOD_ATTACHMENT = {
    "device": AuthenticatorAttachment.PLATFORM,
    "phone": AuthenticatorAttachment.CROSS_PLATFORM,
    "security_key": AuthenticatorAttachment.CROSS_PLATFORM,
}

# ---- devices ----------------------------------------------------------------------------------
DEVICE_COOKIE = "arepo_device"
DEVICE_COOKIE_MAX_AGE = 400 * 24 * 3600  # browsers cap cookie lifetimes at 400 days
MAX_DEVICES = 30
DEVICE_TOUCH_EVERY = timedelta(minutes=15)  # last-seen write throttle
USER_AGENT_MAX = 300

_hasher = PasswordHash.recommended()  # Argon2id, same family as account passwords


class SecurityKeyError(Exception):
    """A refused request. ``status`` is the HTTP status; ``code`` a machine-readable reason."""

    def __init__(self, status: int, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


# ---- small helpers ----------------------------------------------------------------------------
def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _iso(dt: datetime | None) -> str | None:
    dt = _aware(dt)
    return dt.isoformat() if dt else None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def client_data_challenge(credential: dict) -> str | None:
    """The challenge (base64url) echoed in a response's clientDataJSON, or None if unreadable."""
    try:
        raw = credential["response"]["clientDataJSON"]
        data = json.loads(_b64url_decode(raw))
        challenge = data.get("challenge")
        return challenge if isinstance(challenge, str) and challenge else None
    except (KeyError, TypeError, ValueError):
        return None


def normalise_method(method: str | None) -> str:
    method = (method or "any").strip().lower().replace("-", "_")
    if method not in KEY_METHODS:
        raise SecurityKeyError(422, "Unknown sign-in method.", "bad_method")
    return method


def clean_nickname(name: str | None, fallback: str) -> str:
    name = " ".join((name or "").split())[:NICKNAME_MAX]
    return name or fallback


def normalise_code(code: str) -> str:
    return "".join(ch for ch in (code or "").lower() if ch.isalnum())


def generate_recovery_codes(n: int = RECOVERY_CODE_COUNT) -> list[str]:
    out = []
    for _ in range(n):
        raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))
        out.append(f"{raw[:5]}-{raw[5:]}")
    return out


def key_dict(row: AdminWebAuthnCredential) -> dict:
    try:
        transports = json.loads(row.transports) if row.transports else []
    except ValueError:
        transports = []
    return {
        "id": row.id,
        "nickname": row.nickname,
        "created_at": _iso(row.created_at),
        "last_used_at": _iso(row.last_used_at),
        "transports": transports,
        "synced": bool(row.backed_up) or row.device_type == "multi_device",
    }


def _audit(session: AsyncSession, user: User, action: str, now: datetime,
           detail: dict | None = None) -> None:
    session.add(LabAdminAudit(
        at=now, actor_user_id=str(user.id), actor_email=user.email, action=action,
        target_user_id=str(user.id), target_email=user.email,
        detail=json.dumps(detail, sort_keys=True) if detail else None,
    ))


# ---- enforcement ------------------------------------------------------------------------------
async def key_count(session: AsyncSession, user_id) -> int:
    return int((await session.execute(
        select(func.count()).select_from(AdminWebAuthnCredential)
        .where(AdminWebAuthnCredential.user_id == user_id)
    )).scalar_one())


def stepup_required_for(mode: str, keys: int) -> bool:
    if mode == "off":
        return False
    if mode == "always":
        return True
    return keys > 0


async def stepup_required(session: AsyncSession, user: User,
                          settings: Settings | None = None) -> bool:
    mode = (settings or get_settings()).lab_hardware_key_mode
    if mode == "off":
        return False
    return stepup_required_for(mode, await key_count(session, user.id))


async def user_locked(session: AsyncSession, user: User, token: str | None, now: datetime,
                      settings: Settings | None = None,
                      device_token: str | None = None) -> int | None:
    """None when this user may act now; otherwise their key count (they need to unlock first).

    Locked = enforcement applies to them (they have a key, or mode "always" and they are a
    superuser), the step-up token is not a live step-up of theirs, and this browser is not one of
    their trusted, unexpired devices.
    """
    mode = (settings or get_settings()).lab_hardware_key_mode
    if mode == "off":
        return None
    keys = await key_count(session, user.id)
    if keys == 0 and not (mode == "always" and user.is_superuser):
        return None
    if await active_stepup(session, user, token, now) is not None:
        return None
    if keys > 0 and device_token:
        device = await trusted_device(session, user, device_token, now)
        if device is not None:
            await _touch_device(session, device, now)
            return None
    return keys


async def active_stepup(
    session: AsyncSession, user: User, token: str | None, now: datetime
) -> AdminStepUpSession | None:
    """The live step-up this cookie token proves for this user, if any."""
    if not token or len(token) > 256:
        return None
    row = (await session.execute(
        select(AdminStepUpSession).where(AdminStepUpSession.token_sha256 == token_hash(token))
    )).scalar_one_or_none()
    if row is None or str(row.user_id) != str(user.id) or row.revoked_at is not None:
        return None
    if _aware(row.expires_at) <= now:
        return None
    return row


async def _new_stepup(
    session: AsyncSession, user: User, method: str, now: datetime,
    credential_id: str | None = None, settings: Settings | None = None,
) -> tuple[str, datetime]:
    s = settings or get_settings()
    # Bounded table: drop this user's expired or revoked step-ups.
    for row in (await session.execute(
        select(AdminStepUpSession).where(AdminStepUpSession.user_id == user.id)
    )).scalars():
        if row.revoked_at is not None or _aware(row.expires_at) <= now:
            await session.delete(row)
    token = secrets.token_urlsafe(32)
    expires = now + timedelta(hours=s.lab_stepup_hours)
    session.add(AdminStepUpSession(
        user_id=user.id, token_sha256=token_hash(token), method=method,
        credential_id=credential_id, created_at=now, expires_at=expires,
    ))
    return token, expires


async def revoke_stepup(session: AsyncSession, user: User, token: str | None,
                        now: datetime) -> None:
    row = await active_stepup(session, user, token, now)
    if row is not None:
        row.revoked_at = now
        await session.commit()


# ---- challenges -------------------------------------------------------------------------------
async def _store_challenge(session: AsyncSession, user: User, purpose: str, challenge: bytes,
                           now: datetime) -> None:
    rows = list((await session.execute(
        select(AdminWebAuthnChallenge).where(AdminWebAuthnChallenge.user_id == user.id)
        .order_by(AdminWebAuthnChallenge.id.desc())
    )).scalars())
    live = 0
    for row in rows:
        if _aware(row.expires_at) <= now or live >= MAX_OPEN_CHALLENGES - 1:
            await session.delete(row)
        else:
            live += 1
    session.add(AdminWebAuthnChallenge(
        user_id=user.id, purpose=purpose, challenge=bytes_to_base64url(challenge),
        created_at=now, expires_at=now + CHALLENGE_TTL,
    ))


async def _consume_challenge(session: AsyncSession, user: User, purpose: str, credential: dict,
                             now: datetime) -> bytes:
    """Delete and return the matching unexpired challenge (single use), or refuse."""
    echoed = client_data_challenge(credential)
    row = None
    if echoed:
        row = (await session.execute(
            select(AdminWebAuthnChallenge).where(
                AdminWebAuthnChallenge.challenge == echoed,
                AdminWebAuthnChallenge.user_id == user.id,
                AdminWebAuthnChallenge.purpose == purpose,
            )
        )).scalar_one_or_none()
    if row is None:
        raise SecurityKeyError(400, "This request has expired. Please try again.",
                               "challenge_invalid")
    expired = _aware(row.expires_at) <= now
    await session.delete(row)
    await session.flush()
    if expired:
        await session.commit()
        raise SecurityKeyError(400, "This request has expired. Please try again.",
                               "challenge_invalid")
    return base64url_to_bytes(row.challenge)


# ---- registration -----------------------------------------------------------------------------
async def _user_credentials(session: AsyncSession, user: User) -> list[AdminWebAuthnCredential]:
    return list((await session.execute(
        select(AdminWebAuthnCredential).where(AdminWebAuthnCredential.user_id == user.id)
        .order_by(AdminWebAuthnCredential.id)
    )).scalars())


def _descriptor(row: AdminWebAuthnCredential) -> PublicKeyCredentialDescriptor:
    transports = []
    try:
        for t in json.loads(row.transports or "[]"):
            if t in _KNOWN_TRANSPORTS:
                transports.append(AuthenticatorTransport(t))
    except ValueError:
        pass
    return PublicKeyCredentialDescriptor(
        id=base64url_to_bytes(row.credential_id), transports=transports or None
    )


async def registration_options(session: AsyncSession, user: User, now: datetime,
                               settings: Settings | None = None, method: str = "any") -> dict:
    s = settings or get_settings()
    method = normalise_method(method)
    existing = await _user_credentials(session, user)
    if len(existing) >= MAX_KEYS:
        raise SecurityKeyError(409, f"You already have {MAX_KEYS} keys. Remove one first.")
    challenge = secrets.token_bytes(32)
    opts = generate_registration_options(
        rp_id=s.webauthn_rp_id,
        rp_name=s.lab_webauthn_rp_name,
        user_id=user.id.bytes,
        user_name=user.email,
        user_display_name=user.email,
        challenge=challenge,
        timeout=120_000,
        # method "any": no authenticatorAttachment, so USB/NFC keys AND platform passkeys
        # (Touch ID, iPhone) work. Otherwise steer the browser to the chosen kind of key.
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=METHOD_ATTACHMENT.get(method),
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=[_descriptor(r) for r in existing],
    )
    await _store_challenge(session, user, "register", challenge, now)
    await session.commit()
    return {"publicKey": _with_hints(json.loads(options_to_json(opts)), method)}


def _with_hints(public_key: dict, method: str) -> dict:
    """Add WebAuthn L3 ``hints`` (a plain JSON member; browsers that predate it ignore it)."""
    if method in METHOD_HINTS:
        public_key["hints"] = list(METHOD_HINTS[method])
    else:
        public_key.pop("hints", None)
    return public_key


@dataclass
class Registered:
    key: dict
    recovery_codes: list[str] | None
    stepup_token: str | None
    stepup_expires: datetime | None


async def register_key(session: AsyncSession, user: User, credential: dict,
                       nickname: str | None, now: datetime,
                       settings: Settings | None = None) -> Registered:
    s = settings or get_settings()
    expected = await _consume_challenge(session, user, "register", credential, now)
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=expected,
            expected_rp_id=s.webauthn_rp_id,
            expected_origin=s.webauthn_origin_list,
            require_user_verification=False,
        )
    except Exception as exc:  # noqa: BLE001 - every py_webauthn rejection is a 400
        await session.commit()
        raise SecurityKeyError(400, "The security key response could not be verified.",
                               "verification_failed") from exc
    cred_id = bytes_to_base64url(verified.credential_id)
    dup = (await session.execute(
        select(AdminWebAuthnCredential.id).where(AdminWebAuthnCredential.credential_id == cred_id)
    )).scalar_one_or_none()
    if dup is not None:
        await session.commit()
        raise SecurityKeyError(409, "This key is already registered.")
    existing = await key_count(session, user.id)
    if existing >= MAX_KEYS:
        await session.commit()
        raise SecurityKeyError(409, f"You already have {MAX_KEYS} keys. Remove one first.")
    raw_transports = credential.get("response", {}).get("transports") or []
    transports = [t for t in raw_transports if isinstance(t, str) and t in _KNOWN_TRANSPORTS]
    row = AdminWebAuthnCredential(
        user_id=user.id, credential_id=cred_id,
        public_key=bytes_to_base64url(verified.credential_public_key),
        sign_count=int(verified.sign_count), transports=json.dumps(transports),
        nickname=clean_nickname(nickname, f"Security key {existing + 1}"),
        aaguid=verified.aaguid, device_type=getattr(verified.credential_device_type, "value",
                                                    None),
        backed_up=bool(verified.credential_backed_up), created_at=now,
    )
    session.add(row)
    codes: list[str] | None = None
    token: str | None = None
    expires: datetime | None = None
    if existing == 0:
        # First key: issue fresh one-time recovery codes (replacing any older set) and grant a
        # step-up, since registering just proved possession of the key.
        codes = await _replace_recovery_codes(session, user, now)
        token, expires = await _new_stepup(session, user, "register", now, cred_id, s)
    _audit(session, user, "security_key_registered", now,
           {"nickname": row.nickname, "first": existing == 0})
    await session.commit()
    await session.refresh(row)
    return Registered(key_dict(row), codes, token, expires)


# ---- authentication ---------------------------------------------------------------------------
def _method_descriptor(row: AdminWebAuthnCredential, method: str) -> PublicKeyCredentialDescriptor:
    """Descriptor for ``row`` with transports steered to ``method``.

    Every credential id stays in the allow-list whatever the method: a synced iCloud/Google
    passkey registered on a Mac (transports internal+hybrid) must still be usable from the phone
    over hybrid when "phone" is chosen on a computer that does not hold the passkey.
    """
    if method not in METHOD_TRANSPORTS:
        return _descriptor(row)
    return PublicKeyCredentialDescriptor(
        id=base64url_to_bytes(row.credential_id),
        transports=[AuthenticatorTransport(t) for t in METHOD_TRANSPORTS[method]],
    )


async def authentication_options(session: AsyncSession, user: User, now: datetime,
                                 settings: Settings | None = None, method: str = "any") -> dict:
    s = settings or get_settings()
    method = normalise_method(method)
    creds = await _user_credentials(session, user)
    if not creds:
        raise SecurityKeyError(409, "No security key is registered yet.", "no_keys")
    challenge = secrets.token_bytes(32)
    opts = generate_authentication_options(
        rp_id=s.webauthn_rp_id,
        challenge=challenge,
        timeout=120_000,
        allow_credentials=[_method_descriptor(r, method) for r in creds],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    await _store_challenge(session, user, "authenticate", challenge, now)
    await session.commit()
    return {"publicKey": _with_hints(json.loads(options_to_json(opts)), method)}


async def _verify_assertion(session: AsyncSession, user: User, credential: dict, now: datetime,
                            settings: Settings | None = None) -> AdminWebAuthnCredential:
    """Verify one assertion against a single-use challenge; bump the sign count (no commit)."""
    s = settings or get_settings()
    expected = await _consume_challenge(session, user, "authenticate", credential, now)
    cred_id = credential.get("id") if isinstance(credential, dict) else None
    row = None
    if isinstance(cred_id, str):
        row = (await session.execute(
            select(AdminWebAuthnCredential).where(
                AdminWebAuthnCredential.credential_id == cred_id,
                AdminWebAuthnCredential.user_id == user.id,
            )
        )).scalar_one_or_none()
    if row is None:
        await session.commit()
        raise SecurityKeyError(400, "This key is not registered to your account.",
                               "unknown_key")
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=expected,
            expected_rp_id=s.webauthn_rp_id,
            expected_origin=s.webauthn_origin_list,
            credential_public_key=base64url_to_bytes(row.public_key),
            credential_current_sign_count=int(row.sign_count),
            require_user_verification=False,
        )
    except Exception as exc:  # noqa: BLE001 - includes sign-count regression (possible clone)
        await session.commit()
        raise SecurityKeyError(400, "The security key response could not be verified.",
                               "verification_failed") from exc
    user_handle = (credential.get("response") or {}).get("userHandle")
    if user_handle:
        try:
            if base64url_to_bytes(user_handle) != user.id.bytes:
                raise ValueError
        except ValueError as exc:
            await session.commit()
            raise SecurityKeyError(400, "This key belongs to a different account.",
                                   "unknown_key") from exc
    row.sign_count = int(verified.new_sign_count)
    row.last_used_at = now
    return row


async def authenticate(session: AsyncSession, user: User, credential: dict, now: datetime,
                       settings: Settings | None = None) -> tuple[str, datetime]:
    s = settings or get_settings()
    row = await _verify_assertion(session, user, credential, now, s)
    token, expires = await _new_stepup(session, user, "key", now, row.credential_id, s)
    await session.commit()
    return token, expires


# ---- recovery codes ---------------------------------------------------------------------------
async def _replace_recovery_codes(session: AsyncSession, user: User,
                                  now: datetime) -> list[str]:
    await session.execute(delete(AdminRecoveryCode).where(AdminRecoveryCode.user_id == user.id))
    codes = generate_recovery_codes()
    # Argon2 is deliberately slow; keep it off the event loop.
    hashes = await run_in_threadpool(lambda: [_hasher.hash(normalise_code(c)) for c in codes])
    for code_hash in hashes:
        session.add(AdminRecoveryCode(user_id=user.id, code_hash=code_hash, created_at=now))
    return codes


async def regenerate_recovery_codes(session: AsyncSession, user: User,
                                    now: datetime) -> list[str]:
    codes = await _replace_recovery_codes(session, user, now)
    _audit(session, user, "recovery_codes_regenerated", now)
    await session.commit()
    return codes


async def recovery_codes_remaining(session: AsyncSession, user: User) -> int:
    return int((await session.execute(
        select(func.count()).select_from(AdminRecoveryCode).where(
            AdminRecoveryCode.user_id == user.id, AdminRecoveryCode.used_at.is_(None)
        )
    )).scalar_one())


async def use_recovery_code(session: AsyncSession, user: User, code: str, now: datetime,
                            settings: Settings | None = None) -> tuple[str, datetime, int]:
    failures = int((await session.execute(
        select(func.count()).select_from(LabAdminAudit).where(
            LabAdminAudit.actor_user_id == str(user.id),
            LabAdminAudit.action == "recovery_code_failed",
            LabAdminAudit.at >= now - timedelta(hours=1),
        )
    )).scalar_one())
    if failures >= MAX_RECOVERY_FAILURES_PER_HOUR:
        raise SecurityKeyError(429, "Too many wrong recovery codes. Try again in an hour.")
    wanted = normalise_code(code)
    match = None
    if len(wanted) == 10:
        rows = list((await session.execute(
            select(AdminRecoveryCode).where(
                AdminRecoveryCode.user_id == user.id, AdminRecoveryCode.used_at.is_(None)
            )
        )).scalars())
        hashes = [r.code_hash for r in rows]
        idx = await run_in_threadpool(
            lambda: next((i for i, h in enumerate(hashes) if _hasher.verify(wanted, h)), None)
        )
        match = rows[idx] if idx is not None else None
    if match is None:
        _audit(session, user, "recovery_code_failed", now)
        await session.commit()
        raise SecurityKeyError(400, "That recovery code is not valid (or was already used).",
                               "recovery_invalid")
    match.used_at = now
    token, expires = await _new_stepup(session, user, "recovery", now, None, settings)
    remaining = await recovery_codes_remaining(session, user)
    _audit(session, user, "recovery_code_used", now, {"remaining": remaining})
    await session.commit()
    return token, expires, remaining


# ---- key management ---------------------------------------------------------------------------
async def list_keys(session: AsyncSession, user: User) -> list[dict]:
    return [key_dict(r) for r in await _user_credentials(session, user)]


async def _own_key(session: AsyncSession, user: User, key_id: int) -> AdminWebAuthnCredential:
    row = await session.get(AdminWebAuthnCredential, key_id)
    if row is None or str(row.user_id) != str(user.id):
        raise SecurityKeyError(404, "Key not found.")
    return row


async def rename_key(session: AsyncSession, user: User, key_id: int, nickname: str,
                     now: datetime) -> dict:
    row = await _own_key(session, user, key_id)
    old = row.nickname
    row.nickname = clean_nickname(nickname, old)
    _audit(session, user, "security_key_renamed", now, {"from": old, "to": row.nickname})
    await session.commit()
    return key_dict(row)


async def delete_key(session: AsyncSession, user: User, key_id: int, now: datetime,
                     settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    row = await _own_key(session, user, key_id)
    remaining = await key_count(session, user.id) - 1
    if remaining == 0 and s.lab_hardware_key_mode != "off":
        raise SecurityKeyError(
            409, "You can't remove your last key while keys are required. Add another key "
                 "first.", "last_key")
    nickname = row.nickname
    await session.delete(row)
    _audit(session, user, "security_key_removed", now, {"nickname": nickname})
    await session.commit()
    return {"deleted": key_id, "remaining": remaining}


async def status(session: AsyncSession, user: User, token: str | None, now: datetime,
                 settings: Settings | None = None,
                 device: AdminTrustedDevice | None = None) -> dict:
    """``device`` is this browser's device row (see :func:`ensure_device`), if known."""
    s = settings or get_settings()
    keys = await key_count(session, user.id)
    mode = s.lab_hardware_key_mode
    live = await active_stepup(session, user, token, now)
    trusted = keys > 0 and device is not None and device_is_trusted(device, now)
    return {
        "unlocked": (not stepup_required_for(mode, keys)) or live is not None or trusted,
        "device": device_dict(device, device.id, now) if device is not None else None,
        "trusted_device_days": s.trusted_device_days,
        "enforcement": mode,
        "required": stepup_required_for(mode, keys),
        "keys": keys,
        "step_up": {
            "active": live is not None,
            "expires_at": _iso(live.expires_at) if live else None,
            "method": live.method if live else None,
        },
        "recovery_codes_remaining": await recovery_codes_remaining(session, user),
        "rp_id": s.webauthn_rp_id,
        "stepup_hours": s.lab_stepup_hours,
    }



# ---- devices + per-device trust ---------------------------------------------------------------
def device_label(user_agent: str | None) -> str:
    """A short default nickname from a User-Agent, e.g. "Mac · Safari" or "iPhone · Chrome"."""
    ua = user_agent or ""
    if "iPhone" in ua:
        system = "iPhone"
    elif "iPad" in ua:
        system = "iPad"
    elif "Android" in ua:
        system = "Android"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        system = "Mac"
    elif "Windows" in ua:
        system = "Windows"
    elif "CrOS" in ua:
        system = "Chromebook"
    elif "Linux" in ua:
        system = "Linux"
    else:
        system = "Device"
    if "Edg/" in ua or "EdgiOS" in ua or "EdgA" in ua:
        browser = "Edge"
    elif "Firefox/" in ua or "FxiOS" in ua:
        browser = "Firefox"
    elif "Chrome/" in ua or "CriOS" in ua:
        browser = "Chrome"
    elif "Safari/" in ua:
        browser = "Safari"
    else:
        browser = "Browser"
    return f"{system} · {browser}"


def device_is_trusted(row: AdminTrustedDevice, now: datetime) -> bool:
    """Trusted and unexpired. ``LAB_TRUSTED_DEVICE_DAYS=0`` switches the feature off, and then
    existing trust stops counting at once."""
    if get_settings().trusted_device_days <= 0:
        return False
    until = _aware(row.trusted_until)
    return until is not None and until > now


def device_dict(row: AdminTrustedDevice, current_id: int | None, now: datetime) -> dict:
    trusted = device_is_trusted(row, now)
    return {
        "id": row.id,
        "nickname": row.nickname,
        "first_seen_at": _iso(row.first_seen_at),
        "last_seen_at": _iso(row.last_seen_at),
        "trusted": trusted,
        "trusted_at": _iso(row.trusted_at) if trusted else None,
        "trusted_until": _iso(row.trusted_until) if trusted else None,
        "current": current_id is not None and row.id == current_id,
    }


def _valid_device_token(token: str | None) -> bool:
    return bool(token) and 16 <= len(token) <= 256


async def find_device(session: AsyncSession, user: User,
                      device_token: str | None) -> AdminTrustedDevice | None:
    if not _valid_device_token(device_token):
        return None
    return (await session.execute(
        select(AdminTrustedDevice).where(
            AdminTrustedDevice.user_id == user.id,
            AdminTrustedDevice.device_sha256 == token_hash(device_token),
        )
    )).scalar_one_or_none()


async def trusted_device(session: AsyncSession, user: User, device_token: str | None,
                         now: datetime) -> AdminTrustedDevice | None:
    """This browser's device row if it is one of ``user``'s trusted, unexpired devices."""
    row = await find_device(session, user, device_token)
    if row is None or not device_is_trusted(row, now):
        return None
    return row


async def _touch_device(session: AsyncSession, row: AdminTrustedDevice, now: datetime) -> None:
    """Record last-seen at most every DEVICE_TOUCH_EVERY (best effort, never blocks a request)."""
    last = _aware(row.last_seen_at)
    if last is not None and now - last < DEVICE_TOUCH_EVERY:
        return
    try:
        row.last_seen_at = now
        await session.commit()
    except Exception:  # noqa: BLE001 - a last-seen write must never fail the request
        await session.rollback()


async def ensure_device(
    session: AsyncSession, user: User, device_token: str | None, user_agent: str | None,
    now: datetime,
) -> tuple[AdminTrustedDevice, str | None]:
    """This browser's device row for ``user`` (created on first sight) and, when the browser had
    no usable device cookie, the new token to set. Commits."""
    row = await find_device(session, user, device_token)
    if row is not None:
        last = _aware(row.last_seen_at)
        if last is None or now - last >= timedelta(minutes=1):
            row.last_seen_at = now
            await session.commit()
        return row, None
    new_token = None
    if not _valid_device_token(device_token):
        new_token = secrets.token_urlsafe(32)
        device_token = new_token
    # Bounded table: forget this user's least recently seen UNTRUSTED devices beyond the cap.
    rows = list((await session.execute(
        select(AdminTrustedDevice).where(AdminTrustedDevice.user_id == user.id)
    )).scalars())
    spare = sorted((r for r in rows if not device_is_trusted(r, now)),
                   key=lambda r: _aware(r.last_seen_at or r.first_seen_at))
    excess = len(rows) - (MAX_DEVICES - 1)
    for old in spare[:max(0, excess)]:
        await session.delete(old)
    ua = (user_agent or "")[:USER_AGENT_MAX] or None
    row = AdminTrustedDevice(
        user_id=user.id, device_sha256=token_hash(device_token), nickname=device_label(ua),
        user_agent=ua, first_seen_at=now, last_seen_at=now,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row, new_token


async def list_devices(session: AsyncSession, user: User, current: AdminTrustedDevice | None,
                       now: datetime) -> list[dict]:
    rows = list((await session.execute(
        select(AdminTrustedDevice).where(AdminTrustedDevice.user_id == user.id)
    )).scalars())
    rows.sort(key=lambda r: _aware(r.last_seen_at or r.first_seen_at), reverse=True)
    cur = current.id if current is not None else None
    return [device_dict(r, cur, now) for r in rows]


async def trust_this_device(session: AsyncSession, user: User, credential: dict,
                            device_token: str | None, user_agent: str | None, now: datetime,
                            settings: Settings | None = None) -> tuple[dict, str | None]:
    """Mark the CURRENT browser as trusted. Needs a fresh key assertion made on this device."""
    s = settings or get_settings()
    days = s.trusted_device_days
    if days <= 0:
        raise SecurityKeyError(409, "Trusted devices are switched off on the server.",
                               "trust_disabled")
    await _verify_assertion(session, user, credential, now, s)
    await session.commit()  # keep the consumed challenge + new sign count even if below fails
    row, new_token = await ensure_device(session, user, device_token, user_agent, now)
    row.trusted_at = now
    row.trusted_until = now + timedelta(days=days)
    _audit(session, user, "device_trusted", now,
           {"device": row.nickname, "device_id": row.id, "days": days,
            "until": row.trusted_until.isoformat()})
    await session.commit()
    return device_dict(row, row.id, now), new_token


async def _own_device(session: AsyncSession, user: User, device_id: int) -> AdminTrustedDevice:
    row = await session.get(AdminTrustedDevice, device_id)
    if row is None or str(row.user_id) != str(user.id):
        raise SecurityKeyError(404, "Device not found.")
    return row


async def untrust_device(session: AsyncSession, user: User, device_id: int, now: datetime,
                         reason: str = "owner") -> dict:
    row = await _own_device(session, user, device_id)
    was = device_is_trusted(row, now)
    row.trusted_until = None
    row.trusted_at = None
    if was:
        _audit(session, user, "device_trust_revoked", now,
               {"device": row.nickname, "device_id": row.id, "reason": reason})
    await session.commit()
    return device_dict(row, None, now)


async def rename_device(session: AsyncSession, user: User, device_id: int, nickname: str,
                        now: datetime) -> dict:
    row = await _own_device(session, user, device_id)
    old = row.nickname
    row.nickname = clean_nickname(nickname, old)
    await session.commit()
    return device_dict(row, None, now)


async def forget_device(session: AsyncSession, user: User, device_id: int, now: datetime) -> dict:
    row = await _own_device(session, user, device_id)
    nickname, was = row.nickname, device_is_trusted(row, now)
    await session.delete(row)
    if was:
        _audit(session, user, "device_trust_revoked", now,
               {"device": nickname, "device_id": device_id, "reason": "forgotten"})
    await session.commit()
    return {"deleted": device_id}


async def lock_this_browser(session: AsyncSession, user: User, stepup_token: str | None,
                            device_token: str | None, now: datetime) -> None:
    """"Lock now": revoke this browser's step-up AND end trust on this device, if any."""
    row = await find_device(session, user, device_token)
    if row is not None and device_is_trusted(row, now):
        await untrust_device(session, user, row.id, now, reason="lock_now")
    await revoke_stepup(session, user, stepup_token, now)
