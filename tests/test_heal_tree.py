import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import heal_tree


class HealTreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "docs").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_alert_state_restores_origin_instead_of_resetting(self):
        path = self.root / "data" / "alert_state.json"
        path.write_text('<<<<<<< ours\n{"sig":"new"}\n=======\n{}\n>>>>>>> theirs\n')
        good = json.dumps({"sig": "delivered", "sends_today": {"count": 2}}).encode()
        with mock.patch.object(heal_tree, "_origin_blob", return_value=good):
            healed = heal_tree.heal_tree(self.root)
        self.assertEqual(json.loads(path.read_text())["sig"], "delivered")
        self.assertTrue(any("restored from origin/main" in item for item in healed))

    def test_alert_state_fails_closed_when_origin_unavailable(self):
        path = self.root / "data" / "alert_state.json"
        original = b"not-json"
        path.write_bytes(original)
        with mock.patch.object(
            heal_tree, "_origin_blob", side_effect=RuntimeError("offline")
        ):
            with self.assertRaisesRegex(RuntimeError, "offline"):
                heal_tree.heal_tree(self.root)
        self.assertEqual(path.read_bytes(), original)

    def test_predictions_log_unions_as_strict_csv_by_composite_key(self):
        path = self.root / "data" / "predictions_log.csv"
        h = heal_tree.PREDICTION_FIELDS
        row1 = ["2026-08-03T10:00:00Z", "2026-08-03 12:00"] + [""] * 11
        row2 = ["2026-08-03T11:00:00Z", "2026-08-03 12:00"] + [""] * 11
        lines = [
            ",".join(h),
            "<<<<<<< ours",
            ",".join(row1),
            "=======",
            ",".join(row1),
            ",".join(row2),
            ">>>>>>> theirs",
        ]
        path.write_text("\n".join(lines) + "\n")
        healed = heal_tree.heal_tree(self.root)
        with path.open(newline="") as f:
            rows = list(csv.reader(f, strict=True))
        self.assertEqual(rows, [h, row1, row2])
        self.assertIn("CSV-unioned (2 rows)", healed[0])

    def test_marked_docs_artifact_is_restored_not_deleted(self):
        path = self.root / "docs" / "archive.html"
        path.write_text("<<<<<<< ours\nbad\n=======\nworse\n>>>>>>> theirs\n")
        with mock.patch.object(
            heal_tree, "_origin_blob", return_value=b"<html>known good</html>\n"
        ):
            healed = heal_tree.heal_tree(self.root)
        self.assertEqual(path.read_text(), "<html>known good</html>\n")
        self.assertTrue(any("docs: restored" in item for item in healed))


if __name__ == "__main__":
    unittest.main()
