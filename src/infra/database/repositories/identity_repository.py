from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.user.enums import IdentityProvider
from src.infra.database.models import UserIdentityModel


class SqlAlchemyUserIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user_id_by_identity(
        self, provider: IdentityProvider, subject_id: str
    ) -> UUID | None:
        result = await self._session.execute(
            select(UserIdentityModel.user_id).where(
                UserIdentityModel.provider == provider.value,
                UserIdentityModel.subject_id == subject_id,
            )
        )
        return result.scalar_one_or_none()

    async def link_identity(self, user_id: UUID, provider: IdentityProvider, subject_id: str) -> None:
        row = UserIdentityModel(
            id=uuid.uuid4(),
            user_id=user_id,
            provider=provider.value,
            subject_id=subject_id,
        )
        self._session.add(row)
        await self._session.flush()

    async def find_subject_id_for_user(
        self, user_id: UUID, provider: IdentityProvider
    ) -> str | None:
        result = await self._session.execute(
            select(UserIdentityModel.subject_id).where(
                UserIdentityModel.user_id == user_id,
                UserIdentityModel.provider == provider.value,
            )
        )
        return result.scalar_one_or_none()
