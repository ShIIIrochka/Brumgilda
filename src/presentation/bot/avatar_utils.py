"""Shared avatar/photo utilities for profile and search cards."""

from __future__ import annotations

import logging
import os
from uuid import UUID

from aiogram.types import BufferedInputFile, FSInputFile
from punq import Container

from src.application.usecases.user.update_user_profile import UpdateUserProfile
from src.domain.user import draft_keys as dk
from src.domain.user.enums import IdentityProvider
from src.domain.user.repositories import IUserIdentityRepository
from src.domain.user.user import User

logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
DEFAULT_AVATAR_PATH = os.path.normpath(os.path.join(_ASSETS_DIR, "default_avatar.png"))

# Cached Telegram file_id for the default avatar (set after first upload)
_cached_placeholder_file_id: str | None = None


def format_age_caption(user: User) -> str:
    if user.age is None:
        return "возраст не указан"
    return f"{user.age} лет"


def default_photo_input() -> FSInputFile | BufferedInputFile | str:
    global _cached_placeholder_file_id
    if _cached_placeholder_file_id:
        return _cached_placeholder_file_id
    if os.path.isfile(DEFAULT_AVATAR_PATH):
        return FSInputFile(DEFAULT_AVATAR_PATH)
    # Minimal 1x1 PNG fallback
    return BufferedInputFile(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82",
        filename="avatar.png",
    )


def cache_placeholder_file_id(file_id: str) -> None:
    """Call after first successful send of placeholder to cache its file_id."""
    global _cached_placeholder_file_id
    _cached_placeholder_file_id = file_id


async def fetch_telegram_profile_photo_file_id(bot, telegram_user_id: int) -> str | None:
    try:
        photos = await bot.get_user_profile_photos(telegram_user_id, limit=1)
        if photos.total_count > 0:
            return photos.photos[0][-1].file_id
    except Exception:
        logger.debug("get_user_profile_photos failed for %s", telegram_user_id, exc_info=True)
    return None


async def persist_telegram_avatar_file_id(
    bot,
    container: Container,
    internal_user_id: UUID,
    telegram_actor_id: int,
) -> None:
    fid = await fetch_telegram_profile_photo_file_id(bot, telegram_actor_id)
    if not fid:
        return
    try:
        await container.resolve(UpdateUserProfile).execute(
            internal_user_id,
            {dk.TELEGRAM_AVATAR_FILE_ID: fid},
        )
    except Exception:
        logger.exception("persist telegram_avatar_file_id failed")


async def resolve_photo_for_card(
    bot,
    container: Container,
    subject_user: User,
) -> FSInputFile | BufferedInputFile | str:
    # 1. Already have cached file_id
    if subject_user.telegram_avatar_file_id:
        return subject_user.telegram_avatar_file_id

    # 2. Try to fetch from Telegram via identity
    identities = container.resolve(IUserIdentityRepository)
    sid = await identities.find_subject_id_for_user(subject_user.id, IdentityProvider.TELEGRAM)
    if sid:
        fid = await fetch_telegram_profile_photo_file_id(bot, int(sid))
        if fid:
            return fid

    # 3. Default placeholder
    return default_photo_input()
