from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.domain.user import draft_keys as dk
from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.exceptions import DomainValidationError


class User:
    def __init__(
        self,
        id: UUID,
        *,
        onboarding_completed_at: datetime | None = None,
        onboarding_draft: dict[str, Any] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        direction_id: UUID | None = None,
        custom_direction_label: str | None = None,
        user_status: UserStatus | None = None,
        school_grade: int | None = None,
        school_name: str | None = None,
        student_course: int | None = None,
        university: str | None = None,
        specialty: str | None = None,
        has_olympiad_experience: bool = False,
        olympiad_description: str | None = None,
        olympiad_links: list[str] | None = None,
        team_seeking_mode: TeamSeekingMode | None = None,
        age: int | None = None,
        telegram_avatar_file_id: str | None = None,
        telegram_username: str | None = None,
    ) -> None:
        self.id = id
        self.onboarding_completed_at = onboarding_completed_at
        self.onboarding_draft = onboarding_draft if onboarding_draft is not None else {}
        self.first_name = first_name
        self.last_name = last_name
        self.direction_id = direction_id
        self.custom_direction_label = custom_direction_label
        self.user_status = user_status
        self.school_grade = school_grade
        self.school_name = school_name
        self.student_course = student_course
        self.university = university
        self.specialty = specialty
        self.has_olympiad_experience = has_olympiad_experience
        self.olympiad_description = olympiad_description
        self.olympiad_links = olympiad_links if olympiad_links is not None else []
        self.team_seeking_mode = team_seeking_mode
        self.age = age
        self.telegram_avatar_file_id = telegram_avatar_file_id
        self.telegram_username = telegram_username

    @classmethod
    def create_new(cls) -> User:
        return cls(id=uuid.uuid4())

    @property
    def is_onboarding_complete(self) -> bool:
        return self.onboarding_completed_at is not None

    def merge_draft(self, patch: dict[str, Any]) -> None:
        if self.is_onboarding_complete:
            raise DomainValidationError("Onboarding already completed")
        merged = deepcopy(self.onboarding_draft)
        for k, v in patch.items():
            if v is None:
                merged.pop(k, None)
            else:
                merged[k] = v
        self.onboarding_draft = merged

    def _draft_or_profile(self) -> dict[str, Any]:
        if self.is_onboarding_complete:
            return {
                dk.FIRST_NAME: self.first_name,
                dk.LAST_NAME: self.last_name,
                dk.AGE: self.age,
                dk.DIRECTION_ID: str(self.direction_id) if self.direction_id else None,
                dk.CUSTOM_DIRECTION_LABEL: self.custom_direction_label,
                dk.USER_STATUS: self.user_status.value if self.user_status else None,
                dk.SCHOOL_GRADE: self.school_grade,
                dk.SCHOOL_NAME: self.school_name,
                dk.STUDENT_COURSE: self.student_course,
                dk.UNIVERSITY: self.university,
                dk.SPECIALTY: self.specialty,
                dk.HAS_OLYMPIAD_EXPERIENCE: self.has_olympiad_experience,
                dk.OLYMPIAD_DESCRIPTION: self.olympiad_description,
                dk.OLYMPIAD_LINKS: list(self.olympiad_links),
                dk.TEAM_SEEKING_MODE: self.team_seeking_mode.value if self.team_seeking_mode else None,
            }
        return deepcopy(self.onboarding_draft)

    def validate_complete(self) -> None:
        d = self._draft_or_profile()
        errors: list[str] = []

        def req(key: str) -> Any:
            val = d.get(key)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(key)
            return val

        req(dk.FIRST_NAME)
        req(dk.LAST_NAME)
        age_val = d.get(dk.AGE)
        if age_val is None:
            errors.append(dk.AGE)
        elif not isinstance(age_val, int) or not (10 <= age_val <= 100):
            errors.append(dk.AGE)
        dir_id = d.get(dk.DIRECTION_ID)
        custom = d.get(dk.CUSTOM_DIRECTION_LABEL)
        if not dir_id and not (custom and str(custom).strip()):
            errors.append("direction")
        status_raw = d.get(dk.USER_STATUS)
        if not status_raw:
            errors.append(dk.USER_STATUS)
        else:
            try:
                status = UserStatus(str(status_raw))
            except ValueError:
                errors.append(dk.USER_STATUS)
                status = None
            if status is not None:
                if status == UserStatus.SCHOOL:
                    if d.get(dk.SCHOOL_GRADE) is None:
                        errors.append(dk.SCHOOL_GRADE)
                elif status in (UserStatus.STUDENT, UserStatus.MASTER):
                    if d.get(dk.STUDENT_COURSE) is None:
                        errors.append(dk.STUDENT_COURSE)
                    spec = d.get(dk.SPECIALTY)
                    if spec is None or (isinstance(spec, str) and not spec.strip()):
                        errors.append(dk.SPECIALTY)

        has_ol = d.get(dk.HAS_OLYMPIAD_EXPERIENCE)
        if has_ol is True:
            desc = d.get(dk.OLYMPIAD_DESCRIPTION)
            if desc is None or (isinstance(desc, str) and not desc.strip()):
                errors.append(dk.OLYMPIAD_DESCRIPTION)
            links = d.get(dk.OLYMPIAD_LINKS) or []
            if not isinstance(links, list) or not any(
                isinstance(x, str) and x.strip() for x in links
            ):
                errors.append(dk.OLYMPIAD_LINKS)

        mode_raw = d.get(dk.TEAM_SEEKING_MODE)
        if not mode_raw:
            errors.append(dk.TEAM_SEEKING_MODE)
        else:
            try:
                TeamSeekingMode(str(mode_raw))
            except ValueError:
                errors.append(dk.TEAM_SEEKING_MODE)

        if errors:
            raise DomainValidationError(f"Invalid onboarding: {', '.join(sorted(set(errors)))}")

    def complete_onboarding(self) -> None:
        if self.is_onboarding_complete:
            raise DomainValidationError("Onboarding already completed")
        self.validate_complete()
        d = self.onboarding_draft

        self.first_name = str(d[dk.FIRST_NAME]).strip()
        self.last_name = str(d[dk.LAST_NAME]).strip()
        self.age = int(d[dk.AGE])
        raw_dir = d.get(dk.DIRECTION_ID)
        self.direction_id = UUID(str(raw_dir)) if raw_dir else None
        cdl = d.get(dk.CUSTOM_DIRECTION_LABEL)
        self.custom_direction_label = str(cdl).strip() if cdl else None
        self.user_status = UserStatus(str(d[dk.USER_STATUS]))
        self.school_grade = d.get(dk.SCHOOL_GRADE)
        sn = d.get(dk.SCHOOL_NAME)
        self.school_name = str(sn).strip() if sn else None
        self.student_course = d.get(dk.STUDENT_COURSE)
        uni = d.get(dk.UNIVERSITY)
        self.university = str(uni).strip() if uni else None
        sp = d.get(dk.SPECIALTY)
        self.specialty = str(sp).strip() if sp else None
        self.has_olympiad_experience = bool(d.get(dk.HAS_OLYMPIAD_EXPERIENCE))
        od = d.get(dk.OLYMPIAD_DESCRIPTION)
        self.olympiad_description = str(od).strip() if od else None
        raw_links = d.get(dk.OLYMPIAD_LINKS) or []
        self.olympiad_links = [str(x).strip() for x in raw_links if isinstance(x, str) and x.strip()]
        self.team_seeking_mode = TeamSeekingMode(str(d[dk.TEAM_SEEKING_MODE]))

        self.onboarding_completed_at = datetime.now(tz=UTC)
        self.onboarding_draft = {}

    def _clear_education_fields_for_status(self, status: UserStatus) -> None:
        """Сбрасывает поля, не относящиеся к выбранному статусу (смена школа↔вуз)."""
        if status == UserStatus.SCHOOL:
            self.student_course = None
            self.university = None
            self.specialty = None
        elif status in (UserStatus.STUDENT, UserStatus.MASTER):
            self.school_grade = None
            self.school_name = None
        elif status == UserStatus.NOT_STUDYING:
            self.school_grade = None
            self.school_name = None
            self.student_course = None
            self.university = None
            self.specialty = None

    def update_profile(self, updates: dict[str, Any]) -> None:
        if not self.is_onboarding_complete:
            raise DomainValidationError("Cannot update profile before onboarding is complete")
        for key, value in updates.items():
            if key == dk.FIRST_NAME:
                if not value or not str(value).strip():
                    raise DomainValidationError("first_name is required")
                self.first_name = str(value).strip()
            elif key == dk.LAST_NAME:
                if not value or not str(value).strip():
                    raise DomainValidationError("last_name is required")
                self.last_name = str(value).strip()
            elif key == dk.AGE:
                if not isinstance(value, int) or not (10 <= value <= 100):
                    raise DomainValidationError("age must be between 10 and 100")
                self.age = value
            elif key == dk.DIRECTION_ID:
                self.direction_id = UUID(str(value)) if value else None
            elif key == dk.CUSTOM_DIRECTION_LABEL:
                self.custom_direction_label = str(value).strip() if value else None
            elif key == dk.USER_STATUS:
                self.user_status = UserStatus(str(value))
                self._clear_education_fields_for_status(self.user_status)
            elif key == dk.TEAM_SEEKING_MODE:
                self.team_seeking_mode = TeamSeekingMode(str(value))
            elif key == dk.SCHOOL_GRADE:
                self.school_grade = int(value) if value is not None else None
            elif key == dk.SCHOOL_NAME:
                self.school_name = str(value).strip() if value else None
            elif key == dk.STUDENT_COURSE:
                self.student_course = int(value) if value is not None else None
            elif key == dk.UNIVERSITY:
                self.university = str(value).strip() if value else None
            elif key == dk.SPECIALTY:
                self.specialty = str(value).strip() if value else None
            elif key == dk.TELEGRAM_AVATAR_FILE_ID:
                self.telegram_avatar_file_id = str(value) if value else None
            elif key == dk.AVATAR_URL:
                self.avatar_url = str(value).strip() if value else None
