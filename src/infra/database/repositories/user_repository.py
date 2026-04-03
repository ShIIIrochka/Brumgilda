from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.user import User
from src.domain.user.value_objects import SearchFilter, SearchResult
from src.infra.database.models import UserModel


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserModel, user_id)
        if row is None:
            return None
        return _to_entity(row)

    async def save(self, user: User) -> None:
        row = await self._session.get(UserModel, user.id)
        if row is None:
            row = UserModel(id=user.id)
            self._session.add(row)
        _to_row(user, row)
        await self._session.flush()

    async def search(self, fltr: SearchFilter, offset: int, limit: int) -> SearchResult:
        base = select(UserModel).where(
            UserModel.onboarding_completed_at.isnot(None),
            UserModel.id != fltr.exclude_user_id,
            UserModel.team_seeking_mode == fltr.seeking_mode.value,
        )
        if fltr.direction_id is not None:
            base = base.where(UserModel.direction_id == fltr.direction_id)
        if fltr.user_status is not None:
            base = base.where(UserModel.user_status == fltr.user_status.value)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        rows_q = base.order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
        rows = (await self._session.execute(rows_q)).scalars().all()

        return SearchResult(
            users=[_to_entity(r) for r in rows],
            total=total,
            offset=offset,
            limit=limit,
        )


def _to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        onboarding_completed_at=row.onboarding_completed_at,
        onboarding_draft=dict(row.onboarding_draft or {}),
        first_name=row.first_name,
        last_name=row.last_name,
        age=row.age,
        telegram_avatar_file_id=row.telegram_avatar_file_id,
        direction_id=row.direction_id,
        custom_direction_label=row.custom_direction_label,
        user_status=UserStatus(row.user_status) if row.user_status else None,
        school_grade=row.school_grade,
        school_name=row.school_name,
        student_course=row.student_course,
        university=row.university,
        specialty=row.specialty,
        has_olympiad_experience=row.has_olympiad_experience,
        olympiad_description=row.olympiad_description,
        olympiad_links=list(row.olympiad_links or []),
        team_seeking_mode=TeamSeekingMode(row.team_seeking_mode) if row.team_seeking_mode else None,
    )


def _to_row(user: User, row: UserModel) -> None:
    row.onboarding_completed_at = user.onboarding_completed_at
    row.onboarding_draft = user.onboarding_draft
    row.first_name = user.first_name
    row.last_name = user.last_name
    row.age = user.age
    row.telegram_avatar_file_id = user.telegram_avatar_file_id
    row.direction_id = user.direction_id
    row.custom_direction_label = user.custom_direction_label
    row.user_status = user.user_status.value if user.user_status else None
    row.school_grade = user.school_grade
    row.school_name = user.school_name
    row.student_course = user.student_course
    row.university = user.university
    row.specialty = user.specialty
    row.has_olympiad_experience = user.has_olympiad_experience
    row.olympiad_description = user.olympiad_description
    row.olympiad_links = list(user.olympiad_links)
    row.team_seeking_mode = user.team_seeking_mode.value if user.team_seeking_mode else None
