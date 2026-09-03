"""Сервис социальной OAuth-аутентификации."""

import hashlib

from cache.base import Cache
from core.security import generate_secure_token, hash_password
from core.tracing import trace_method
from models.user import User
from oauth.enums import OAuthProviderName
from oauth.models import OAuthUserInfo
from oauth.registry import OAuthProviderRegistry
from oauth.state import RedisOAuthStateStore
from services.cache_keys.users import (
    get_login_history_cache_pattern,
)
from services.exceptions import (
    InactiveUserError,
    OAuthAccountLinkRequiredError,
    OAuthEmailRequiredError,
    UserNotFoundError,
)
from services.login_session import create_login_session
from services.token import TokenPair, TokenService
from unit_of_work.base import (
    AbstractUnitOfWork,
    UnitOfWorkFactory,
)


class OAuthService:
    """Управляет OAuth-авторизацией через внешних провайдеров."""

    def __init__(
        self,
        *,
        provider_registry: OAuthProviderRegistry,
        state_store: RedisOAuthStateStore,
        uow_factory: UnitOfWorkFactory,
        token_service: TokenService,
        cache: Cache,
    ) -> None:
        """Сохраняет зависимости OAuth-сервиса."""
        self._provider_registry = provider_registry
        self._state_store = state_store
        self._uow_factory = uow_factory
        self._token_service = token_service
        self._cache = cache

    @trace_method("oauth.start_authorization")
    async def start_authorization(
        self,
        provider_name: OAuthProviderName,
    ) -> str:
        """Создаёт OAuth-state и возвращает URL авторизации."""
        provider = self._provider_registry.get(
            provider_name,
        )

        authorization_data = await self._state_store.create(
            provider=provider.name,
            redirect_uri=provider.redirect_uri,
        )

        return provider.build_authorization_url(
            state=authorization_data.state,
            code_challenge=(authorization_data.code_challenge),
        )

    @trace_method("oauth.authenticate")
    async def authenticate(
        self,
        *,
        provider_name: OAuthProviderName,
        code: str,
        state: str,
        device_id: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Завершает OAuth-вход и возвращает наши JWT."""
        provider = self._provider_registry.get(
            provider_name,
        )

        state_data = await self._state_store.consume(
            state=state,
            expected_provider=provider.name,
        )

        provider_token = await provider.exchange_code(
            code=code,
            code_verifier=state_data.code_verifier,
            redirect_uri=state_data.redirect_uri,
            state=state,
            device_id=device_id,
        )

        user_info = await provider.get_user_info(
            token=provider_token,
        )

        async with self._uow_factory() as uow:
            user = await self._get_or_create_user(
                uow=uow,
                provider_name=provider.name,
                user_info=user_info,
            )

            if not user.is_active:
                raise InactiveUserError(
                    "User is inactive",
                )

            token_pair = await create_login_session(
                uow=uow,
                token_service=self._token_service,
                user=user,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await uow.commit()

        await self._cache.delete_by_pattern(
            get_login_history_cache_pattern(
                user.id,
            ),
        )

        return token_pair

    async def _get_or_create_user(
        self,
        *,
        uow: AbstractUnitOfWork,
        provider_name: OAuthProviderName,
        user_info: OAuthUserInfo,
    ) -> User:
        """Находит либо создает локального OAuth-пользователя."""
        social_account = await uow.social_accounts.get_by_provider_identity(
            provider=provider_name.value,
            provider_user_id=user_info.provider_user_id,
        )
        if social_account is not None:
            return social_account.user

        email = self._get_required_email(
            user_info,
        )

        existing_user = await uow.users.get_by_email(email)
        if existing_user is not None:
            raise OAuthAccountLinkRequiredError(
                "A local account with this email already exists. "
                "Sign in with the existing account before linking "
                "the OAuth provider."
            )

        user = await uow.users.create(
            login=self._build_social_login(
                provider_name=provider_name,
                provider_user_id=(user_info.provider_user_id),
            ),
            email=email,
            password_hash=hash_password(
                generate_secure_token()[:64],
            ),
            first_name=user_info.first_name,
            last_name=user_info.last_name,
        )

        default_roles = await uow.roles.get_default_roles()

        if default_roles:
            await uow.users.add_roles(
                user,
                default_roles,
            )

        await uow.social_accounts.create(
            user_id=user.id,
            provider=provider_name.value,
            provider_user_id=(user_info.provider_user_id),
            email=email,
        )

        user_with_roles = await uow.users.get_by_id(
            user.id,
        )
        if user_with_roles is None:
            raise UserNotFoundError(
                "OAuth user was not created",
            )

        return user_with_roles

    @staticmethod
    def _get_required_email(
        user_info: OAuthUserInfo,
    ) -> str:
        """Возвращает подходящий email OAuth-пользователя."""
        if not user_info.email:
            raise OAuthEmailRequiredError(
                "OAuth provider did not return an email",
            )

        if user_info.email_verified is False:
            raise OAuthEmailRequiredError(
                "OAuth provider returned an unverified email",
            )

        return user_info.email.strip().lower()

    @staticmethod
    def _build_social_login(
        *,
        provider_name: OAuthProviderName,
        provider_user_id: str,
    ) -> str:
        """Генерирует технический уникальный login."""
        identity = f"{provider_name.value}:{provider_user_id}"

        identity_hash = hashlib.sha256(
            identity.encode("utf-8"),
        ).hexdigest()

        return f"oauth_{provider_name.value}_{identity_hash}"
