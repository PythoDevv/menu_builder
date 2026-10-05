"""PostgreSQL uchun raqamlangan dump yaratish va qayta tiklash yordamchilari."""

import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.engine import URL, make_url

from config import DB_URL, DUMPS_DIR, TIMEZONE

BACKUP_RE = re.compile(r"^backup_(\d{4,})_(\d{8}_\d{6})(?:_[a-z0-9_]+)?\.dump$")


class BackupError(RuntimeError):
    pass


def list_backups(directory: Path = DUMPS_DIR) -> list[Path]:
    """Yaroqli raqamlangan dumplarni eng yangisidan boshlab qaytaradi."""
    if not directory.exists():
        return []
    return sorted(
        (path for path in directory.iterdir() if BACKUP_RE.match(path.name)),
        key=lambda path: int(BACKUP_RE.match(path.name).group(1)),  # type: ignore[union-attr]
        reverse=True,
    )


def _next_number(directory: Path) -> int:
    backups = list_backups(directory)
    if not backups:
        return 1
    match = BACKUP_RE.match(backups[0].name)
    return int(match.group(1)) + 1 if match else 1


def _postgres_options(url: URL) -> tuple[list[str], dict[str, str]]:
    if not url.database:
        raise BackupError("DB_URL ichida baza nomi ko'rsatilmagan")
    args = ["--dbname", url.database]
    if url.host:
        args += ["--host", url.host]
    if url.port:
        args += ["--port", str(url.port)]
    if url.username:
        args += ["--username", url.username]

    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    sslmode = url.query.get("sslmode") or url.query.get("ssl")
    if sslmode:
        sslmode_value = str(sslmode).lower()
        env["PGSSLMODE"] = {
            "true": "require",
            "false": "disable",
        }.get(sslmode_value, sslmode_value)
    return args, env


def _run(command: list[str], env: dict[str, str]) -> None:
    executable = command[0]
    if shutil.which(executable) is None:
        raise BackupError(f"{executable} topilmadi. PostgreSQL client paketini o'rnating")
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "noma'lum xato").strip()
        raise BackupError(f"{executable} xatosi: {details}")


def create_backup(*, reason: str = "pre_migrate", directory: Path = DUMPS_DIR) -> Path:
    """Custom-format dump yaratadi; muvaffaqiyatsiz fayl yakuniy nomga o'tmaydi."""
    directory.mkdir(parents=True, exist_ok=True)
    number = _next_number(directory)
    stamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y%m%d_%H%M%S")
    safe_reason = re.sub(r"[^a-z0-9_]+", "_", reason.lower()).strip("_")
    suffix = f"_{safe_reason}" if safe_reason else ""
    target = directory / f"backup_{number:04d}_{stamp}{suffix}.dump"
    partial = directory / f".{target.name}.partial"

    url = make_url(DB_URL)
    options, env = _postgres_options(url)
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(partial),
        *options,
    ]
    try:
        _run(command, env)
        if not partial.is_file() or partial.stat().st_size == 0:
            raise BackupError("pg_dump bo'sh fayl yaratdi")
        partial.replace(target)
        target.chmod(0o600)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return target


def restore_backup(path: Path) -> None:
    """Tanlangan custom-format dumpni joriy DB_URL bazasiga tiklaydi."""
    if not path.is_file() or not BACKUP_RE.match(path.name):
        raise BackupError(f"Yaroqli dump fayli emas: {path}")
    url = make_url(DB_URL)
    options, env = _postgres_options(url)
    command = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        *options,
        str(path),
    ]
    _run(command, env)
