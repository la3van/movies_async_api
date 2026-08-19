"""Конфигурация Gunicorn."""
import os

bind = os.getenv(
    "GUNICORN_BIND",
    "0.0.0.0:8000",
)

workers = int(
    os.getenv(
        "GUNICORN_WORKERS",
        "2",
    ),
)

worker_class = "gevent"
worker_connections = int(
    os.getenv(
        "GUNICORN_WORKER_CONNECTIONS",
        "1000",
    ),
)

timeout = int(
    os.getenv(
        "GUNICORN_TIMEOUT",
        "30",
    ),
)
graceful_timeout = int(
    os.getenv(
        "GUNICORN_GRACEFUL_TIMEOUT",
        "10",
    ),
)

keepalive = int(
    os.getenv(
        "GUNICORN_KEEPALIVE",
        "5",
    ),
)

loglevel = os.getenv(
    "GUNICORN_LOG_LEVEL",
    "info",
)

accesslog = "-"
errorlog = "-"
