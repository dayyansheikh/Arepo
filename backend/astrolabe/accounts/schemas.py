"""Pydantic schemas for accounts, preferences, saved markets and alert history."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import BaseModel, Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    auth_provider: str = "local"
    consent_at: datetime | None = None


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


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
