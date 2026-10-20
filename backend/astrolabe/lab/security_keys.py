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
                      settings: Settings | None = None) -> int | None:
    """None when this user may act now; otherwise their key count (they need to unlock first).

    Locked = enforcement applies to them (they have a key, or mode "always" and they are a
    superuser) and the step-up token is not a live step-up of theirs.
    """
    mode = (settings or get_settings()).lab_hardware_key_mode
    if mode == "off":
        return None
    keys = await key_count(session, user.id)
    if keys == 0 and not (mode == "always" and user.is_superuser):
        return None
    if await active_stepup(session, user, token, now) is not None:
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
                               settings: Settings | None = None) -> dict:
    s = settings or get_settings()
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
        # No authenticatorAttachment: USB/NFC keys AND platform passkeys (Touch ID, iPhone) work.
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=[_descriptor(r) for r in existing],
    )
    await _store_challenge(session, user, "register", challenge, now)
    await session.commit()
    return {"publicKey": json.loads(options_to_json(opts))}


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
async def authentication_options(session: AsyncSession, user: User, now: datetime,
                                 settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    creds = await _user_credentials(session, user)
    if not creds:
        raise SecurityKeyError(409, "No security key is registered yet.", "no_keys")
    challenge = secrets.token_bytes(32)
    opts = generate_authentication_options(
        rp_id=s.webauthn_rp_id,
        challenge=challenge,
        timeout=120_000,
        allow_credentials=[_descriptor(r) for r in creds],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    await _store_challenge(session, user, "authenticate", challenge, now)
    await session.commit()
    return {"publicKey": json.loads(options_to_json(opts))}


async def authenticate(session: AsyncSession, user: User, credential: dict, now: datetime,
                       settings: Settings | None = None) -> tuple[str, datetime]:
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
                 settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    keys = await key_count(session, user.id)
    mode = s.lab_hardware_key_mode
    live = await active_stepup(session, user, token, now)
    return {
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
