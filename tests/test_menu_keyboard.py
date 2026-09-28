import unittest

from db.models import MenuItem
from keyboards.user_kb import _menu_rows


def item(title: str, buttons_per_row: int) -> MenuItem:
    return MenuItem(title=title, buttons_per_row=buttons_per_row)


def row_titles(items: list[MenuItem]) -> list[list[str]]:
    return [[button.text for button in row] for row in _menu_rows(items)]


class MenuRowsTest(unittest.TestCase):
    def test_two_pairable_buttons_share_a_row(self) -> None:
        items = [item("A", 2), item("B", 2)]

        self.assertEqual(row_titles(items), [["A", "B"]])

    def test_one_then_two_stay_on_separate_rows(self) -> None:
        items = [item("A", 1), item("B", 2)]

        self.assertEqual(row_titles(items), [["A"], ["B"]])

    def test_one_two_one_all_stay_on_separate_rows(self) -> None:
        items = [item("A", 1), item("B", 2), item("C", 1)]

        self.assertEqual(row_titles(items), [["A"], ["B"], ["C"]])

    def test_pairs_are_built_only_from_adjacent_two_buttons(self) -> None:
        items = [
            item("A", 2),
            item("B", 2),
            item("C", 1),
            item("D", 2),
            item("E", 2),
        ]

        self.assertEqual(row_titles(items), [["A", "B"], ["C"], ["D", "E"]])


if __name__ == "__main__":
    unittest.main()
