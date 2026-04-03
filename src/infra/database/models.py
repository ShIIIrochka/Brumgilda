from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.database.base import Base


class DirectionModel(Base):
    __tablename__ = "directions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("directions.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_other: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    onboarding_draft: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("directions.id", ondelete="SET NULL"), nullable=True
    )
    custom_direction_label: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    school_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(512), nullable=True)

    student_course: Mapped[int | None] = mapped_column(Integer, nullable=True)
    university: Mapped[str | None] = mapped_column(String(512), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(512), nullable=True)

    has_olympiad_experience: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    olympiad_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    olympiad_links: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")

    team_seeking_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)

    telegram_avatar_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    identities: Mapped[list[UserIdentityModel]] = relationship(
        "UserIdentityModel", back_populates="user", cascade="all, delete-orphan"
    )


class UserIdentityModel(Base):
    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "subject_id", name="uq_identity_provider_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[UserModel] = relationship("UserModel", back_populates="identities")
