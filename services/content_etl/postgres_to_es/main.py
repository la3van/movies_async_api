"""Точка запуска ETL-приложения."""

from logging.config import dictConfig

from postgres_to_es.bootstrap import build_etl_service
from postgres_to_es.config import get_settings
from postgres_to_es.logger import LOGGING_CONFIG
from postgres_to_es.sentry import init_sentry


def main() -> None:
    """Запускает ETL-сервис."""
    dictConfig(LOGGING_CONFIG)

    settings = get_settings()
    init_sentry(
        service_name=settings.project_name,
    )

    with build_etl_service() as service:
        service.run()


if __name__ == "__main__":
    main()
