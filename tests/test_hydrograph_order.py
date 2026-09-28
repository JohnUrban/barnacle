"""Round 07 R4: the event hydrograph decides each range whisker from THAT
record's own basis, so the set of whiskers is invariant to ledger row order
(no ledger reordering happens; the test permutes an in-memory copy)."""
import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "assets/observations/2026-09-27/analysis/event10_hydrographs.py"


def _load():
    spec = importlib.util.spec_from_file_location("event10_hydrographs", PATH)
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


class HydrographOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load()
        cls.rows = cls.m.ledger_rows()
        cls.window = ("2026-09-26 04:00", "2026-09-26 13:30")   # Sep 26 AM panel

    def _bars(self, rows):
        tape, _strip = self.m.gather(rows, *self.window)
        return sorted((str(b[0]), round(b[1], 3), round(b[2], 3))
                      for b in (self.m.range_bar(rec) for rec in tape) if b)

    def test_basis_travels_with_each_record(self):
        tape, _ = self.m.gather(self.rows, *self.window)
        self.assertTrue(tape)
        self.assertTrue(all(len(rec) == 9 for rec in tape))
        self.assertTrue(all(rec[8] in ("stated", "stated_landmarks", "unquantified", "none")
                            for rec in tape))

    def test_range_bars_are_order_invariant(self):
        base = self._bars(self.rows)
        self.assertGreaterEqual(len(base), 2)
        # Codex's probe: move the approximate/unquantified row 221 (12:52 curb -0.4) last
        target = self.rows[219]
        self.assertEqual(target[1]["observed_depth_in"], "-0.4")
        moved = [x for x in self.rows if x is not target] + [target]
        self.assertEqual(self._bars(moved), base)
        self.assertEqual(self._bars(list(reversed(self.rows))), base)

    def test_unquantified_record_never_earns_a_bar(self):
        tape, _ = self.m.gather(self.rows, *self.window)
        for rec in tape:
            if rec[8] == "unquantified":
                self.assertIsNone(self.m.range_bar(rec))

    def test_full_figure_whisker_count_matches_gather(self):
        from matplotlib.axes import Axes
        from matplotlib.figure import Figure
        from unittest import mock
        expected = 0
        for eid, _title, a, b, _note in self.m.TIDES:
            tape, _ = self.m.gather(self.rows, a, b)
            expected += sum(1 for rec in tape if self.m.range_bar(rec))
        drawn = []
        original = Axes.plot

        def spy(ax, *args, **kwargs):
            if kwargs.get("color") == "#b45309" and kwargs.get("lw") == 1.6:
                drawn.append(args)
            return original(ax, *args, **kwargs)
        with mock.patch.object(Axes, "plot", spy), mock.patch.object(Figure, "savefig"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.m.main()
        self.assertEqual(len(drawn), expected)
        self.assertEqual(len(drawn), 6)


if __name__ == "__main__":
    unittest.main()
