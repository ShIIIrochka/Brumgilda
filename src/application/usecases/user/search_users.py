from __future__ import annotations

from src.domain.user.repositories import IUserRepository
from src.domain.user.value_objects import SearchFilter, SearchResult


class SearchUsers:
    def __init__(self, users: IUserRepository) -> None:
        self._users = users

    async def execute(self, fltr: SearchFilter, offset: int = 0, limit: int = 1) -> SearchResult:
        return await self._users.search(fltr, offset, limit)
