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


class Search(StatesGroup):
    pick_direction = State()
    pick_status = State()
    browsing = State()
