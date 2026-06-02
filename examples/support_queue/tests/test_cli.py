from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from support_queue.cli import main


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "tickets.json"


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> str:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["--data", str(DATA_PATH), *args])
        self.assertEqual(exit_code, 0)
        return buffer.getvalue()

    def test_list_defaults_to_open_tickets(self) -> None:
        output = self.run_cli("list")

        self.assertIn("TCK-1001", output)
        self.assertIn("TCK-1002", output)
        self.assertIn("TCK-1004", output)
        self.assertNotIn("TCK-1003", output)

    def test_list_can_filter_by_priority(self) -> None:
        output = self.run_cli("list", "--priority", "urgent")

        self.assertIn("TCK-1004", output)
        self.assertNotIn("TCK-1001", output)

    def test_summary_prints_backlog_counts(self) -> None:
        output = self.run_cli("summary")

        self.assertEqual(output.strip(), "open=3 closed=1 urgent=1")


if __name__ == "__main__":
    unittest.main()

