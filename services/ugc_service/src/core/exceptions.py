"""Исключения доменного и инфраструктурного уровней."""


class UGCServiceError(Exception):
    """Базовая ожидаемая ошибка UGC Service."""

    detail = "ugc_service_error"


class EntityNotFoundError(UGCServiceError):
    """Запрошенная сущность отсутствует."""

    detail = "entity_not_found"


class ResourceConflictError(UGCServiceError):
    """Операция нарушает уникальность или состояние ресурса."""

    detail = "resource_conflict"


class ResourceForbiddenError(UGCServiceError):
    """Пользователь не имеет права менять ресурс."""

    detail = "resource_forbidden"


class DependencyUnavailableError(UGCServiceError):
    """Внешняя зависимость временно недоступна."""

    detail = "dependency_unavailable"


class FilmNotFoundError(EntityNotFoundError):
    """Фильм отсутствует в Content Service."""

    detail = "film_not_found"


class ReviewNotFoundError(EntityNotFoundError):
    """Рецензия не найдена."""

    detail = "review_not_found"


class RatingNotFoundError(EntityNotFoundError):
    """Оценка пользователя не найдена."""

    detail = "rating_not_found"
