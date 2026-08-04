"""Alert configuration, read from environment variables. Never hardcodes credentials.

External email sending is OFF unless ``ALERT_EMAIL_ENABLED=true`` and a provider is configured.
The recipient variable is prepared for dayyansheikh.work@gmail.com but defaults to empty so
nothing is ever sent without explicit configuration.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _envbool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _envfloat(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _envint(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class AlertConfig:
    enabled: bool = False               # ALERT_EMAIL_ENABLED (external sending)
    provider: str = "console"           # ALERT_PROVIDER: console | smtp | resend
    recipient: str = ""                 # ALERT_RECIPIENT (e.g. dayyansheikh.work@gmail.com)
    sender: str = "arepo-alerts@localhost"   # ALERT_SENDER (must be a verified Resend sender)
    test_mode: bool = False             # ALERT_TEST_MODE: build+record but do not send externally

    # Resend provider (spec §18): HTTPS API, key from env only.
    resend_api_key: str = ""            # RESEND_API_KEY (never hardcode; from env only)

    # Eligibility thresholds (spec section 11), all configurable.
    min_strength: float = 0.40          # ALERT_MIN_STRENGTH
    min_confidence: float = 0.40        # ALERT_MIN_CONFIDENCE
    min_families: int = 2               # ALERT_MIN_FAMILIES
    min_priority: int = 50              # ALERT_MIN_PRIORITY (0-100)
    cooldown_hours: float = 12.0        # ALERT_COOLDOWN_HOURS (per market)
    max_retries: int = 2                # ALERT_MAX_RETRIES

    # SMTP provider details (only used when provider == "smtp" AND enabled). From env only.
    smtp_host: str = ""                 # ALERT_SMTP_HOST
    smtp_port: int = 587                # ALERT_SMTP_PORT
    smtp_user: str = ""                 # ALERT_SMTP_USER
    smtp_password: str = ""             # ALERT_SMTP_PASSWORD (never hardcode; from env only)

    @classmethod
    def from_env(cls) -> AlertConfig:
        return cls(
            enabled=_envbool("ALERT_EMAIL_ENABLED", False),
            provider=os.environ.get("ALERT_PROVIDER", "console"),
            recipient=os.environ.get("ALERT_RECIPIENT", ""),
            sender=os.environ.get("ALERT_SENDER", "arepo-alerts@localhost"),
            test_mode=_envbool("ALERT_TEST_MODE", False),
            min_strength=_envfloat("ALERT_MIN_STRENGTH", 0.40),
            min_confidence=_envfloat("ALERT_MIN_CONFIDENCE", 0.40),
            min_families=_envint("ALERT_MIN_FAMILIES", 2),
            min_priority=_envint("ALERT_MIN_PRIORITY", 50),
            cooldown_hours=_envfloat("ALERT_COOLDOWN_HOURS", 12.0),
            max_retries=_envint("ALERT_MAX_RETRIES", 2),
            smtp_host=os.environ.get("ALERT_SMTP_HOST", ""),
            smtp_port=_envint("ALERT_SMTP_PORT", 587),
            smtp_user=os.environ.get("ALERT_SMTP_USER", ""),
            smtp_password=os.environ.get("ALERT_SMTP_PASSWORD", ""),
            resend_api_key=os.environ.get("RESEND_API_KEY", ""),
        )

    @property
    def can_send_externally(self) -> bool:
        """True only when external sending is genuinely configured and allowed."""
        if not self.enabled or self.test_mode:
            return False
        if self.provider == "smtp":
            return bool(self.smtp_host and self.recipient)
        if self.provider == "resend":
            return bool(self.resend_api_key and self.sender)
        return False  # the console provider never sends externally
