"""OAuth-интеграция auth-сервиса."""

from oauth.base import OAuthProvider
from oauth.enums import OAuthProviderName
from oauth.models import (
    OAuthAuthorizationData,
    OAuthStateData,
    OAuthToken,
    OAuthUserInfo,
)
from oauth.registry import OAuthProviderRegistry
from oauth.state import RedisOAuthStateStore

__all__ = (
    "OAuthAuthorizationData",
    "OAuthProvider",
    "OAuthProviderName",
    "OAuthProviderRegistry",
    "OAuthStateData",
    "OAuthToken",
    "OAuthUserInfo",
    "RedisOAuthStateStore",
)
