"""Ограниченный шаблонизатор: только {{ variable }}, без исполнения кода."""

import html
import re

VARIABLE = re.compile(r"{{\s*([a-z][a-z0-9_]{0,39})\s*}}")


def validate_template(value: str) -> None:
    """Отклоняет выражения за пределами простых подстановок."""
    rest = VARIABLE.sub("", value)
    if any(marker in rest for marker in ("{{", "}}", "{%", "%}", "{#", "#}")):
        raise ValueError("Only {{ variable }} interpolation is supported")


def render(value: str, context: dict[str, str], escape: bool = False) -> str:
    """Подставляет переменные, при необходимости экранируя HTML."""
    validate_template(value)

    def replace(match: re.Match[str]) -> str:
        """Подставляет обязательную переменную вместо найденного маркера."""
        key = match.group(1)
        if key not in context:
            raise ValueError("Missing template variable: " + key)
        return html.escape(context[key]) if escape else context[key]

    result = VARIABLE.sub(replace, value)
    if len(result) > 200000:
        raise ValueError("Rendered message is too large")
    return result
