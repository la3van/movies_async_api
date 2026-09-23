"""Ограниченный шаблонизатор: только {{ variable }}, без исполнения кода."""

import html
import re

VARIABLE = re.compile(r"{{\s*([a-z][a-z0-9_]{0,39})\s*}}")


def validate_template(value: str) -> None:
    """Отклоняет выражения за пределами простых подстановок."""
    rest = VARIABLE.sub("", value)
    if any(marker in rest for marker in ("{{", "}}", "{%", "%}", "{#", "#}")):
        raise ValueError("Only {{ variable }} interpolation is supported")


MAX_RENDERED_LENGTH = 200000


def render(value: str, context: dict[str, str], escape: bool = False) -> str:
    """Собирает письмо, проверяя размер до выделения каждого фрагмента."""
    if len(value) > MAX_RENDERED_LENGTH:
        raise ValueError("Rendered message is too large")
    validate_template(value)
    fragments: list[str] = []
    length = 0
    position = 0
    for match in VARIABLE.finditer(value):
        literal_length = match.start() - position
        key = match.group(1)
        if key not in context:
            raise ValueError("Missing template variable: " + key)
        replacement = context[key]
        replacement_length = len(replacement)
        if escape:
            for char, extra in (
                ("&", 4),
                ("<", 3),
                (">", 3),
                ('"', 5),
                ("'", 5),
            ):
                replacement_length += replacement.count(char) * extra
        length += literal_length + replacement_length
        if length > MAX_RENDERED_LENGTH:
            raise ValueError("Rendered message is too large")
        fragments.append(value[position: match.start()])
        fragments.append(html.escape(replacement) if escape else replacement)
        position = match.end()
    if length + len(value) - position > MAX_RENDERED_LENGTH:
        raise ValueError("Rendered message is too large")
    fragments.append(value[position:])
    return "".join(fragments)
