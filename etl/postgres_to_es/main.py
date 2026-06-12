"""Стартовая точка запуска PostgreSQL->Elasticsearch сервиса."""

from postgres_to_es.service import ETLService


if __name__ == '__main__':
    service = ETLService()
    service.run()
