# FindTeam: Profile + Search + Age + Avatar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add age field to onboarding, profile viewing/editing with Telegram avatars, and teammate search with filters and pagination cards.

**Architecture:** Extend existing DDD + Clean Architecture + punq DI. New features follow the same layered pattern: domain entities/value objects -> use cases -> infrastructure repos -> presentation handlers. Profile and Search are separate routers in the presentation layer.

**Tech Stack:** Python 3.13, aiogram 3, SQLAlchemy 2 (async), PostgreSQL, Alembic, punq

**Parallelization:** Tasks 1-2 are sequential (domain then infra). Tasks 3 and 4 are **independent and can run in parallel** (profile feature and search feature). Task 5 wires everything together.

---

### Task 1: Domain Layer Changes

**Files:**
- Modify: `src/domain/user/user.py`
- Modify: `src/domain/user/draft_keys.py`
- Modify: `src/domain/user/repositories.py`
- Create: `src/domain/user/value_objects.py`

- [ ] **Step 1: Add AGE draft key**

In `src/domain/user/draft_keys.py`, add at the end:

```python
AGE = "age"
```

- [ ] **Step 2: Add age and telegram_avatar_file_id to User aggregate**

In `src/domain/user/user.py`, update `__init__` to add two new parameters after `team_seeking_mode`:

```python
        age: int | None = None,
        telegram_avatar_file_id: str | None = None,
```

And set them:

```python
        self.age = age
        self.telegram_avatar_file_id = telegram_avatar_file_id
```

- [ ] **Step 3: Update `_draft_or_profile` to include age**

In `src/domain/user/user.py`, inside the `_draft_or_profile` method, add `dk.AGE: self.age,` after the `dk.LAST_NAME` line in the `is_onboarding_complete` branch.

- [ ] **Step 4: Update `validate_complete` to require age**

In `src/domain/user/user.py`, inside `validate_complete`, after `req(dk.LAST_NAME)` add:

```python
        age_val = d.get(dk.AGE)
        if age_val is None:
            errors.append(dk.AGE)
        elif not isinstance(age_val, int) or not (10 <= age_val <= 100):
            errors.append(dk.AGE)
```

- [ ] **Step 5: Update `complete_onboarding` to set age**

In `src/domain/user/user.py`, inside `complete_onboarding`, after `self.last_name = str(d[dk.LAST_NAME]).strip()` add:

```python
        self.age = int(d[dk.AGE])
```

- [ ] **Step 6: Add `update_profile` method to User**

In `src/domain/user/user.py`, add after `complete_onboarding`:

```python
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
```

- [ ] **Step 7: Create SearchFilter and SearchResult value objects**

Create `src/domain/user/value_objects.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.user import User


@dataclass(frozen=True, slots=True)
class SearchFilter:
    direction_id: UUID | None
    user_status: UserStatus | None
    exclude_user_id: UUID
    seeking_mode: TeamSeekingMode


@dataclass(frozen=True, slots=True)
class SearchResult:
    users: list[User]
    total: int
    offset: int
    limit: int
```

- [ ] **Step 8: Add search method to IUserRepository protocol**

In `src/domain/user/repositories.py`, add import at top:

```python
from src.domain.user.value_objects import SearchFilter, SearchResult
```

Add method to `IUserRepository`:

```python
    async def search(self, fltr: SearchFilter, offset: int, limit: int) -> SearchResult: ...
```

- [ ] **Step 9: Commit**

```bash
git add src/domain/user/user.py src/domain/user/draft_keys.py src/domain/user/repositories.py src/domain/user/value_objects.py
git commit -m "feat(domain): add age, avatar, update_profile, search filter/result"
```

---

### Task 2: Infrastructure Layer (Models, Repositories, Migration, DI)

**Files:**
- Modify: `src/infra/database/models.py`
- Modify: `src/infra/database/repositories/user_repository.py`
- Modify: `src/infra/di.py`
- Create: `src/application/usecases/user/update_user_profile.py`
- Create: `src/application/usecases/user/search_users.py`
- Create: `alembic/versions/xxxx_add_age_and_avatar.py`

- [ ] **Step 1: Add age and telegram_avatar_file_id to UserModel**

In `src/infra/database/models.py`, add after `last_name` column:

```python
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

Add after `team_seeking_mode` column:

```python
    telegram_avatar_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

- [ ] **Step 2: Update `_to_entity` and `_to_row` in user_repository.py**

In `src/infra/database/repositories/user_repository.py`, update `_to_entity` to include:

```python
        age=row.age,
        telegram_avatar_file_id=row.telegram_avatar_file_id,
```

(Add after `last_name=row.last_name,`)

Update `_to_row` to include:

```python
    row.age = user.age
    row.telegram_avatar_file_id = user.telegram_avatar_file_id
```

(Add after `row.last_name = user.last_name`)

- [ ] **Step 3: Implement search method in SqlAlchemyUserRepository**

In `src/infra/database/repositories/user_repository.py`, add imports at top:

```python
from sqlalchemy import func, select

from src.domain.user.value_objects import SearchFilter, SearchResult
```

Add method to `SqlAlchemyUserRepository`:

```python
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
```

- [ ] **Step 4: Create UpdateUserProfile use case**

Create `src/application/usecases/user/update_user_profile.py`:

```python
from __future__ import annotations

from typing import Any
from uuid import UUID

from src.application.common.exceptions import UserNotFoundError
from src.domain.user.repositories import IUserRepository


class UpdateUserProfile:
    def __init__(self, users: IUserRepository) -> None:
        self._users = users

    async def execute(self, user_id: UUID, updates: dict[str, Any]) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        user.update_profile(updates)
        await self._users.save(user)
```

- [ ] **Step 5: Create SearchUsers use case**

Create `src/application/usecases/user/search_users.py`:

```python
from __future__ import annotations

from src.domain.user.repositories import IUserRepository
from src.domain.user.value_objects import SearchFilter, SearchResult


class SearchUsers:
    def __init__(self, users: IUserRepository) -> None:
        self._users = users

    async def execute(self, fltr: SearchFilter, offset: int = 0, limit: int = 1) -> SearchResult:
        return await self._users.search(fltr, offset, limit)
```

- [ ] **Step 6: Register new use cases in DI container**

In `src/infra/di.py`, add imports:

```python
from src.application.usecases.user.update_user_profile import UpdateUserProfile
from src.application.usecases.user.search_users import SearchUsers
```

Add registrations before `return container`:

```python
    container.register(UpdateUserProfile)
    container.register(SearchUsers)
```

- [ ] **Step 7: Create Alembic migration**

Create `alembic/versions/0002_add_age_and_avatar.py`:

```python
"""Add age and telegram_avatar_file_id columns

Revision ID: 0002_age_avatar
Revises: 5e150362c97d
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_age_avatar"
down_revision: Union[str, Sequence[str], None] = "5e150362c97d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("telegram_avatar_file_id", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_avatar_file_id")
    op.drop_column("users", "age")
```

- [ ] **Step 8: Commit**

```bash
git add src/infra/database/models.py src/infra/database/repositories/user_repository.py src/infra/di.py src/application/usecases/user/update_user_profile.py src/application/usecases/user/search_users.py alembic/versions/0002_add_age_and_avatar.py
git commit -m "feat(infra): add age/avatar columns, search repo, new use cases"
```

---

### Task 3: Profile Feature (handlers, keyboards, states, onboarding age)

> **Can run in parallel with Task 4** after Tasks 1-2 are done.

**Files:**
- Modify: `src/presentation/bot/states.py`
- Modify: `src/presentation/bot/keyboards.py`
- Modify: `src/presentation/bot/onboarding_handlers.py`
- Modify: `src/presentation/bot/onboarding_prompts.py`
- Modify: `src/presentation/bot/onboarding_resume.py`
- Create: `src/presentation/bot/profile_handlers.py`

- [ ] **Step 1: Add FSM states for ProfileEdit and age onboarding**

Replace `src/presentation/bot/states.py` entirely:

```python
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    first_name = State()
    last_name = State()
    age = State()
    direction_pick = State()
    direction_custom = State()
    user_status = State()
    school_grade = State()
    school_name = State()
    student_course = State()
    university = State()
    specialty = State()
    olympiad_gate = State()
    olympiad_desc = State()
    olympiad_links = State()
    team_mode = State()


class ProfileEdit(StatesGroup):
    first_name = State()
    last_name = State()
    age = State()
    direction_pick = State()
    direction_custom = State()
    user_status = State()
    school_grade = State()
    school_name = State()
    student_course = State()
    university = State()
    specialty = State()
    team_mode = State()
```

- [ ] **Step 2: Add age onboarding resume step**

In `src/presentation/bot/onboarding_resume.py`, add after `_need_last_name`:

```python
async def _need_age(
    _user: User, d: dict, _dirs: IDirectionRepository
) -> State | None:
    return Onboarding.age if d.get(dk.AGE) is None else None
```

Add `dk` import if not already there (it's imported via `from src.domain.user import draft_keys as dk`).

Update `RESUME_PIPELINE` to insert `_need_age` after `_need_last_name`:

```python
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
```

- [ ] **Step 3: Add age prompt to onboarding_prompts.py**

In `src/presentation/bot/onboarding_prompts.py`, add after `_p_last_name`:

```python
async def _p_age(
    target: Message, _state: FSMContext, _c: Container, _uid: UUID
) -> None:
    await target.answer("Сколько тебе лет? (число от 10 до 100)")
```

Add to `ONBOARDING_PROMPTS` dict after the last_name entry:

```python
    _state_key(Onboarding.age): _p_age,
```

- [ ] **Step 4: Add age handler to onboarding_handlers.py**

In `src/presentation/bot/onboarding_handlers.py`, add after `on_last_name`:

```python
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
```

Also add `dk.AGE` is already available via `from src.domain.user import draft_keys as dk`.

- [ ] **Step 5: Add profile keyboards**

In `src/presentation/bot/keyboards.py`, add at the end:

```python
def profile_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Имя", callback_data="pedit:first_name"),
                InlineKeyboardButton(text="Фамилия", callback_data="pedit:last_name"),
                InlineKeyboardButton(text="Возраст", callback_data="pedit:age"),
            ],
            [
                InlineKeyboardButton(text="Направление", callback_data="pedit:direction"),
                InlineKeyboardButton(text="Статус", callback_data="pedit:user_status"),
            ],
            [
                InlineKeyboardButton(text="Режим поиска", callback_data="pedit:team_mode"),
            ],
        ]
    )
```

- [ ] **Step 6: Create profile_handlers.py**

Create `src/presentation/bot/profile_handlers.py`:

```python
from __future__ import annotations

import os
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    Message,
)
from punq import Container

from src.application.usecases.user.get_user import GetUser
from src.application.usecases.user.update_user_profile import UpdateUserProfile
from src.domain.directions.repository import IDirectionRepository
from src.domain.user import draft_keys as dk
from src.domain.user.enums import TeamSeekingMode, UserStatus
from src.domain.user.exceptions import DomainValidationError
from src.domain.user.user import User
from src.presentation.bot import keyboards as kb
from src.presentation.bot.states import ProfileEdit

router = Router(name="profile")

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


def _build_profile_caption(user: User, direction_name: str | None) -> str:
    lines: list[str] = []
    lines.append(f"{user.first_name} {user.last_name}, {user.age} лет")
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


async def _get_avatar_photo(
    user: User, bot, telegram_user_id: int
) -> FSInputFile | BufferedInputFile | str:
    try:
        photos = await bot.get_user_profile_photos(telegram_user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            return file_id
    except Exception:
        pass
    return FSInputFile(_DEFAULT_AVATAR)


async def _send_profile_card(
    target: Message,
    user: User,
    container: Container,
    bot,
    telegram_user_id: int,
    reply_markup=None,
) -> None:
    dirs = container.resolve(IDirectionRepository)
    direction_name = None
    if user.direction_id:
        d = await dirs.get_by_id(user.direction_id)
        if d:
            direction_name = d.name
    caption = _build_profile_caption(user, direction_name)
    photo = await _get_avatar_photo(user, bot, telegram_user_id)
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
        message, user, container, message.bot,
        message.from_user.id,
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
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.infra.database.directions_seed import ensure_directions_seed

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
) -> None:
    try:
        await container.resolve(UpdateUserProfile).execute(user_id, updates)
    except DomainValidationError as e:
        await message.answer(f"Ошибка: {e}")
        return
    await state.clear()
    user = await container.resolve(GetUser).execute(user_id)
    if user is None:
        return
    await _send_profile_card(
        message, user, container, message.bot,
        message.from_user.id,
        reply_markup=kb.profile_edit_keyboard(),
    )


@router.message(ProfileEdit.first_name, F.text)
async def on_pedit_first_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _apply_update_and_show_profile(
        message, container, user_id, state, {dk.FIRST_NAME: message.text.strip()}
    )


@router.message(ProfileEdit.last_name, F.text)
async def on_pedit_last_name(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _apply_update_and_show_profile(
        message, container, user_id, state, {dk.LAST_NAME: message.text.strip()}
    )


@router.message(ProfileEdit.age, F.text)
async def on_pedit_age(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    text = (message.text or "").strip()
    if not text.isdigit() or not (10 <= int(text) <= 100):
        await message.answer("Введите число от 10 до 100.")
        return
    await _apply_update_and_show_profile(
        message, container, user_id, state, {dk.AGE: int(text)}
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
            reply_markup=kb.directions_keyboard(children, show_back=True)
        )
        return
    if node.is_other:
        await state.set_state(ProfileEdit.direction_custom)
        await cq.message.edit_reply_markup(reply_markup=None)
        await cq.message.answer("Опишите направление текстом:")
        return
    await _apply_update_and_show_profile(
        cq.message, container, user_id, state,
        {dk.DIRECTION_ID: str(node.id), dk.CUSTOM_DIRECTION_LABEL: None},
    )


@router.message(ProfileEdit.direction_custom, F.text)
async def on_pedit_direction_custom(
    message: Message, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    await _apply_update_and_show_profile(
        message, container, user_id, state,
        {dk.CUSTOM_DIRECTION_LABEL: message.text.strip()},
    )


@router.callback_query(ProfileEdit.user_status, F.data.startswith("st:"))
async def on_pedit_user_status(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    raw = (cq.data or "")[3:]
    await _apply_update_and_show_profile(
        cq.message, container, user_id, state, {dk.USER_STATUS: raw}
    )


@router.callback_query(ProfileEdit.team_mode, F.data.startswith("tm:"))
async def on_pedit_team_mode(
    cq: CallbackQuery, state: FSMContext, container: Container, user_id: UUID | None
) -> None:
    if user_id is None or cq.message is None:
        return
    await cq.answer()
    mode = (cq.data or "").split(":")[1]
    await _apply_update_and_show_profile(
        cq.message, container, user_id, state, {dk.TEAM_SEEKING_MODE: mode}
    )
```

- [ ] **Step 7: Update cmd_start to mention /profile**

In `src/presentation/bot/onboarding_handlers.py`, change the welcome-back message (line 69-72) from:

```python
        await message.answer(
            f"С возвращением, {user.first_name}! Профиль заполнен. "
            "Редактирование профиля можно добавить отдельной командой позже."
        )
```

To:

```python
        await message.answer(
            f"С возвращением, {user.first_name}! Профиль заполнен.\n"
            "/profile — посмотреть и отредактировать профиль\n"
            "/search — найти сокомандника"
        )
```

- [ ] **Step 8: Commit**

```bash
git add src/presentation/bot/states.py src/presentation/bot/keyboards.py src/presentation/bot/onboarding_handlers.py src/presentation/bot/onboarding_prompts.py src/presentation/bot/onboarding_resume.py src/presentation/bot/profile_handlers.py
git commit -m "feat(profile): add age to onboarding, profile view/edit with avatars"
```

---

### Task 4: Search Feature (handlers, keyboards, states)

> **Can run in parallel with Task 3** after Tasks 1-2 are done.

**Files:**
- Modify: `src/presentation/bot/states.py` (already modified in Task 3 — if running in parallel, add Search states independently)
- Modify: `src/presentation/bot/keyboards.py`
- Create: `src/presentation/bot/search_handlers.py`

- [ ] **Step 1: Add Search state group to states.py**

In `src/presentation/bot/states.py`, add at the end:

```python
class Search(StatesGroup):
    pick_direction = State()
    pick_status = State()
    browsing = State()
```

- [ ] **Step 2: Add search keyboards**

In `src/presentation/bot/keyboards.py`, add at the end:

```python
def search_status_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Школьник", callback_data=f"sst:{UserStatus.SCHOOL.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Студент", callback_data=f"sst:{UserStatus.STUDENT.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Магистрант", callback_data=f"sst:{UserStatus.MASTER.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Не учусь", callback_data=f"sst:{UserStatus.NOT_STUDYING.value}"
                )
            ],
            [
                InlineKeyboardButton(text="Любой", callback_data="sst:any")
            ],
        ]
    )


def search_direction_keyboard(
    directions: list[Direction], *, show_back: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=d.name, callback_data=f"sdir:{d.id}")]
        for d in directions
    ]
    rows.insert(0, [InlineKeyboardButton(text="Любое направление", callback_data="sdir:any")])
    if show_back:
        rows.append([InlineKeyboardButton(text="Назад", callback_data="sdir:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_pagination_keyboard(offset: int, total: int) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    if offset > 0:
        buttons.append(InlineKeyboardButton(text="<<", callback_data="spg:prev"))
    buttons.append(
        InlineKeyboardButton(text=f"{offset + 1}/{total}", callback_data="spg:noop")
    )
    if offset + 1 < total:
        buttons.append(InlineKeyboardButton(text=">>", callback_data="spg:next"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])
```

- [ ] **Step 3: Create search_handlers.py**

Create `src/presentation/bot/search_handlers.py`:

```python
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
    lines.append(f"{user.first_name} {user.last_name}, {user.age} лет")
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

    fltr = SearchFilter(
        direction_id=UUID(direction_id) if direction_id else None,
        user_status=UserStatus(status_raw) if status_raw else None,
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
    await state.update_data(search_direction_id=None, search_status=None, search_offset=0)
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
    await state.set_state(Search.browsing)
    await _show_result(cq.message, container, state, cq.bot, user_id)


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
```

- [ ] **Step 4: Commit**

```bash
git add src/presentation/bot/states.py src/presentation/bot/keyboards.py src/presentation/bot/search_handlers.py
git commit -m "feat(search): add teammate search with filters and card pagination"
```

---

### Task 5: Wire Everything Together in main.py

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Register profile and search routers**

In `src/main.py`, add imports:

```python
from src.presentation.bot import profile_handlers, search_handlers
```

Add router registrations after `dp.include_router(onboarding_handlers.router)`:

```python
        dp.include_router(profile_handlers.router)
        dp.include_router(search_handlers.router)
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: register profile and search routers in main"
```

---

### Task 6: Final Integration Commit

- [ ] **Step 1: Verify all files are committed**

```bash
git status
```

Expected: clean working tree.

- [ ] **Step 2: Final commit if any remaining changes**

```bash
git add -A
git commit -m "feat: complete profile, search, age, avatar features"
```
