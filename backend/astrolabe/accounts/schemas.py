"""Pydantic schemas for accounts, preferences, saved markets and alert history."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi_users import schemas
from pydantic import BaseModel, Field, field_validator

from ..categories import USER_SELECTABLE_CATEGORIES

DigestFrequency = Literal["off", "every_6h", "daily", "twice_daily", "weekly"]
DigestTopN = Literal[5, 10, 20]


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str | None = None
    last_name: str | None = None
    auth_provider: str = "local"
    consent_at: datetime | None = None


class UserCreate(schemas.BaseUserCreate):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Name cannot be blank")
        return cleaned


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Name cannot be blank")
        return cleaned


class PreferenceRead(BaseModel):
    email_enabled: bool
    immediate_exceptional: bool
    daily_digest: bool
    weekly_summary: bool
    min_research_priority: int
    min_confidence: float
    categories: list[str]
    short_term_only: bool
    max_hours_to_close: int | None
    paused: bool
    unsubscribed: bool
    digest_frequency: DigestFrequency
    digest_top_n: DigestTopN
    digest_unsubscribed: bool
    updated_at: datetime | None = None


class PreferenceUpdate(BaseModel):
    """All fields optional: a PATCH-style partial update. Ranges are validated."""

    email_enabled: bool | None = None
    immediate_exceptional: bool | None = None
    daily_digest: bool | None = None
    weekly_summary: bool | None = None
    min_research_priority: int | None = Field(default=None, ge=0, le=100)
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    categories: list[str] | None = None
    short_term_only: bool | None = None
    max_hours_to_close: int | None = Field(default=None, ge=1, le=24 * 30)
    paused: bool | None = None
    unsubscribed: bool | None = None
    digest_frequency: DigestFrequency | None = None
    digest_top_n: DigestTopN | None = None

    @field_validator("categories")
    @classmethod
    def supported_categories(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unsupported = sorted(set(value) - set(USER_SELECTABLE_CATEGORIES))
        if unsupported:
            raise ValueError(f"Unsupported digest categories: {', '.join(unsupported)}")
        return list(dict.fromkeys(value))


class DigestSummaryRead(BaseModel):
    id: int
    sent_at: datetime
    frequency: DigestFrequency
    signal_count: int
    categories: list[str]


class DigestListRead(BaseModel):
    items: list[DigestSummaryRead]
    has_more: bool


class DigestEvaluationRead(BaseModel):
    horizon: str
    state: str
    unavailable_reason: str | None = None
    resolved: bool = False
    resolved_outcome: str | None = None
    resolution_correct: bool | None = None


class DigestEntryRead(BaseModel):
    rank: int
    market_id: str
    token_id: str
    market_question: str
    outcome_name: str
    canonical_url: str
    category: str
    direction: str
    strength: float
    research_priority: int
    signal_captured_at: datetime
    evaluation: DigestEvaluationRead


class DigestDetailRead(BaseModel):
    id: int
    sent_at: datetime
    frequency: DigestFrequency
    categories: list[str]
    evaluation_horizon: str
    entries: list[DigestEntryRead]


class DigestUnsubscribeRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class DigestUnsubscribeRead(BaseModel):
    ok: bool = True


class SavedMarketRead(BaseModel):
    market_id: str
    question: str
    created_at: datetime


class SavedMarketCreate(BaseModel):
    market_id: str
    question: str = ""


class AlertDeliveryRead(BaseModel):
    market_id: str
    token_id: str
    subject: str
    status: str
    detail: str
    at: datetime
