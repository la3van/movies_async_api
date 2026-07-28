"""PKCE и одноразовое Redis-хранилище OAuth-state."""
import base64
import hashlib
import secrets

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from oauth.enums import OAuthProviderName
from oauth.models import (
    OAuthAuthorizationData,
    OAuthStateData,
)
from services.exceptions import (
    InvalidOAuthStateError,
    OAuthStateStorageError,
)


_STATE_BYTES = 32
_CODE_VERIFIER_BYTES = 64
_STATE_CREATE_ATTEMPTS = 3


class RedisOAuthStateStore:
    """Хранит состояние незаверённых OAuth-flow в Redis."""
    def __init__(
        self,
        *,
        redis: Redis,
        key_prefix: str,
        ttl_seconds: int,
    ) -> None:
        """Инициализирует хранилище OAuth-state."""
        if not key_prefix:
            raise ValueError(
                'OAuth state key prefix must not be empty',
            )

        if ttl_seconds < 1:
            raise ValueError(
                'OAuth state TTL must be greater than zero',
            )

        self._redis = redis
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds

    async def create(
        self,
        *,
        provider: OAuthProviderName,
        redirect_uri: str,
    ) -> OAuthAuthorizationData:
        """Создаёт и сохраняет новое OAuth-состояние."""
        for _ in range(_STATE_CREATE_ATTEMPTS):
            state = secrets.token_urlsafe(
                _STATE_BYTES,
            )
            code_verifier = secrets.token_urlsafe(
                _CODE_VERIFIER_BYTES,
            )
            code_challenge = _build_code_challenge(
                code_verifier,
            )

            state_data = OAuthStateData(
                provider=provider,
                code_verifier=code_verifier,
                redirect_uri=redirect_uri,
            )

            redis_key = self._build_key(state)

            try:
                created = await self._redis.set(
                    name=redis_key,
                    value=state_data.model_dump_json(),
                    ex=self._ttl_seconds,
                    nx=True,
                )
            except RedisError as error:
                raise OAuthStateStorageError(
                    'Could not save OAuth state',
                ) from error

            if created:
                return OAuthAuthorizationData(
                    state=state,
                    code_challenge=code_challenge,
                )

        raise OAuthStateStorageError(
            'Could not allocate unique OAuth state',
        )

    async def consume(
        self,
        *,
        state: str,
        expected_provider: OAuthProviderName,
    ) -> OAuthStateData:
        """Одноразово извлекает и проверяет OAuth-состояние."""
        if not state:
            raise InvalidOAuthStateError(
                'OAuth state is missing',
            )

        redis_key = self._build_key(state)

        try:
            raw_state_data = await self._redis.getdel(redis_key)
        except RedisError as error:
            raise OAuthStateStorageError(
                'Could not read OAuth state'
            ) from error

        if raw_state_data is None:
            raise InvalidOAuthStateError(
                'OAuth state is invalid, expired or already used',
            )

        try:
            state_data = OAuthStateData.model_validate_json(
                raw_state_data,
            )
        except ValidationError as error:
            raise InvalidOAuthStateError(
                'OAuth state data is invalid',
            ) from error

        if state_data.provider != expected_provider:
            raise InvalidOAuthStateError(
                'OAuth state provider does not match callback provider',
            )

        return state_data

    def _build_key(
        self,
        state: str,
    ) -> str:
        """Формирует Redis-ключ по хешу OAuth-service."""
        state_hash = hashlib.sha256(
            state.encode('utf-8'),
        ).hexdigest()

        return f'{self._key_prefix}:{state_hash}'


def _build_code_challenge(
    code_verifier: str,
) -> str:
    """Вычисляет PKCE code challenge методом S256."""
    verifier_digest = hashlib.sha256(
        code_verifier.encode('ascii'),
    ).digest()

    return (
        base64.urlsafe_b64encode(
            verifier_digest,
        )
        .rstrip(b'=')
        .decode('ascii')
    )
