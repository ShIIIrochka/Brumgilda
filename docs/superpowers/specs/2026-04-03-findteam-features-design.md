# FindTeam: Profile + Search Features Design

## Overview

Extend the FindTeam Telegram bot with three new capabilities:
1. Age field in onboarding
2. Profile viewing & editing with avatar support
3. Teammate search with filters, pagination, and avatar cards

Architecture: DDD + Clean Architecture + punq DI (following existing patterns).

---

## 1. Age Field in Onboarding

### Domain Changes
- `User` aggregate: add `age: int | None` field
- Draft key: `AGE = "age"`
- Validation: 10 <= age <= 100

### Onboarding Flow
- New FSM state `Onboarding.age` inserted between `last_name` and `direction_pick`
- Prompt: "Укажи свой возраст (число):"
- Parse integer from text, validate range, patch draft

### Database
- Migration: add `age INTEGER` column to `users` table

---

## 2. Profile Viewing & Editing

### Avatar Support
- On onboarding completion and on `/profile`, fetch user's Telegram profile photo via `bot.get_user_profile_photos()`
- Store `telegram_avatar_file_id: str | None` in User (cached, refreshed on profile view)
- Placeholder: bundled `assets/default_avatar.png` sent when no Telegram photo available
- Profile cards (own and in search) send photo with caption containing profile info

### `/profile` Command
- Shows current user's profile as a photo message:
  - Avatar (Telegram photo or placeholder)
  - Caption: Name, Age, Direction, Status, Education details, Olympiad, Team mode
- Inline buttons below:
  - `Имя` | `Фамилия` | `Возраст`
  - `Направление` | `Статус`
  - `Режим поиска`

### Edit Flow
- User taps edit button -> FSM state `ProfileEdit.<field>`
- User enters new value -> validated -> saved via `UpdateUserProfile` use case
- Returns to profile card with updated data

### New Use Case: `UpdateUserProfile`
- Input: `user_id: UUID`, `updates: dict[str, Any]`
- Loads user, applies updates to profile fields directly (not draft), validates, saves
- Domain method: `User.update_profile(updates)` with field-level validation

### FSM States
```python
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

---

## 3. Teammate Search

### `/search` Command Flow
1. Bot asks: "Выбери направление для поиска:" (direction tree, same as onboarding + "Любое" option)
2. Bot asks: "Выбери статус:" (school/student/master/not_studying + "Любой")
3. Bot shows: "Поиск..." -> displays first result card

### Search Logic
- Filter: completed onboarding only
- Filter: matching team_seeking_mode (LOOKING_FOR_TEAM sees LOOKING_FOR_PEOPLE and vice versa)
- Filter: direction_id match (if specified), user_status match (if specified)
- Order: by `created_at DESC`
- Exclude self from results
- Pagination: offset-based, 1 result per page

### Result Card
- Photo message: avatar of found user (Telegram photo or placeholder)
- Caption:
  ```
  {first_name} {last_name}, {age} лет
  {direction_name}
  {status_label}: {education_details}
  {olympiad_info if any}
  {team_mode_label}
  ```
- Inline buttons: `← | 1/N | →`

### Domain: Value Objects
```python
@dataclass(frozen=True)
class SearchFilter:
    direction_id: UUID | None
    user_status: UserStatus | None
    exclude_user_id: UUID
    seeking_mode: TeamSeekingMode

@dataclass(frozen=True)
class SearchResult:
    users: list[User]
    total: int
    offset: int
    limit: int
```

### New Use Case: `SearchUsers`
- Input: `SearchFilter`, `offset: int`, `limit: int = 1`
- Delegates to `IUserRepository.search(filter, offset, limit)`
- Returns `SearchResult`

### Repository Extension
- `IUserRepository` gets new method: `async def search(filter: SearchFilter, offset: int, limit: int) -> SearchResult`
- SQL: SELECT with WHERE clauses per filter, COUNT for total, LIMIT/OFFSET

### FSM States
```python
class Search(StatesGroup):
    pick_direction = State()
    pick_status = State()
    browsing = State()  # stores filter + offset in FSM data
```

---

## 4. File Structure (new/changed)

```
src/
  domain/
    user/
      user.py                  # EDIT: +age, +update_profile(), +telegram_avatar_file_id
      repositories.py          # EDIT: +search() method
      draft_keys.py            # EDIT: +AGE
      value_objects.py         # NEW: SearchFilter, SearchResult
  application/
    usecases/user/
      update_user_profile.py   # NEW
      search_users.py          # NEW
  infra/
    database/
      models.py                # EDIT: +age, +telegram_avatar_file_id columns
      repositories/
        user_repository.py     # EDIT: +search() implementation
  presentation/
    bot/
      profile_handlers.py      # NEW: /profile view + edit FSM
      search_handlers.py       # NEW: /search + filters + pagination
      onboarding_handlers.py   # EDIT: +age handler
      onboarding_prompts.py    # EDIT: +age prompt
      onboarding_resume.py     # EDIT: +age validation step
      keyboards.py             # EDIT: +profile edit KB, +search KBs, +pagination KB
      states.py                # EDIT: +ProfileEdit, +Search state groups
  main.py                      # EDIT: register new routers
assets/
  default_avatar.png           # NEW: placeholder avatar image
alembic/
  versions/
    xxxx_add_age_and_avatar.py # NEW: migration
```

---

## 5. DI Container Updates

Register in `build_container()`:
- `UpdateUserProfile` use case
- `SearchUsers` use case

---

## 6. Validation Rules

| Field | Rule |
|-------|------|
| age | 10 <= age <= 100, integer |
| profile update | only completed-onboarding users can edit |
| search | only completed-onboarding users can search |
| search results | only completed-onboarding users appear |

---

## 7. Commands Summary

| Command | Description |
|---------|-------------|
| `/start` | Start onboarding (existing) |
| `/profile` | View own profile + edit buttons |
| `/search` | Search for teammates |
