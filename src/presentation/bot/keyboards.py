from __future__ import annotations

from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.domain.directions.entities import Direction
from src.domain.user.enums import TeamSeekingMode, UserStatus


def directions_keyboard(
    directions: list[Direction], *, show_back: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=d.name, callback_data=f"dir:{d.id}")]
        for d in directions
    ]
    if show_back:
        rows.append([InlineKeyboardButton(text="Назад", callback_data="dir:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_status_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Школьник", callback_data=f"st:{UserStatus.SCHOOL.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Студент", callback_data=f"st:{UserStatus.STUDENT.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Магистрант", callback_data=f"st:{UserStatus.MASTER.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Не учусь", callback_data=f"st:{UserStatus.NOT_STUDYING.value}"
                )
            ],
        ]
    )


def school_grade_keyboard() -> InlineKeyboardMarkup:
    grades = list(range(1, 12))
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for g in grades:
        row.append(InlineKeyboardButton(text=str(g), callback_data=f"gr:{g}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def student_course_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for c in range(1, 7):
        row.append(InlineKeyboardButton(text=str(c), callback_data=f"cr:{c}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def olympiad_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="oly:yes"),
                InlineKeyboardButton(text="Нет", callback_data="oly:no"),
            ],
        ]
    )


def team_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Ищу команду",
                    callback_data=f"tm:{TeamSeekingMode.LOOKING_FOR_TEAM.value}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Ищу людей",
                    callback_data=f"tm:{TeamSeekingMode.LOOKING_FOR_PEOPLE.value}",
                )
            ],
        ]
    )


def university_skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="uni:skip")],
        ]
    )


def finish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завершить регистрацию", callback_data="onb:finish"
                )
            ],
        ]
    )


def parse_dir_callback(data: str) -> UUID | str | None:
    if not data.startswith("dir:"):
        return None
    payload = data[4:]
    if payload == "back":
        return "back"
    try:
        return UUID(payload)
    except ValueError:
        return None


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
