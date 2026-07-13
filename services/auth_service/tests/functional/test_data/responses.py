"""Ожидаемые поля ответов auth-сервиса."""
TOKEN_PAIR_FIELDS = {
    'access_token',
    'refresh_token',
    'token_type',
}

USER_RESPONSE_FIELDS = {
    'id',
    'login',
    'email',
    'first_name',
    'last_name',
    'is_active',
    'is_superuser',
    'roles',
    'created_at',
    'updated_at',
}

ROLE_RESPONSE_FIELDS = {
    'id',
    'name',
    'description',
    'is_default',
    'permissions',
    'created_at',
    'updated_at',
}

PERMISSION_RESPONSE_FIELDS = {
    'id',
    'code',
    'description',
    'created_at',
    'updated_at',
}

LOGIN_HISTORY_RESPONSE_FIELDS = {
    'id',
    'login',
    'is_successful',
    'reason',
    'user_agent',
    'ip_address',
    'created_at',
    'updated_at',
}

PAGINATED_RESPONSE_FIELDS = {
    'items',
    'total',
    'limit',
    'offset',
}
