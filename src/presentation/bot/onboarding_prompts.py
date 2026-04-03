from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message
from punq import Container
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.directions.repository import IDirectionRepository
from src.infra.database.directions_seed import ensure_directions_seed
from src.presentation.bot import keyboards as kb
from src.presentation.bot.states import Onboarding

logger = logging.getLogger(__name__)

PromptSender = Callable[[Message, FSMContext, Container, UUID], Awaitable[None]]


async def _p_first_name(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Как вас зовут? (имя)")


async def _p_last_name(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Фамилия?")


async def _p_age(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Сколько тебе лет? (число от 10 до 100)")


async def _p_direction_pick(
    target: Message, state: FSMContext, c: Container, _uid: UUID
) -> None:
    session = c.resolve(AsyncSession)
    await ensure_directions_seed(session)
    await session.flush()

    dirs = c.resolve(IDirectionRepository)
    roots = await dirs.list_roots()
    await state.update_data(view_parent_id=None)

    if not roots:
        logger.error(
            "Таблица directions пуста после сида — проверьте БД и миграции (alembic upgrade head)."
        )
        await target.answer(
            "Список направлений временно недоступен. Попробуйте позже или напишите /start ещё раз. "
            "Если вы администратор: выполните миграции и убедитесь, что в таблице directions есть записи."
        )
        return

    await target.answer(
        "Выберите направление — кнопки отображаются прямо под этим сообщением (не в поле ввода).",
        reply_markup=kb.directions_keyboard(roots, show_back=False),
    )


async def _p_direction_custom(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Опишите направление текстом:")


async def _p_user_status(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Ваш статус?", reply_markup=kb.user_status_keyboard())


async def _p_school_grade(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Класс?", reply_markup=kb.school_grade_keyboard())


async def _p_school_name(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer(
        "Школа (необязательно). Напишите название или «-», если не хотите указывать."
    )


async def _p_student_course(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Курс?", reply_markup=kb.student_course_keyboard())


async def _p_university(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer(
        "ВУЗ (необязательно). Можно пропустить кнопкой или написать «-».",
        reply_markup=kb.university_skip_keyboard(),
    )


async def _p_specialty(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Специальность (обязательно):")


async def _p_olympiad_gate(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer(
        "Были ли олимпиадные достижения?",
        reply_markup=kb.olympiad_keyboard(),
    )


async def _p_olympiad_desc(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Кратко опишите достижения:")


async def _p_olympiad_links(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Ссылки (каждая с новой строки):")


async def _p_team_mode(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Режим профиля:", reply_markup=kb.team_mode_keyboard())


def _state_key(st: State) -> str:
    return st.state


ONBOARDING_PROMPTS: dict[str, PromptSender] = {
    _state_key(Onboarding.first_name): _p_first_name,
    _state_key(Onboarding.last_name): _p_last_name,
    _state_key(Onboarding.age): _p_age,
    _state_key(Onboarding.direction_pick): _p_direction_pick,
    _state_key(Onboarding.direction_custom): _p_direction_custom,
    _state_key(Onboarding.user_status): _p_user_status,
    _state_key(Onboarding.school_grade): _p_school_grade,
    _state_key(Onboarding.school_name): _p_school_name,
    _state_key(Onboarding.student_course): _p_student_course,
    _state_key(Onboarding.university): _p_university,
    _state_key(Onboarding.specialty): _p_specialty,
    _state_key(Onboarding.olympiad_gate): _p_olympiad_gate,
    _state_key(Onboarding.olympiad_desc): _p_olympiad_desc,
    _state_key(Onboarding.olympiad_links): _p_olympiad_links,
    _state_key(Onboarding.team_mode): _p_team_mode,
}


async def send_onboarding_prompt(
    st: State,
    target: Message,
    fsm: FSMContext,
    container: Container,
    user_id: UUID,
) -> None:
    sender = ONBOARDING_PROMPTS.get(st.state)
    if sender is None:
        raise KeyError(f"No onboarding prompt registered for state {st.state!r}")
    await sender(target, fsm, container, user_id)
