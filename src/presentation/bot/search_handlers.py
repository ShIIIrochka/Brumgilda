from __future__ import annotations

import os
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from punq import Container
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.usecases.user.get_user import GetUser
from src.application.usecases.user.search_users import SearchUsers
from src.domain.directions.repository import IDirectionRepository
from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.user import User
from src.domain.user.value_objects import SearchFilter
from src.infra.database.directions_seed import ensure_directions_seed
from src.presentation.bot import keyboards as kb
from src.presentation.bot.states import Search

router = Router(name="search")

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
_DEFAULT_AVATAR = os.path.normpath(os.path.join(_ASSETS_DIR, "default_avatar.png"))

_STATUS_LABELS = {
    UserStatus.SCHOOL: "Школьник",
    UserStatus.STUDENT: "Студент",
    UserStatus.MASTER: "Магистрант",
    UserStatus.NOT_STUDYING: "Не учусь",
}

_MODE_LABELS = {
    TeamSeekingMode.LOOKING_FOR_TEAM: "Ищу команду",
    TeamSeekingMode.LOOKING_FOR_PEOPLE: "Ищу людей",
}


def _build_card_caption(user: User, direction_name: str | None) -> str:
    lines: list[str] = []
    name_line = f"{user.first_name} {user.last_name}, {user.age} лет"
    if user.telegram_username:
        name_line += f"  @{user.telegram_username}"
    lines.append(name_line)
    dir_label = direction_name or user.custom_direction_label or "—"
    lines.append(f"Направление: {dir_label}")
    if user.user_status:
        status_label = _STATUS_LABELS.get(user.user_status, user.user_status.value)
        lines.append(f"Статус: {status_label}")
        if user.user_status == UserStatus.SCHOOL and user.school_grade:
            lines.append(f"  Класс: {user.school_grade}")
            if user.school_name:
                lines.append(f"  Школа: {user.school_name}")
        elif user.user_status in (UserStatus.STUDENT, UserStatus.MASTER):
            if user.student_course:
                lines.append(f"  Курс: {user.student_course}")
            if user.university:
                lines.append(f"  ВУЗ: {user.university}")
            if user.specialty:
                lines.append(f"  Специальность: {user.specialty}")
    if user.has_olympiad_experience:
        lines.append(f"Олимпиады: {user.olympiad_description or '—'}")
        if user.olympiad_links:
            lines.append("  Ссылки: " + ", ".join(user.olympiad_links))
    if user.team_seeking_mode:
        lines.append(_MODE_LABELS.get(user.team_seeking_mode, ""))
    return "\n".join(lines)


async def _get_avatar(user: User, bot, container: Container) -> FSInputFile | str:
    if user.telegram_avatar_file_id:
        return user.telegram_avatar_file_id
    return FSInputFile(_DEFAULT_AVATAR)


async def _show_result(
    target: Message,
    container: Container,
    state: FSMContext,
    bot,
    user_id: UUID,
) -> None:
    data = await state.get_data()
    direction_id = data.get("search_direction_id")
    status_raw = data.get("search_status")
    offset = data.get("search_offset", 0)

    me = await container.resolve(GetUser).execute(user_id)
    if me is None or me.team_seeking_mode is None:
        await target.answer("Сначала завершите регистрацию: /start")
        return

    opposite_mode = (
        TeamSeekingMode.LOOKING_FOR_TEAM
        if me.team_seeking_mode == TeamSeekingMode.LOOKING_FOR_PEOPLE
        else TeamSeekingMode.LOOKING_FOR_PEOPLE
    )

    specialty_q = data.get("search_specialty")

    fltr = SearchFilter(
        direction_id=UUID(direction_id) if direction_id else None,
        user_status=UserStatus(status_raw) if status_raw else None,
        specialty_query=specialty_q or None,
        exclude_user_id=user_id,
        seeking_mode=opposite_mode,
    )

    result = await container.resolve(SearchUsers).execute(fltr, offset=offset, limit=1)

    if result.total == 0:
        await target.answer("Никого не найдено. Попробуйте другие фильтры: /search")
        await state.clear()
        return

    found_user = result.users[0]
    dirs = container.resolve(IDirectionRepository)
    direction_name = None
    if found_user.direction_id:
        d = await dirs.get_by_id(found_user.direction_id)
        if d:
            direction_name = d.name

    caption = _build_card_caption(found_user, direction_name)
    photo = await _get_avatar(found_user, bot, container)
    pagination = kb.search_pagination_keyboard(offset, result.total)

    await target.answer_photo(photo=photo, caption=caption, reply_markup=pagination)


@router.message(Command("search"))
async def cmd_search(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    user = await container.resolve(GetUser).execute(user_id)
    if user is None or not user.is_onboarding_complete:
        await message.answer("Сначала завершите регистрацию: /start")
        return
    await state.clear()

    session = container.resolve(AsyncSession)
    await ensure_directions_seed(session)
    await session.flush()

    dirs = container.resolve(IDirectionRepository)
    roots = await dirs.list_roots()
    await state.set_state(Search.pick_direction)
    await state.update_data(search_direction_id=None, search_status=None, search_specialty=None, search_offset=0)
    await message.answer(
        "Поиск сокомандников. Выберите направление:",
        reply_markup=kb.search_direction_keyboard(roots, show_back=False),
    )


@router.callback_query(Search.pick_direction, F.data == "sdir:any")
async def on_search_dir_any(
    cq: CallbackQuery, state: FSMContext, **_: object
) -> None:
    await cq.answer()
    await state.update_data(search_direction_id=None)
    await state.set_state(Search.pick_status)
    await cq.message.answer(
        "Выберите статус:", reply_markup=kb.search_status_keyboard()
    )


@router.callback_query(Search.pick_direction, F.data == "sdir:back")
async def on_search_dir_back(
    cq: CallbackQuery, state: FSMContext, container: Container, **_: object
) -> None:
    await cq.answer()
    data = await state.get_data()
    vp = data.get("view_parent_id")
    if vp is None:
        return
    dirs = container.resolve(IDirectionRepository)
    node = await dirs.get_by_id(vp)
    gp = node.parent_id if node else None
    nxt_list = await dirs.list_children(gp) if gp else await dirs.list_roots()
    await state.update_data(view_parent_id=gp)
    await cq.message.edit_reply_markup(
        reply_markup=kb.search_direction_keyboard(nxt_list, show_back=gp is not None)
    )


@router.callback_query(Search.pick_direction, F.data.startswith("sdir:"))
async def on_search_dir_pick(
    cq: CallbackQuery, state: FSMContext, container: Container, **_: object
) -> None:
    raw = (cq.data or "")[5:]
    await cq.answer()
    try:
        picked_id = UUID(raw)
    except ValueError:
        return
    dirs = container.resolve(IDirectionRepository)
    node = await dirs.get_by_id(picked_id)
    if node is None:
        return
    children = await dirs.list_children(node.id)
    if children:
        await state.update_data(view_parent_id=node.id)
        await cq.message.edit_reply_markup(
            reply_markup=kb.search_direction_keyboard(children, show_back=True)
        )
        return
    await state.update_data(search_direction_id=str(node.id))
    await state.set_state(Search.pick_status)
    await cq.message.edit_reply_markup(reply_markup=None)
    await cq.message.answer(
        "Выберите статус:", reply_markup=kb.search_status_keyboard()
    )


@router.callback_query(Search.pick_status, F.data.startswith("sst:"))
async def on_search_status(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    raw = (cq.data or "")[4:]
    status_val = None if raw == "any" else raw
    await state.update_data(search_status=status_val, search_offset=0)
    if status_val in (UserStatus.STUDENT.value, UserStatus.MASTER.value):
        await state.set_state(Search.pick_specialty)
        await cq.message.answer(
            "Введите специальность для поиска (или отправьте «-» чтобы пропустить):"
        )
        return
    await state.update_data(search_specialty=None)
    await state.set_state(Search.browsing)
    await _show_result(cq.message, container, state, cq.bot, user_id)


@router.message(Search.pick_specialty, F.text)
async def on_search_specialty(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    text = (message.text or "").strip()
    spec_val = None if text == "-" else text
    await state.update_data(search_specialty=spec_val, search_offset=0)
    await state.set_state(Search.browsing)
    await _show_result(message, container, state, message.bot, user_id)


@router.callback_query(Search.browsing, F.data == "spg:prev")
async def on_search_prev(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    data = await state.get_data()
    offset = max(0, data.get("search_offset", 0) - 1)
    await state.update_data(search_offset=offset)
    await _show_result(cq.message, container, state, cq.bot, user_id)


@router.callback_query(Search.browsing, F.data == "spg:next")
async def on_search_next(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    data = await state.get_data()
    offset = data.get("search_offset", 0) + 1
    await state.update_data(search_offset=offset)
    await _show_result(cq.message, container, state, cq.bot, user_id)


@router.callback_query(Search.browsing, F.data == "spg:noop")
async def on_search_noop(cq: CallbackQuery, **_: object) -> None:
    await cq.answer()
