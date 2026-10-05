"""Raqamlangan PostgreSQL dumplardan birini interaktiv tanlab tiklaydi.

    python3 restore.py
"""

import sys

from sqlalchemy.engine import make_url

from config import DB_URL, DUMPS_DIR
from db_backup import BackupError, create_backup, list_backups, restore_backup


def main() -> int:
    backups = list_backups()
    if not backups:
        print(f"❌ Dump topilmadi: {DUMPS_DIR}")
        return 1

    print("Mavjud dumplar (eng yangisi tepada):")
    for index, path in enumerate(backups, start=1):
        size_mb = path.stat().st_size / (1024 * 1024)
        latest = "  ← oxirgisi" if index == 1 else ""
        print(f"  {index}. {path.name} ({size_mb:.2f} MB){latest}")

    raw = input(f"Qaysi dump tiklansin? [1-{len(backups)}, Enter=1]: ").strip()
    try:
        choice = int(raw or "1")
        if not 1 <= choice <= len(backups):
            raise ValueError
        selected = backups[choice - 1]
    except ValueError:
        print("❌ Noto'g'ri tanlov")
        return 1

    database = make_url(DB_URL).database or "(noma'lum)"
    confirm = input(
        f"⚠️ '{database}' bazasi {selected.name} holatiga qaytariladi. "
        "Davom etish uchun RESTORE yozing: "
    ).strip()
    if confirm != "RESTORE":
        print("Bekor qilindi")
        return 0

    print("Joriy holat xavfsizlik uchun dump qilinmoqda...")
    safety = create_backup(reason="pre_restore")
    print(f"✅ Xavfsizlik dumpi: {safety.name}")
    print(f"⏳ Tiklanmoqda: {selected.name}")
    restore_backup(selected)
    print("✅ Baza muvaffaqiyatli tiklandi")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except (BackupError, OSError) as exc:
        print(f"❌ Restore bajarilmadi: {exc}")
        code = 1
    except KeyboardInterrupt:
        print("\nBekor qilindi")
        code = 130
    sys.exit(code)
