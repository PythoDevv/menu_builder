import unittest
from unittest.mock import patch

from sqlalchemy.dialects import postgresql

from db.queries import get_contents


class _SessionSpy:
    def __init__(self) -> None:
        self.statement = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def scalars(self, statement):
        self.statement = statement
        return []


class ContentOrderTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_contents_orders_by_id(self) -> None:
        session = _SessionSpy()

        with patch("db.queries.session_maker", return_value=session):
            await get_contents(item_id=42)

        sql = str(
            session.statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertIn("ORDER BY contents.id", sql)
        self.assertNotIn("ORDER BY contents.position", sql)


if __name__ == "__main__":
    unittest.main()
