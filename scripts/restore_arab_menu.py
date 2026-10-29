#!/usr/bin/env python3
"""Restore only the Arabic lesson menu from the arab-tili-menu-bot branch."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.base import close_db, session_maker  # noqa: E402
from db.models import Content, MenuItem  # noqa: E402


DATA_REF = "FETCH_HEAD:data/lesson_menu.json"


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("‘", "'").replace("’", "'").replace("`", "'")
    return " ".join(value.casefold().split())


def load_payload() -> dict[str, Any]:
    subprocess.run(
        ["git", "fetch", "origin", "arab-tili-menu-bot"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    raw = subprocess.check_output(
        ["git", "show", DATA_REF], cwd=PROJECT_ROOT, text=True
    )
    payload = json.loads(raw)
    if payload.get("schema_version") != 1 or not payload.get("parents"):
        raise ValueError("arab-tili-menu-bot dataset is missing or unsupported")
    return payload


async def children(session: Any, parent_id: int) -> list[MenuItem]:
    return list(
        await session.scalars(
            select(MenuItem)
            .where(MenuItem.parent_id == parent_id)
            .order_by(MenuItem.position, MenuItem.id)
            .with_for_update()
        )
    )


async def upsert_item(
    session: Any,
    parent_id: int | None,
    definition: dict[str, Any],
    position: int,
    counters: dict[str, int],
    root_position: int | None = None,
) -> MenuItem:
    if parent_id is None:
        candidates = list(
            await session.scalars(
                select(MenuItem)
                .where(MenuItem.parent_id.is_(None))
                .order_by(MenuItem.position, MenuItem.id)
                .with_for_update()
            )
        )
    else:
        candidates = await children(session, parent_id)

    title = definition["title"]
    matches = [
        item for item in candidates if normalize_title(item.title) == normalize_title(title)
    ]
    if len(matches) > 1:
        raise ValueError(f"Multiple menu items match {title!r}")

    if matches:
        item = matches[0]
        item.title = title
        item.position = item.position if parent_id is None else position
        item.is_active = True
        counters["reused"] += 1
    else:
        item = MenuItem(
            parent_id=parent_id,
            title=title,
            position=root_position if parent_id is None else position,
            is_active=True,
            required_referrals=0,
        )
        session.add(item)
        await session.flush()
        counters["created"] += 1
    return item


async def sync_contents(
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
        if content.source_chat_id is not None and content.source_message_id is not None
    }

    for position, definition in enumerate(definitions, start=1):
        message_id = definition["source_message_id"]
        content = by_source.get((source_chat_id, message_id))
        if content is None:
            position_matches = [
                current
                for current in existing
                if current.position == position
                and current.source_chat_id is None
                and current.source_message_id is None
                and current.type == definition["type"]
            ]
            if len(position_matches) > 1:
                raise ValueError(
                    f"Multiple unlinked contents at position {position} for item {item_id}"
                )
            content = position_matches[0] if position_matches else None

        if content is None:
            content = Content(menu_item_id=item_id)
            session.add(content)
            existing.append(content)
            counters["contents_created"] += 1
        else:
            counters["contents_reused"] += 1

        content.type = definition["type"]
        content.file_id = None
        content.source_chat_id = source_chat_id
        content.source_message_id = message_id
        content.text_html = definition.get("caption_html")
        content.position = position


async def restore(payload: dict[str, Any], source_chat_id: int, apply: bool) -> None:
    counters = {
        "created": 0,
        "reused": 0,
        "contents_created": 0,
        "contents_reused": 0,
        "contents_to_restore": 0,
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
        next_root_position = max((item.position for item in roots), default=0) + 1

        for parent_definition in payload["parents"]:
            parent_matches = [
                item
                for item in roots
                if normalize_title(item.title)
                == normalize_title(parent_definition["title"])
            ]
            if len(parent_matches) > 1:
                raise ValueError(f"Multiple root menus match {parent_definition['title']!r}")
            if parent_matches:
                parent = parent_matches[0]
                parent.title = parent_definition["title"]
                parent.is_active = True
                counters["reused"] += 1
            else:
                parent = await upsert_item(
                    session,
                    None,
                    parent_definition,
                    0,
                    counters,
                    root_position=next_root_position,
                )
                roots.append(parent)
                next_root_position += 1

            for section_position, section_definition in enumerate(
                parent_definition["sections"], start=1
            ):
                section = await upsert_item(
                    session,
                    parent.id,
                    section_definition,
                    section_position,
                    counters,
                )
                for item_position, item_definition in enumerate(
                    section_definition["items"], start=1
                ):
                    item = await upsert_item(
                        session,
                        section.id,
                        item_definition,
                        item_position,
                        counters,
                    )
                    definitions = item_definition["contents"]
                    counters["contents_to_restore"] += len(definitions)
                    if apply:
                        await sync_contents(
                            session,
                            item.id,
                            definitions,
                            source_chat_id,
                            counters,
                        )

        if apply:
            await session.commit()
        else:
            await session.rollback()

    action = "restored" if apply else "would restore"
    print(
        f"Menu items {action}: {counters['created']} create, "
        f"{counters['reused']} reuse"
    )
    print(
        f"Source contents {action}: {counters['contents_to_restore']} total; "
        f"{counters['contents_created']} create, {counters['contents_reused']} reuse"
    )
    print("No menu items or contents are deleted.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore Arabic lesson menu data without deleting other menus."
    )
    parser.add_argument(
        "--source-chat-id",
        type=int,
        default=int(os.getenv("SOURCE_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or 0)
        or None,
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    payload = load_payload()
    if args.apply:
        if args.source_chat_id is None:
            raise ValueError("Set SOURCE_CHAT_ID or TELEGRAM_CHAT_ID in .env")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "migrate.py")],
            cwd=PROJECT_ROOT,
            check=True,
        )
    try:
        await restore(payload, args.source_chat_id or 0, apply=args.apply)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(async_main())