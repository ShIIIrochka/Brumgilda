"""Идempotentные вставки направлений (совпадают с alembic 0001)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database.models import DirectionModel

IT = UUID("018f0001-0000-7000-8000-000000000001")
SPORT = UUID("018f0001-0000-7000-8000-000000000002")
ART = UUID("018f0001-0000-7000-8000-000000000003")
OTHER_AREA = UUID("018f0001-0000-7000-8000-000000000004")


def _row(
    i: UUID,
    p: UUID | None,
    name: str,
    order: int,
    is_other: bool = False,
) -> dict:
    return {
        "id": i,
        "parent_id": p,
        "name": name,
        "sort_order": order,
        "is_other": is_other,
    }


# Порядок: сначала корни, затем дети (FK на родителя).
_DIRECTION_SEED_ROWS: list[dict] = [
    _row(IT, None, "АЙТИ", 0),
    _row(SPORT, None, "СПОРТ", 1),
    _row(ART, None, "ИСКУССТВО", 2),
    _row(OTHER_AREA, None, "ДРУГОЕ НАПРАВЛЕНИЕ", 3),
    _row(UUID("018f0001-0000-7000-8000-000000000011"), IT, "ML", 0),
    _row(UUID("018f0001-0000-7000-8000-000000000012"), IT, "Backend", 1),
    _row(UUID("018f0001-0000-7000-8000-000000000013"), IT, "Frontend", 2),
    _row(UUID("018f0001-0000-7000-8000-000000000014"), IT, "Mobile", 3),
    _row(UUID("018f0001-0000-7000-8000-000000000015"), IT, "Дизайн", 4),
    _row(UUID("018f0001-0000-7000-8000-000000000017"), IT, "Продукт менеджер", 5),
    _row(UUID("018f0001-0000-7000-8000-000000000018"), IT, "Проджект менеджер", 6),
    _row(UUID("018f0001-0000-7000-8000-000000000016"), IT, "Другое", 7, True),
    _row(UUID("018f0001-0000-7000-8000-000000000021"), SPORT, "Баскетбол", 0),
    _row(UUID("018f0001-0000-7000-8000-000000000022"), SPORT, "Футбол", 1),
    _row(UUID("018f0001-0000-7000-8000-000000000023"), SPORT, "Другое", 2, True),
    _row(UUID("018f0001-0000-7000-8000-000000000031"), ART, "Графический дизайн", 0),
    _row(UUID("018f0001-0000-7000-8000-000000000032"), ART, "Другое", 1, True),
    _row(UUID("018f0001-0000-7000-8000-000000000041"), OTHER_AREA, "Указать вручную", 0, True),
]


async def ensure_directions_seed(session: AsyncSession) -> None:
    stmt = (
        pg_insert(DirectionModel)
        .values(_DIRECTION_SEED_ROWS)
        .on_conflict_do_nothing(index_elements=[DirectionModel.id])
    )
    await session.execute(stmt)
