"""Проверки состояния процесса и свежести рабочего цикла."""

import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

HEARTBEAT = Path("/tmp/notification-heartbeat")


def beat() -> None:
    """Отмечает время успешно завершённой итерации процесса."""
    HEARTBEAT.touch()


def unready() -> None:
    """Сбрасывает признак готовности после ошибки рабочего цикла."""
    HEARTBEAT.unlink(missing_ok=True)


def healthy(max_age: float = 90) -> bool:
    """Проверяет, что последняя успешная итерация достаточно свежая."""
    try:
        return time.time() - HEARTBEAT.stat().st_mtime < max_age
    except FileNotFoundError:
        return False


class HealthServer:
    """HTTP-сервер состояния фонового процесса и его метрик."""

    def __init__(self, max_age: float) -> None:
        """Запускает служебный HTTP-сервер в отдельном потоке."""

        class Handler(BaseHTTPRequestHandler):
            """Обработчик служебных HTTP-запросов фонового процесса."""

            def do_GET(self) -> None:
                """Возвращает состояние процесса или метрики Prometheus."""
                if self.path == "/metrics":
                    from prometheus_client import generate_latest

                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "text/plain; version=0.0.4"
                    )
                    self.end_headers()
                    self.wfile.write(generate_latest())
                    return
                if self.path == "/health":
                    code = 200
                elif self.path == "/ready":
                    code = 200 if healthy(max_age) else 503
                else:
                    code = 404
                self.send_response(code)
                self.end_headers()
                self.wfile.write(b"OK" if code == 200 else b"NOT_READY")

            def log_message(self, format: str, *args: Any) -> None:
                """Подавляет стандартный журнал служебных HTTP-запросов."""
                pass

        HEARTBEAT.unlink(missing_ok=True)
        self.server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        """Закрывает HTTP-сервер и дожидается завершения его потока."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


if __name__ == "__main__":
    from core.config import get_settings

    raise SystemExit(0 if healthy(get_settings().health_stale_seconds) else 1)
