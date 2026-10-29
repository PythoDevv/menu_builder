import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.engine import make_url

from db_backup import _postgres_options, list_backups
import restore


class BackupFilesTest(unittest.TestCase):
    def test_numbered_backups_are_listed_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            directory = Path(raw_dir)
            older = directory / "backup_0002_20261005_120000_pre_migrate.dump"
            newer = directory / "backup_0010_20261005_130000_pre_restore.dump"
            ignored = directory / "notes.txt"
            for path in (older, newer, ignored):
                path.touch()

            self.assertEqual(list_backups(directory), [newer, older])

    def test_password_is_passed_via_environment_not_command_arguments(self) -> None:
        url = make_url("postgresql+asyncpg://user:secret@db.example:5433/app")

        args, env = _postgres_options(url)

        self.assertNotIn("secret", args)
        self.assertEqual(env["PGPASSWORD"], "secret")
        self.assertEqual(
            args,
            ["--dbname", "app", "--host", "db.example", "--port", "5433", "--username", "user"],
        )

    def test_restore_enter_selects_latest_and_takes_safety_backup(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            latest = Path(raw_dir) / "backup_0002_20261005_130000_pre_migrate.dump"
            safety = Path(raw_dir) / "backup_0003_20261005_140000_pre_restore.dump"
            latest.write_bytes(b"dump")
            safety.write_bytes(b"safety")

            with (
                patch.object(restore, "list_backups", return_value=[latest]),
                patch("builtins.input", side_effect=["", "RESTORE"]),
                patch.object(restore, "create_backup", return_value=safety) as create,
                patch.object(restore, "restore_backup") as run_restore,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(restore.main(), 0)

            create.assert_called_once_with(reason="pre_restore")
            run_restore.assert_called_once_with(latest)

    def test_restore_rejects_zero_selection(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            latest = Path(raw_dir) / "backup_0001_20261005_120000_pre_migrate.dump"
            latest.write_bytes(b"dump")
            with (
                patch.object(restore, "list_backups", return_value=[latest]),
                patch("builtins.input", return_value="0"),
                patch.object(restore, "restore_backup") as run_restore,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(restore.main(), 1)
            run_restore.assert_not_called()


if __name__ == "__main__":
    unittest.main()
