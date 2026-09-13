#!/usr/bin/env python3
"""Import lesson submenus whose videos are copied from a Telegram channel.

The command is a dry run unless --apply is passed. It stores only the source
chat/message references; video files are not uploaded or saved in PostgreSQL.
"""

import argparse
import asyncio
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import BASE_DIR  # noqa: E402  (loads .env)
from db.base import close_db, session_maker  # noqa: E402
from db.models import Content, MenuItem  # noqa: E402


DEFAULT_DATA_FILE = BASE_DIR / "data" / "lesson_menu.json"


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("‘", "'").replace("’", "'").replace("`", "'")
    return " ".join(value.casefold().split())


def load_payload(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)

    if payload.get("schema_version") != 1:
        raise ValueError("Only schema_version=1 is supported")

    parents = payload.get("parents")
    if not isinstance(parents, list) or not parents:
        raise ValueError("'parents' must be a non-empty list")

    for parent in parents:
        _validate_title(parent.get("title"), "parent")
        sections = parent.get("sections")
        if not isinstance(sections, list) or not sections:
            raise ValueError(f"Sections are missing for {parent.get('title')!r}")
        for section in sections:
            _validate_title(section.get("title"), "section")
            items = section.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError(f"Items are missing for {section.get('title')!r}")
            for item in items:
                _validate_title(item.get("title"), "item")
                contents = item.get("contents")
                if not isinstance(contents, list) or not contents:
                    raise ValueError(f"Contents are missing for {item.get('title')!r}")
                for content in contents:
                    if content.get("type") not in {"video", "document"}:
                        raise ValueError("Only video and document content is supported")
                    message_id = content.get("source_message_id")
                    if not isinstance(message_id, int) or message_id <= 0:
                        raise ValueError(
                            f"Invalid source_message_id for {content.get('title')!r}"
                        )
    return payload


def _validate_title(value: Any, kind: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise ValueError(f"Invalid {kind} title: {value!r}")


async def _children(session: Any, parent_id: int) -> list[MenuItem]:
    return list(
        await session.scalars(
            select(MenuItem)
            .where(MenuItem.parent_id == parent_id)
            .order_by(MenuItem.position, MenuItem.id)
            .with_for_update()
        )
    )


async def _upsert_child(
    session: Any,
    parent_id: int,
    definition: dict[str, Any],
    position: int,
    counters: dict[str, int],
) -> MenuItem:
    title = definition["title"]
    matches = [
        item
        for item in await _children(session, parent_id)
        if normalize_title(item.title) == normalize_title(title)
    ]
    if len(matches) > 1:
        raise ValueError(f"Multiple menu items match {title!r} under ID {parent_id}")

    if matches:
        item = matches[0]
        counters["reused"] += 1
        item.title = title
        item.position = position
        item.is_active = True
    else:
        item = MenuItem(
            parent_id=parent_id,
            title=title,
            position=position,
            is_active=True,
            required_referrals=0,
        )
        session.add(item)
        await session.flush()
        counters["created"] += 1
    return item


async def _sync_contents(
    session: Any,
    item_id: int,
    definitions: list[dict[str, Any]],
    source_chat_id: int,
    counters: dict[str, int],
) -> None:
    existing = list(
        await session.scalars(
            select(Content)
            .where(Content.menu_item_id == item_id)
            .order_by(Content.position, Content.id)
            .with_for_update()
        )
    )
    by_source = {
        (content.source_chat_id, content.source_message_id): content
        for content in existing
        if content.source_chat_id is not None
        and content.source_message_id is not None
    }

    for position, definition in enumerate(definitions, start=1):
        source_key = (source_chat_id, definition["source_message_id"])
        content = by_source.get(source_key)
        if content is None:
            content = Content(menu_item_id=item_id)
            session.add(content)
            counters["contents_created"] += 1
        else:
            counters["contents_reused"] += 1

        content.type = definition["type"]
        content.file_id = None
        content.source_chat_id = source_chat_id
        content.source_message_id = definition["source_message_id"]
        content.text_html = definition.get("caption_html")
        content.position = position


async def import_lessons(
    payload: dict[str, Any], source_chat_id: int, apply: bool
) -> None:
    counters = {
        "created": 0,
        "reused": 0,
        "contents_created": 0,
        "contents_reused": 0,
    }
    async with session_maker() as session:
        roots = list(
            await session.scalars(
                select(MenuItem)
                .where(MenuItem.parent_id.is_(None))
                .order_by(MenuItem.position, MenuItem.id)
                .with_for_update()
            )
        )

        for parent_definition in payload["parents"]:
            parent_matches = [
                item
                for item in roots
                if normalize_title(item.title)
                == normalize_title(parent_definition["title"])
            ]
            if len(parent_matches) != 1:
                raise ValueError(
                    f"Expected one existing root button named "
                    f"{parent_definition['title']!r}, found {len(parent_matches)}. "
                    "Run scripts/import_root_menu.py --apply first."
                )
            parent = parent_matches[0]

            for section_position, section_definition in enumerate(
                parent_definition["sections"], start=1
            ):
                section = await _upsert_child(
                    session,
                    parent.id,
                    section_definition,
                    section_position,
                    counters,
                )
                for item_position, item_definition in enumerate(
                    section_definition["items"], start=1
                ):
                    item = await _upsert_child(
                        session,
                        section.id,
                        item_definition,
                        item_position,
                        counters,
                    )
                    await _sync_contents(
                        session,
                        item.id,
                        item_definition["contents"],
                        source_chat_id,
                        counters,
                    )

        action = "committed" if apply else "rolled back (dry run)"
        if apply:
            await session.commit()
        else:
            await session.rollback()

    print(f"Source chat: {source_chat_id}")
    print(
        f"Menu items: {counters['created']} create, {counters['reused']} reuse"
    )
    print(
        "Contents: "
        f"{counters['contents_created']} create, "
        f"{counters['contents_reused']} reuse"
    )
    print(f"Changes {action}.")


def _default_source_chat_id() -> int | None:
    raw = os.getenv("SOURCE_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if raw and raw.lstrip("-").isdigit():
        return int(raw)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import lesson buttons and Telegram source-message references."
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--source-chat-id", type=int, default=_default_source_chat_id())
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.source_chat_id is None:
        raise ValueError(
            "Set SOURCE_CHAT_ID in .env or pass --source-chat-id -100..."
        )
    payload = load_payload(args.file.resolve())
    try:
        await import_lessons(payload, args.source_chat_id, apply=args.apply)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(async_main())
