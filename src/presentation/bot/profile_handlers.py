from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from punq import Container
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.usecases.user.get_user import GetUser
from src.application.usecases.user.update_user_profile import UpdateUserProfile
from src.domain.directions.repository import IDirectionRepository
from src.domain.user import draft_keys as dk
from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.exceptions import DomainValidationError
from src.domain.user.user import User
from src.infra.database.directions_seed import ensure_directions_seed
from src.presentation.bot import keyboards as kb
from src.presentation.bot.avatar_utils import (
    format_age_caption,
    persist_telegram_avatar_file_id,
    resolve_photo_for_card,
)
from src.presentation.bot.states import ProfileEdit

router = Router(name="profile")

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


async def _update_profile_or_fail(
    message: Message, container: Container, user_id: UUID, updates: dict
) -> bool:
    try:
        await container.resolve(UpdateUserProfile).execute(user_id, updates)
    except DomainValidationError as e:
        await message.answer(f"Ошибка: {e}")
        return False
    return True


def _build_profile_caption(user: User, direction_name: str | None) -> str:
    lines: list[str] = []
    fn = user.first_name or "—"
    ln = user.last_name or "—"
    name_line = f"{fn} {ln}, {format_age_caption(user)}"
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


async def _send_profile_card(
    target: Message,
    user: User,
    container: Container,
    bot,
    *,
    telegram_actor_id: int | None = None,
    reply_markup=None,
) -> None:
    if telegram_actor_id is not None:
        await persist_telegram_avatar_file_id(bot, container, user.id, telegram_actor_id)
        refreshed = await container.resolve(GetUser).execute(user.id)
        if refreshed is not None:
            user = refreshed

    dirs = container.resolve(IDirectionRepository)
    direction_name = None
    if user.direction_id:
        d = await dirs.get_by_id(user.direction_id)
        if d:
            direction_name = d.name
    caption = _build_profile_caption(user, direction_name)
    photo = await resolve_photo_for_card(bot, container, user)
    await target.answer_photo(photo=photo, caption=caption, reply_markup=reply_markup)


@router.message(Command("profile"))
async def cmd_profile(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    await state.clear()
    user = await container.resolve(GetUser).execute(user_id)
    if user is None or not user.is_onboarding_complete:
        await message.answer("Сначала завершите регистрацию: /start")
        return
    await _send_profile_card(
        message,
        user,
        container,
        message.bot,
        telegram_actor_id=message.from_user.id,
        reply_markup=kb.profile_edit_keyboard(),
    )


@router.callback_query(F.data == "pedit:first_name")
async def pedit_first_name(cq: CallbackQuery, state: FSMContext, **_: object) -> None:
    await cq.answer()
    await state.set_state(ProfileEdit.first_name)
    await cq.message.answer("Новое имя:")


@router.callback_query(F.data == "pedit:last_name")
async def pedit_last_name(cq: CallbackQuery, state: FSMContext, **_: object) -> None:
    await cq.answer()
    await state.set_state(ProfileEdit.last_name)
    await cq.message.answer("Новая фамилия:")


@router.callback_query(F.data == "pedit:age")
async def pedit_age(cq: CallbackQuery, state: FSMContext, **_: object) -> None:
    await cq.answer()
    await state.set_state(ProfileEdit.age)
    await cq.message.answer("Новый возраст (число от 10 до 100):")


@router.callback_query(F.data == "pedit:direction")
async def pedit_direction(
    cq: CallbackQuery, state: FSMContext, container: Container, **_: object
) -> None:
    await cq.answer()
    session = container.resolve(AsyncSession)
    await ensure_directions_seed(session)
    await session.flush()
    dirs = container.resolve(IDirectionRepository)
    roots = await dirs.list_roots()
    await state.set_state(ProfileEdit.direction_pick)
    await state.update_data(view_parent_id=None, editing_profile=True)
    await cq.message.answer(
        "Выберите направление:", reply_markup=kb.directions_keyboard(roots, show_back=False)
    )


@router.callback_query(F.data == "pedit:user_status")
async def pedit_user_status(cq: CallbackQuery, state: FSMContext, **_: object) -> None:
    await cq.answer()
    await state.set_state(ProfileEdit.user_status)
    await cq.message.answer("Новый статус:", reply_markup=kb.user_status_keyboard())


@router.callback_query(F.data == "pedit:team_mode")
async def pedit_team_mode(cq: CallbackQuery, state: FSMContext, **_: object) -> None:
    await cq.answer()
    await state.set_state(ProfileEdit.team_mode)
    await cq.message.answer("Режим профиля:", reply_markup=kb.team_mode_keyboard())


async def _apply_update_and_show_profile(
    message: Message,
    container: Container,
    user_id: UUID,
    state: FSMContext,
    updates: dict,
    *,
    telegram_actor_id: int,
) -> None:
    if not await _update_profile_or_fail(message, container, user_id, updates):
        return
    await state.clear()
    user = await container.resolve(GetUser).execute(user_id)
    if user is None:
        return
    await _send_profile_card(
        message,
        user,
        container,
        message.bot,
        telegram_actor_id=telegram_actor_id,
        reply_markup=kb.profile_edit_keyboard(),
    )


@router.message(ProfileEdit.first_name, F.text)
async def on_pedit_first_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    await _apply_update_and_show_profile(
        message,
        container,
        user_id,
        state,
        {dk.FIRST_NAME: message.text.strip()},
        telegram_actor_id=message.from_user.id,
    )


@router.message(ProfileEdit.last_name, F.text)
async def on_pedit_last_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    await _apply_update_and_show_profile(
        message,
        container,
        user_id,
        state,
        {dk.LAST_NAME: message.text.strip()},
        telegram_actor_id=message.from_user.id,
    )


@router.message(ProfileEdit.age, F.text)
async def on_pedit_age(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    text = (message.text or "").strip()
    if not text.isdigit() or not (10 <= int(text) <= 100):
        await message.answer("Введите число от 10 до 100.")
        return
    await _apply_update_and_show_profile(
        message,
        container,
        user_id,
        state,
        {dk.AGE: int(text)},
        telegram_actor_id=message.from_user.id,
    )


@router.callback_query(ProfileEdit.direction_pick, F.data == "dir:back")
async def on_pedit_dir_back(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
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
        reply_markup=kb.directions_keyboard(nxt_list, show_back=gp is not None)
    )


@router.callback_query(ProfileEdit.direction_pick, F.data.startswith("dir:"))
async def on_pedit_dir_pick(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None or cq.from_user is None:
        return
    parsed = kb.parse_dir_callback(cq.data or "")
    if not isinstance(parsed, UUID):
        return
    await cq.answer()
    dirs = container.resolve(IDirectionRepository)
    node = await dirs.get_by_id(parsed)
    if node is None:
        return
    children = await dirs.list_children(node.id)
    if children:
        await state.update_data(view_parent_id=node.id)
        await cq.message.edit_reply_markup(
            reply_markup=kb.directions_keyboard(children, show_back=True)
        )
        return
    if node.is_other:
        await state.set_state(ProfileEdit.direction_custom)
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.answer("Опишите направление текстом:")
        return
    await _apply_update_and_show_profile(
        cq.message,
        container,
        user_id,
        state,
        {dk.DIRECTION_ID: str(node.id), dk.CUSTOM_DIRECTION_LABEL: None},
        telegram_actor_id=cq.from_user.id,
    )


@router.message(ProfileEdit.direction_custom, F.text)
async def on_pedit_direction_custom(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    await _apply_update_and_show_profile(
        message,
        container,
        user_id,
        state,
        {dk.CUSTOM_DIRECTION_LABEL: message.text.strip()},
        telegram_actor_id=message.from_user.id,
    )


@router.callback_query(ProfileEdit.user_status, F.data.startswith("st:"))
async def on_pedit_user_status(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None or cq.from_user is None:
        return
    await cq.answer()
    raw = (cq.data or "")[3:]
    try:
        new_status = UserStatus(raw)
    except ValueError:
        return
    if not await _update_profile_or_fail(
        cq.message, container, user_id, {dk.USER_STATUS: raw}
    ):
        return

    tid = cq.from_user.id
    if new_status == UserStatus.SCHOOL:
        await state.set_state(ProfileEdit.school_grade)
        await cq.message.answer("Класс?", reply_markup=kb.school_grade_keyboard())
        return
    if new_status in (UserStatus.STUDENT, UserStatus.MASTER):
        await state.set_state(ProfileEdit.student_course)
        await cq.message.answer("Курс?", reply_markup=kb.student_course_keyboard())
        return

    await state.clear()
    user = await container.resolve(GetUser).execute(user_id)
    if user is None:
        return
    await _send_profile_card(
        cq.message,
        user,
        container,
        cq.bot,
        telegram_actor_id=tid,
        reply_markup=kb.profile_edit_keyboard(),
    )


@router.callback_query(ProfileEdit.school_grade, F.data.startswith("gr:"))
async def on_pedit_school_grade(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    grade = int((cq.data or "").split(":")[1])
    if not await _update_profile_or_fail(
        cq.message, container, user_id, {dk.SCHOOL_GRADE: grade}
    ):
        return
    await state.set_state(ProfileEdit.school_name)
    await cq.message.answer(
        "Школа (необязательно). Напишите название или «-», если не хотите указывать."
    )


@router.message(ProfileEdit.school_name, F.text)
async def on_pedit_school_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    text = message.text.strip()
    val = "" if text == "-" else text
    await _apply_update_and_show_profile(
        message,
        container,
        user_id,
        state,
        {dk.SCHOOL_NAME: val},
        telegram_actor_id=message.from_user.id,
    )


@router.callback_query(ProfileEdit.student_course, F.data.startswith("cr:"))
async def on_pedit_student_course(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    course = int((cq.data or "").split(":")[1])
    if not await _update_profile_or_fail(
        cq.message, container, user_id, {dk.STUDENT_COURSE: course}
    ):
        return
    await state.set_state(ProfileEdit.university)
    await cq.message.answer(
        "ВУЗ (необязательно). Можно пропустить кнопкой или написать «-».",
        reply_markup=kb.university_skip_keyboard(),
    )


@router.callback_query(ProfileEdit.university, F.data == "uni:skip")
async def on_pedit_university_skip(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    if not await _update_profile_or_fail(
        cq.message, container, user_id, {dk.UNIVERSITY: ""}
    ):
        return
    await state.set_state(ProfileEdit.specialty)
    await cq.message.answer("Специальность (обязательно):")


@router.message(ProfileEdit.university, F.text)
async def on_pedit_university_text(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    text = message.text.strip()
    val = "" if text == "-" else text
    if not await _update_profile_or_fail(
        message, container, user_id, {dk.UNIVERSITY: val}
    ):
        return
    await state.set_state(ProfileEdit.specialty)
    await message.answer("Специальность (обязательно):")


@router.message(ProfileEdit.specialty, F.text)
async def on_pedit_specialty(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or message.from_user is None:
        return
    await _apply_update_and_show_profile(
        message,
        container,
        user_id,
        state,
        {dk.SPECIALTY: message.text.strip()},
        telegram_actor_id=message.from_user.id,
    )


@router.callback_query(ProfileEdit.team_mode, F.data.startswith("tm:"))
async def on_pedit_team_mode(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None or cq.from_user is None:
        return
    await cq.answer()
    mode = (cq.data or "").split(":")[1]
    await _apply_update_and_show_profile(
        cq.message,
        container,
        user_id,
        state,
        {dk.TEAM_SEEKING_MODE: mode},
        telegram_actor_id=cq.from_user.id,
    )
