from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from punq import Container

from src.application.usecases.user.complete_onboarding import CompleteOnboarding
from src.application.usecases.user.get_user import GetUser
from src.application.usecases.user.patch_onboarding_draft import PatchOnboardingDraft
from src.domain.directions.repository import IDirectionRepository
from src.domain.user import draft_keys as dk
from src.domain.user.enums import TeamSeekingMode
from src.domain.user.exceptions import DomainValidationError
from src.presentation.bot import keyboards as kb
from src.presentation.bot.avatar_utils import persist_telegram_avatar_file_id
from src.presentation.bot.onboarding_prompts import send_onboarding_prompt
from src.presentation.bot.onboarding_resume import compute_resume_state
from src.presentation.bot.states import Onboarding

router = Router(name="onboarding")

_OLYMPIAD_NO_WELCOME = "Понятно, без олимпиадного опыта — тоже отличный старт. Продолжим настройку профиля."


async def _patch(c: Container, user_id: UUID, patch: dict) -> None:
    await c.resolve(PatchOnboardingDraft).execute(user_id, patch)


async def _advance(
    target: Message,
    state: FSMContext,
    container: Container,
    user_id: UUID,
) -> None:
    gu = container.resolve(GetUser)
    user = await gu.execute(user_id)
    if user is None:
        await target.answer("Ошибка: пользователь не найден.")
        return
    dirs = container.resolve(IDirectionRepository)
    nxt = await compute_resume_state(user, dirs)
    if nxt is None:
        await state.set_state(None)
        await target.answer(
            "Черновик регистрации выглядит полным. Нажмите «Завершить регистрацию».",
            reply_markup=kb.finish_keyboard(),
        )
        return
    await state.set_state(nxt)
    await send_onboarding_prompt(nxt, target, state, container, user_id)


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await state.clear()
    gu = container.resolve(GetUser)
    user = await gu.execute(user_id)
    if user is None:
        await message.answer("Не удалось загрузить профиль.")
        return
    if user.is_onboarding_complete:
        await message.answer(
            f"С возвращением, {user.first_name}! Профиль заполнен.\n"
            "/profile — посмотреть и отредактировать профиль\n"
            "/search — найти сокомандника"
        )
        return
    dirs = container.resolve(IDirectionRepository)
    nxt = await compute_resume_state(user, dirs)
    if nxt is None:
        await message.answer(
            "Черновик регистрации выглядит полным. Нажмите «Завершить регистрацию».",
            reply_markup=kb.finish_keyboard(),
        )
        return
    await state.set_state(nxt)
    await send_onboarding_prompt(nxt, message, state, container, user_id)


@router.callback_query(F.data == "onb:finish")
async def on_finish_registration(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None or cq.from_user is None:
        return
    await cq.answer()
    try:
        await container.resolve(CompleteOnboarding).execute(user_id)
    except DomainValidationError as e:
        await cq.message.answer(f"Проверьте данные: {e}")
        return
    await persist_telegram_avatar_file_id(cq.bot, container, user_id, cq.from_user.id)
    await state.clear()
    await cq.message.answer("Регистрация завершена. Удачи в поиске команды!")


@router.message(Onboarding.first_name, F.text)
async def on_first_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _patch(container, user_id, {dk.FIRST_NAME: message.text.strip()})
    await _advance(message, state, container, user_id)


@router.message(Onboarding.last_name, F.text)
async def on_last_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _patch(container, user_id, {dk.LAST_NAME: message.text.strip()})
    await _advance(message, state, container, user_id)


@router.message(Onboarding.age, F.text)
async def on_age(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    text = (message.text or "").strip()
    if not text.isdigit() or not (10 <= int(text) <= 100):
        await message.answer("Введите число от 10 до 100.")
        return
    await _patch(container, user_id, {dk.AGE: int(text)})
    await _advance(message, state, container, user_id)


@router.callback_query(Onboarding.direction_pick, F.data == "dir:back")
async def on_dir_back(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    data = await state.get_data()
    vp: UUID | None = data.get("view_parent_id")
    if vp is None:
        return
    dirs = container.resolve(IDirectionRepository)
    node = await dirs.get_by_id(vp)
    gp = node.parent_id if node else None
    nxt_list = (
        await dirs.list_children(gp) if gp is not None else await dirs.list_roots()
    )
    await state.update_data(view_parent_id=gp)
    await cq.message.edit_reply_markup(
        reply_markup=kb.directions_keyboard(nxt_list, show_back=gp is not None)
    )


@router.callback_query(Onboarding.direction_pick, F.data.startswith("dir:"))
async def on_dir_pick(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
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
            reply_markup=kb.directions_keyboard(children, show_back=True),
        )
        return
    if node.is_other:
        await _patch(container, user_id, {dk.DIRECTION_ID: str(node.id)})
        await state.set_state(Onboarding.direction_custom)
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.answer("Опишите направление текстом:")
        return
    await _patch(container, user_id, {dk.DIRECTION_ID: str(node.id)})
    await cq.message.edit_reply_markup(reply_markup=None)
    await _advance(cq.message, state, container, user_id)


@router.message(Onboarding.direction_custom, F.text)
async def on_direction_custom(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _patch(container, user_id, {dk.CUSTOM_DIRECTION_LABEL: message.text.strip()})
    await _advance(message, state, container, user_id)


@router.callback_query(Onboarding.user_status, F.data.startswith("st:"))
async def on_user_status(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    raw = (cq.data or "")[3:]
    await _patch(container, user_id, {dk.USER_STATUS: raw})
    await _advance(cq.message, state, container, user_id)


@router.callback_query(Onboarding.school_grade, F.data.startswith("gr:"))
async def on_school_grade(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    grade = int((cq.data or "").split(":")[1])
    await _patch(container, user_id, {dk.SCHOOL_GRADE: grade})
    await _advance(cq.message, state, container, user_id)


@router.message(Onboarding.school_name, F.text)
async def on_school_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    text = message.text.strip()
    val = "" if text == "-" else text
    await _patch(container, user_id, {dk.SCHOOL_NAME: val})
    await _advance(message, state, container, user_id)


@router.callback_query(Onboarding.student_course, F.data.startswith("cr:"))
async def on_student_course(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    course = int((cq.data or "").split(":")[1])
    await _patch(container, user_id, {dk.STUDENT_COURSE: course})
    await _advance(cq.message, state, container, user_id)


@router.callback_query(Onboarding.university, F.data == "uni:skip")
async def on_university_skip(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    await _patch(container, user_id, {dk.UNIVERSITY: ""})
    await _advance(cq.message, state, container, user_id)


@router.message(Onboarding.university, F.text)
async def on_university_text(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    text = message.text.strip()
    val = "" if text == "-" else text
    await _patch(container, user_id, {dk.UNIVERSITY: val})
    await _advance(message, state, container, user_id)


@router.message(Onboarding.specialty, F.text)
async def on_specialty(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _patch(container, user_id, {dk.SPECIALTY: message.text.strip()})
    await _advance(message, state, container, user_id)


@router.callback_query(
    Onboarding.olympiad_gate,
    F.data.in_({"oly:yes", "oly:no"}),
)
async def on_olympiad_gate(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    if cq.data == "oly:yes":
        await _patch(container, user_id, {dk.HAS_OLYMPIAD_EXPERIENCE: True})
        await state.set_state(Onboarding.olympiad_desc)
        await cq.message.answer("Кратко опишите достижения:")
    else:
        await _patch(
            container,
            user_id,
            {
                dk.HAS_OLYMPIAD_EXPERIENCE: False,
                dk.OLYMPIAD_DESCRIPTION: None,
                dk.OLYMPIAD_LINKS: None,
            },
        )
        await cq.message.answer(_OLYMPIAD_NO_WELCOME)
        await _advance(cq.message, state, container, user_id)


@router.message(Onboarding.olympiad_desc, F.text)
async def on_olympiad_desc(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _patch(container, user_id, {dk.OLYMPIAD_DESCRIPTION: message.text.strip()})
    await state.set_state(Onboarding.olympiad_links)
    await message.answer("Ссылки (каждая с новой строки):")


@router.message(Onboarding.olympiad_links, F.text)
async def on_olympiad_links(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    lines = [ln.strip() for ln in message.text.splitlines() if ln.strip()]
    await _patch(container, user_id, {dk.OLYMPIAD_LINKS: lines})
    await _advance(message, state, container, user_id)


@router.callback_query(Onboarding.team_mode, F.data.startswith("tm:"))
async def on_team_mode(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    mode = (cq.data or "").split(":")[1]
    TeamSeekingMode(mode)
    await _patch(container, user_id, {dk.TEAM_SEEKING_MODE: mode})
    await _advance(cq.message, state, container, user_id)
