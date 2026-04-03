from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.user.enums import IdentityProvider
from src.domain.user.user import User
from src.domain.user.value_objects import SearchFilter, SearchResult


class IUserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def save(self, user: User) -> None: ...
    async def search(self, fltr: SearchFilter, offset: int, limit: int) -> SearchResult: ...


class IUserIdentityRepository(Protocol):
    async def find_user_id_by_identity(
        self, provider: IdentityProvider, subject_id: str
    ) -> UUID | None: ...

    async def link_identity(self, user_id: UUID, provider: IdentityProvider, subject_id: str) -> None: ...

    async def find_subject_id_for_user(
        self, user_id: UUID, provider: IdentityProvider
    ) -> str | None: ...
