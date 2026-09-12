#!/usr/bin/env python3
"""Create and order root menu buttons from a JSON file.

The command is a dry run unless --apply is passed. Existing child menu items and
content records are not changed.
"""

import argparse
import asyncio
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Set

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.base import close_db, session_maker  # noqa: E402
from db.models import MenuItem  # noqa: E402


DEFAULT_DATA_FILE = PROJECT_ROOT / "data" / "root_menu.json"
ALLOWED_CONTENT_TYPES = {"video", "document"}


def normalize_title(value: str) -> str:
    """Normalize harmless title differences used while matching existing rows."""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("‘", "'").replace("’", "'").replace("`", "'")
    return " ".join(value.casefold().split())


def load_items(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)

    if payload.get("schema_version") != 1:
        raise ValueError("Only schema_version=1 is supported")

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("'items' must be a non-empty list")

    known_aliases: Set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item #{index} must be an object")

        title = item.get("title")
        aliases = item.get("aliases", [])
        content_type = item.get("content_type")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Item #{index} has an invalid title")
        if len(title) > 64:
            raise ValueError(f"Title is longer than 64 characters: {title!r}")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Invalid content_type for {title!r}: {content_type!r}"
            )
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias.strip() for alias in aliases
        ):
            raise ValueError(f"Aliases for {title!r} must be non-empty strings")

        match_keys = {normalize_title(title)}
        match_keys.update(normalize_title(alias) for alias in aliases)
        duplicate_keys = known_aliases.intersection(match_keys)
        if duplicate_keys:
            raise ValueError(f"Duplicate title/alias found for {title!r}")

        known_aliases.update(match_keys)
        item["match_keys"] = match_keys

    return items


async def import_root_menu(items: List[Dict[str, Any]], apply: bool) -> None:
    async with session_maker() as session:
        result = await session.execute(
            select(MenuItem)
            .where(MenuItem.parent_id.is_(None))
            .order_by(MenuItem.position, MenuItem.id)
            .with_for_update()
        )
        existing_items = list(result.scalars())

        matches: Dict[int, MenuItem] = {}
        used_ids: Set[int] = set()
        for index, definition in enumerate(items):
            candidates = [
                menu_item
                for menu_item in existing_items
                if menu_item.id not in used_ids
                and normalize_title(menu_item.title) in definition["match_keys"]
            ]
            if len(candidates) > 1:
                ids = ", ".join(str(item.id) for item in candidates)
                raise ValueError(
                    f"Multiple root buttons match {definition['title']!r}: IDs {ids}"
                )
            if candidates:
                matches[index] = candidates[0]
                used_ids.add(candidates[0].id)

        ordered_items: List[MenuItem] = []
        created_titles: List[str] = []
        renamed_titles: List[str] = []
        activated_titles: List[str] = []

        for index, definition in enumerate(items):
            menu_item = matches.get(index)
            if menu_item is None:
                menu_item = MenuItem(
                    parent_id=None,
                    title=definition["title"],
                    position=index + 1,
                    is_active=True,
                    required_referrals=0,
                )
                session.add(menu_item)
                created_titles.append(definition["title"])
            else:
                if menu_item.title != definition["title"]:
                    renamed_titles.append(
                        f"{menu_item.title!r} -> {definition['title']!r}"
                    )
                    menu_item.title = definition["title"]
                if not menu_item.is_active:
                    menu_item.is_active = True
                    activated_titles.append(definition["title"])

            menu_item.position = index + 1
            ordered_items.append(menu_item)

        untouched_items = [
            menu_item for menu_item in existing_items if menu_item.id not in used_ids
        ]
        for position, menu_item in enumerate(
            untouched_items, start=len(ordered_items) + 1
        ):
            menu_item.position = position

        print("Root menu preview:")
        for position, menu_item in enumerate(ordered_items, start=1):
            state = "create" if menu_item.id is None else f"id={menu_item.id}"
            print(f"  {position:>2}. {menu_item.title} [{state}]")

        if untouched_items:
            print("Unlisted existing root buttons kept after configured buttons:")
            for menu_item in untouched_items:
                print(f"  {menu_item.position:>2}. {menu_item.title} [id={menu_item.id}]")

        print(f"Created: {len(created_titles)}")
        print(f"Renamed: {len(renamed_titles)}")
        print(f"Activated: {len(activated_titles)}")

        if renamed_titles:
            for title_change in renamed_titles:
                print(f"  rename: {title_change}")

        if apply:
            await session.commit()
            print("Changes committed to the database.")
        else:
            await session.rollback()
            print("Dry run only; no database changes were saved. Use --apply to save.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import root menu buttons into the configured PostgreSQL database."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"JSON input file (default: {DEFAULT_DATA_FILE})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit changes. Without this flag the command only shows a preview.",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    items = load_items(args.file.resolve())
    try:
        await import_root_menu(items, apply=args.apply)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(async_main())
