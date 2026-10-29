"""Takliflar reytingi posti uchun ``{users-N}`` kalitlarini almashtirish."""

import re
from html import escape
from typing import Sequence

from db.models import User

USER_LIST_RE = re.compile(r"\{users-(\d+)\}")
MAX_RATING_USERS = 50


def rating_limits(template: str) -> list[int]:
    """Shablondagi haqiqiy limitlarni qaytaradi (1..50)."""
    return [
        min(max(int(match), 1), MAX_RATING_USERS)
        for match in USER_LIST_RE.findall(template)
    ]


def _rating_lines(rows: Sequence[tuple[User, int]], limit: int) -> str:
    if not rows:
        return "Hozircha reyting ma'lumotlari yo'q."
    lines: list[str] = []
    for index, (user, count) in enumerate(rows[:limit], start=1):
        name = user.full_name or (f"@{user.username}" if user.username else str(user.tg_id))
        name = name[:48] + ("…" if len(name) > 48 else "")
        lines.append(f"{index}. {escape(name)} — <b>{count}</b> ta")
    return "\n".join(lines)


def render_rating_text(template: str, rows: Sequence[tuple[User, int]]) -> str:
    """Har bir ``{users-N}`` o'rniga top-N ni qo'yadi.

    Markerning oldi va ketidagi mavjud bo'sh satrlar normallashtirilib,
    reyting ro'yxatining tepa-pastida aynan bittadan bo'sh satr qoldiriladi.
    """
    if not USER_LIST_RE.search(template):
        return template

    padded = re.compile(r"(?:[ \t]*\n)*[ \t]*\{users-(\d+)\}[ \t]*(?:\n[ \t]*)*")

    def replace(match: re.Match[str]) -> str:
        limit = min(max(int(match.group(1)), 1), MAX_RATING_USERS)
        return f"\n\n{_rating_lines(rows, limit)}\n\n"

    return padded.sub(replace, template).strip()
