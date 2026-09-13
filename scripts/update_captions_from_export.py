#!/usr/bin/env python3
"""Update only content captions from a Telegram Desktop HTML export."""

import argparse
import json
from pathlib import Path

from build_lesson_menu_data import parse_export_messages


def update_captions(data_file: Path, export_dir: Path, apply: bool) -> tuple[int, int]:
    data = json.loads(data_file.read_text(encoding="utf-8"))
    messages = parse_export_messages(export_dir / "messages.html")
    updated = 0
    missing = 0

    for parent in data["parents"]:
        for section in parent["sections"]:
            for item in section["items"]:
                for content in item["contents"]:
                    message = messages.get(content.get("source_message_id"))
                    if message is None or not message["caption_html"]:
                        missing += 1
                        continue
                    if content.get("caption_html") != message["caption_html"]:
                        content["caption_html"] = message["caption_html"]
                        updated += 1

    if apply:
        data_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return updated, missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", type=Path)
    parser.add_argument(
        "--data-file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "lesson_menu.json",
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    updated, missing = update_captions(
        args.data_file.resolve(), args.export_dir.resolve(), args.apply
    )
    action = "updated" if args.apply else "would update"
    print(f"Captions {action}: {updated}; missing or empty in export: {missing}")


if __name__ == "__main__":
    main()