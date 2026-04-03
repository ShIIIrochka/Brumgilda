from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from aiogram.fsm.state import State

from src.domain.directions.repository import IDirectionRepository
from src.domain.user import draft_keys as dk
from src.domain.user.enums import UserStatus
from src.domain.user.user import User
from src.presentation.bot.states import Onboarding

ResumeStep = Callable[[User, dict, IDirectionRepository], Awaitable[State | None]]


async def _need_first_name(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.first_name if not d.get(dk.FIRST_NAME) else None


async def _need_last_name(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.last_name if not d.get(dk.LAST_NAME) else None


async def _need_age(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.age if d.get(dk.AGE) is None else None


async def _need_direction(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.direction_pick if not d.get(dk.DIRECTION_ID) else None


async def _need_custom_direction(
    _user: User, d: dict, dirs: IDirectionRepository
) -> State | None:
    raw = d.get(dk.DIRECTION_ID)
    if not raw:
        return None
    sub = await dirs.get_by_id(UUID(str(raw)))
    if sub and sub.is_other and not (d.get(dk.CUSTOM_DIRECTION_LABEL) or "").strip():
        return Onboarding.direction_custom
    return None


async def _need_user_status(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.user_status if not d.get(dk.USER_STATUS) else None


async def _need_school_fields(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    if UserStatus(str(d[dk.USER_STATUS])) != UserStatus.SCHOOL:
        return None
    if d.get(dk.SCHOOL_GRADE) is None:
        return Onboarding.school_grade
    if dk.SCHOOL_NAME not in d:
        return Onboarding.school_name
    return None


async def _need_student_fields(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    st = UserStatus(str(d[dk.USER_STATUS]))
    if st not in (UserStatus.STUDENT, UserStatus.MASTER):
        return None
    if d.get(dk.STUDENT_COURSE) is None:
        return Onboarding.student_course
    if dk.UNIVERSITY not in d:
        return Onboarding.university
    if not (d.get(dk.SPECIALTY) or "").strip():
        return Onboarding.specialty
    return None


async def _need_olympiad_gate(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.olympiad_gate if dk.HAS_OLYMPIAD_EXPERIENCE not in d else None


async def _need_olympiad_details(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    if d.get(dk.HAS_OLYMPIAD_EXPERIENCE) is not True:
        return None
    if not (d.get(dk.OLYMPIAD_DESCRIPTION) or "").strip():
        return Onboarding.olympiad_desc
    links = d.get(dk.OLYMPIAD_LINKS) or []
    if not isinstance(links, list) or not any(
        isinstance(x, str) and x.strip() for x in links
    ):
        return Onboarding.olympiad_links
    return None


async def _need_team_mode(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.team_mode if not d.get(dk.TEAM_SEEKING_MODE) else None


RESUME_PIPELINE: tuple[ResumeStep, ...] = (
    _need_first_name,
    _need_last_name,
    _need_age,
    _need_direction,
    _need_custom_direction,
    _need_user_status,
    _need_school_fields,
    _need_student_fields,
    _need_olympiad_gate,
    _need_olympiad_details,
    _need_team_mode,
)


async def compute_resume_state(user: User, dirs: IDirectionRepository) -> State | None:
    if user.is_onboarding_complete:
        return None
    draft = user.onboarding_draft
    for step in RESUME_PIPELINE:
        nxt = await step(user, draft, dirs)
        if nxt is not None:
            return nxt
    return None
