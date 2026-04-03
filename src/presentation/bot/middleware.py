from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.usecases.user.get_user import GetUser
from src.application.usecases.user.resolve_or_create_user_by_external_identity import (
    ResolveOrCreateUserByExternalIdentity,
)
from src.domain.user.enums import IdentityProvider
from src.infra.database.adapter import session_scope
from src.infra.di import build_container


class AppMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope(self._session_factory) as session:
            data["session"] = session
            container = build_container(session)
            data["container"] = container

            user_id = None
            tg_user = None
            if isinstance(event, Message) and event.from_user:
                tg_user = event.from_user
            elif isinstance(event, CallbackQuery) and event.from_user:
                tg_user = event.from_user

            if tg_user is not None:
                uc = container.resolve(ResolveOrCreateUserByExternalIdentity)
                user_id = await uc.execute(
                    IdentityProvider.TELEGRAM, str(tg_user.id)
                )
                # Sync telegram username and avatar on every request
                gu = container.resolve(GetUser)
                user = await gu.execute(user_id)
                if user is not None:
                    changed = False
                    if tg_user.username and user.telegram_username != tg_user.username:
                        user.telegram_username = tg_user.username
                        changed = True
                    if changed:
                        from src.domain.user.repositories import IUserRepository
                        repo = container.resolve(IUserRepository)
                        await repo.save(user)

            data["user_id"] = user_id

            return await handler(event, data)
