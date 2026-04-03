from __future__ import annotations

import punq
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.usecases.user.complete_onboarding import CompleteOnboarding
from src.application.usecases.user.get_user import GetUser
from src.application.usecases.user.patch_onboarding_draft import PatchOnboardingDraft
from src.application.usecases.user.resolve_or_create_user_by_external_identity import (
    ResolveOrCreateUserByExternalIdentity,
)
from src.application.usecases.user.update_user_profile import UpdateUserProfile
from src.application.usecases.user.search_users import SearchUsers
from src.domain.directions.repository import IDirectionRepository
from src.domain.user.repositories import IUserIdentityRepository, IUserRepository
from src.infra.database.repositories.direction_repository import (
    SqlAlchemyDirectionRepository,
)
from src.infra.database.repositories.identity_repository import (
    SqlAlchemyUserIdentityRepository,
)
from src.infra.database.repositories.user_repository import SqlAlchemyUserRepository


def build_container(session: AsyncSession) -> punq.Container:
    container = punq.Container()
    container.register(AsyncSession, instance=session)
    container.register(IUserRepository, SqlAlchemyUserRepository)
    container.register(IUserIdentityRepository, SqlAlchemyUserIdentityRepository)
    container.register(IDirectionRepository, SqlAlchemyDirectionRepository)
    container.register(ResolveOrCreateUserByExternalIdentity)
    container.register(PatchOnboardingDraft)
    container.register(CompleteOnboarding)
    container.register(GetUser)
    container.register(UpdateUserProfile)
    container.register(SearchUsers)
    return container
