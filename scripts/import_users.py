#!/usr/bin/env python3
"""Import Telegram users from JSON without overwriting existing users.

Expected input:
[
    {"tg_id": 123456789, "full_name": "User Name", "username": "username"}
]

The command only previews changes unless --apply is passed.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Iterator, List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.base import close_db, session_maker  # noqa: E402
from db.models import User  # noqa: E402


DEFAULT_DATA_FILE = PROJECT_ROOT / "users.json"
DEFAULT_BATCH_SIZE = 1_000
LOOKUP_BATCH_SIZE = 5_000


def batches(values: List[Any], size: int) -> Iterator[List[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def load_users(path: Path) -> List[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as source:
        payload = json.load(source)

    if not isinstance(payload, list):
        raise ValueError("JSON root must be a list of users")
    if not payload:
        raise ValueError("Users list is empty")

    users: List[dict[str, Any]] = []
    seen_ids = set()
    for index, raw in enumerate(payload, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"User #{index} must be an object")

        tg_id = raw.get("tg_id")
        full_name = raw.get("full_name")
        username = raw.get("username")

        if isinstance(tg_id, bool) or not isinstance(tg_id, int) or tg_id <= 0:
            raise ValueError(f"User #{index} has an invalid tg_id")
        if tg_id in seen_ids:
            raise ValueError(f"Duplicate tg_id at user #{index}: {tg_id}")
        seen_ids.add(tg_id)

        if not isinstance(full_name, str) or not full_name.strip():
            raise ValueError(f"User #{index} has an invalid full_name")
        full_name = full_name.strip()
        if len(full_name) > 255:
            raise ValueError(f"User #{index} full_name is longer than 255 characters")

        if username is not None:
            if not isinstance(username, str):
                raise ValueError(f"User #{index} has an invalid username")
            username = username.strip().lstrip("@") or None
            if username is not None and len(username) > 64:
                raise ValueError(f"User #{index} username is longer than 64 characters")

        users.append(
            {
                "tg_id": tg_id,
                "full_name": full_name,
                "username": username,
                "is_active": True,
            }
        )
    return users


async def existing_user_ids(tg_ids: List[int]) -> set[int]:
    existing = set()
    async with session_maker() as session:
        for chunk in batches(tg_ids, LOOKUP_BATCH_SIZE):
            rows = await session.scalars(select(User.tg_id).where(User.tg_id.in_(chunk)))
            existing.update(rows)
    return existing


async def import_users(
    users: List[dict[str, Any]], apply: bool, batch_size: int
) -> None:
    existing_ids = await existing_user_ids([user["tg_id"] for user in users])
    new_users = [user for user in users if user["tg_id"] not in existing_ids]

    print(f"JSON users: {len(users)}")
    print(f"Already in database (kept unchanged): {len(existing_ids)}")
    print(f"New users to insert: {len(new_users)}")

    if not apply:
        print("Dry run only; no database changes were saved. Use --apply to import.")
        return
    if not new_users:
        print("Nothing to import.")
        return

    inserted = 0
    async with session_maker() as session:
        for chunk in batches(new_users, batch_size):
            statement = (
                pg_insert(User)
                .values(chunk)
                .on_conflict_do_nothing(index_elements=["tg_id"])
            )
            result = await session.execute(statement)
            inserted += result.rowcount or 0
        await session.commit()

    print(f"Imported: {inserted}")
    if inserted != len(new_users):
        print(
            f"Skipped due to concurrent/existing rows: {len(new_users) - inserted}"
        )
    print("Import committed to the database.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import users.json into PostgreSQL without overwriting existing users."
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.batch_size > 5_000:
        raise ValueError("--batch-size must be between 1 and 5000")

    users = load_users(args.file.resolve())
    try:
        await import_users(users, apply=args.apply, batch_size=args.batch_size)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(async_main())
