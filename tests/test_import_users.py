import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_users import load_users


class LoadUsersTests(unittest.TestCase):
    def _load(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "users.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_users(path)

    def test_valid_users_are_normalized(self) -> None:
        users = self._load(
            [
                {
                    "tg_id": 123456789,
                    "full_name": "  Test User  ",
                    "username": "@test_user",
                },
                {"tg_id": 987654321, "full_name": "No Username", "username": None},
            ]
        )

        self.assertEqual(
            [
                {
                    "tg_id": 123456789,
                    "full_name": "Test User",
                    "username": "test_user",
                    "is_active": True,
                },
                {
                    "tg_id": 987654321,
                    "full_name": "No Username",
                    "username": None,
                    "is_active": True,
                },
            ],
            users,
        )

    def test_duplicate_tg_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate tg_id"):
            self._load(
                [
                    {"tg_id": 123, "full_name": "First", "username": None},
                    {"tg_id": 123, "full_name": "Second", "username": None},
                ]
            )

    def test_invalid_user_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid tg_id"):
            self._load([{"tg_id": "123", "full_name": "User", "username": None}])


if __name__ == "__main__":
    unittest.main()
