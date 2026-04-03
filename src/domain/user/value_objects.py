from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.user import User


@dataclass(frozen=True, slots=True)
class SearchFilter:
    direction_id: UUID | None
    user_status: UserStatus | None
    specialty_query: str | None
    exclude_user_id: UUID
    seeking_mode: TeamSeekingMode


@dataclass(frozen=True, slots=True)
class SearchResult:
    users: list[User]
    total: int
    offset: int
    limit: int
