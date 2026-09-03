"""Точка запуска ETL-приложения."""

from postgres_to_es.bootstrap import build_etl_service


def main() -> None:
    """Запускает ETL-сервис."""
    with build_etl_service() as service:
        service.run()


if __name__ == "__main__":
    main()
