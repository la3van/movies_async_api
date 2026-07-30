"""Безопасное определение исходного IP-адреса клиента."""
from __future__ import annotations

import socket
from ipaddress import ip_address, ip_network

from fastapi import Request

from core.config import get_settings


def get_client_ip(request: Request) -> str | None:
    """Возвращает исходный IP только через доверенный proxy."""
    direct_ip = _normalize_ip(
        request.client.host
        if request.client is not None
        else None,
    )

    if direct_ip is None:
        return None

    settings = get_settings()

    if not _is_trusted_proxy(
        direct_ip,
        settings.trusted_proxy_sources,
    ):
        return direct_ip

    real_ip = _normalize_ip(
        request.headers.get('x-real-ip'),
    )
    if real_ip is not None:
        return real_ip

    forwarded_for = request.headers.get(
        'x-forwarded-for',
    )
    if forwarded_for:
        first_forwarded_ip = forwarded_for.split(
            ',',
            maxsplit=1,
        )[0].strip()

        normalized_forwarded_ip = _normalize_ip(
            first_forwarded_ip,
        )

        if normalized_forwarded_ip is not None:
            return normalized_forwarded_ip

    return direct_ip


def _is_trusted_proxy(
    direct_ip: str,
    configured_sources: str,
) -> bool:
    """Проверячет IP по списку адресов, сетей и DNS-имён."""
    direct_address = ip_address(direct_ip)

    sources = (
        source.strip()
        for source in configured_sources.split(',')
        if source.strip()
    )

    for source in sources:
        try:
            network = ip_network(
                source,
                strict=False,
            )
        except ValueError:
            if direct_ip in _resolve_host(source):
                return True
        else:
            if direct_address in network:
                return True
    return False


def _resolve_host(host: str) -> set[str]:
    """Разрешает DNS-имя proxy в набор IP-адресов."""
    try:
        address_info = socket.getaddrinfo(
            host,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return set()

    resolved_addresses: set[str] = set()

    for item in address_info:
        normalized_ip = _normalize_ip(item[4][0])

        if normalized_ip is not None:
            resolved_addresses.add(normalized_ip)

    return resolved_addresses


def _normalize_ip(
    value: str | None,
) -> str | None:
    """Проверяет и нормализует IPv4 или IPv6."""
    if not value:
        return None

    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return None
