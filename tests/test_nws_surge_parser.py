"""NWS CFW parser: the Sandy Hook tide table lives in the raw product,
not in the alerts API description (first real event, 2026-09-23)."""

import datetime as dt
import unittest
from pathlib import Path
from unittest import mock

from forecast import nws_surge_parser as p

FIXTURE = Path(__file__).parent / "fixtures" / "cfw_phi_20260923_0828z.txt"

# Verbatim api.weather.gov `description` of CF.Y.0021 (sent 2026-09-23
# 04:28 EDT): the narrative only, no table.
ALERT_DESCRIPTION = """\
* WHAT...For the High Rip Current Risk, dangerous rip currents.
For the High Surf Advisory, large breaking waves of 6 to 12
feet expected in the surf zone. For the Coastal Flood
Advisory, up to one foot of inundation above ground level
expected in low- lying areas near shorelines and tidal
waterways.

* WHERE...Eastern Monmouth.

* WHEN...For the High Rip Current Risk, through Saturday
evening. For the High Surf Advisory, until 2 PM EDT Saturday.
For the Coastal Flood Advisory, from 4 PM this afternoon to 2
AM EDT Saturday.

* IMPACTS...At this level, flooding begins on the most
vulnerable roads in coastal and bayside communities, and along
inland tidal waterways. Some partial or full road closures are
possible.

* ADDITIONAL DETAILS... Localized moderate tidal flooding impacts
cannot be ruled out. Widespread minor tidal flooding could
continue into the weekend.
"""

ALERT = {
    "event": "Coastal Flood Advisory",
    "sent": "2026-09-23T04:28:00-04:00",
    "description": ALERT_DESCRIPTION,
}

PRODUCT_0828Z = {"id": "a06e2985", "issuanceTime": "2026-09-23T08:28:00+00:00",
                 "issuingOffice": "KPHI", "wmoCollectiveId": "WHUS41"}
PRODUCT_0153Z = {"id": "c1cc4985", "issuanceTime": "2026-09-23T01:53:00+00:00",
                 "issuingOffice": "KPHI", "wmoCollectiveId": "WHUS41"}
PRODUCT_STALE = {"id": "stale", "issuanceTime": "2026-09-21T19:27:00+00:00",
                 "issuingOffice": "KPHI", "wmoCollectiveId": "WHUS41"}

EXPECTED_ROWS = [
    # (when, total MLLW, departure, category) — NJZ014 segment, 08:28Z
    ("2026-09-23 06:00", 5.9, 1.4, "None"),
    ("2026-09-23 18:00", 6.9, 1.8, "Minor"),
    ("2026-09-24 07:00", 6.4, 1.6, "None"),
    ("2026-09-24 19:00", 7.2, 1.9, "Minor"),
    ("2026-09-25 08:00", 7.2, 2.1, "Minor"),
    ("2026-09-25 19:00", 7.5, 2.2, "Minor"),
]


def _fixture():
    return FIXTURE.read_text()


class ParseTests(unittest.TestCase):
    def assertRows(self, rows, expected):
        self.assertEqual(len(rows), len(expected))
        for row, (w, t, d, c) in zip(rows, expected):
            self.assertEqual(row["when"].strftime("%Y-%m-%d %H:%M"), w)
            self.assertAlmostEqual(row["total_mllw_ft"], t, places=2)
            self.assertAlmostEqual(row["departure_ft"], d, places=2)
            self.assertEqual(row["cat"], c)

    def test_alert_description_carries_no_table(self):
        rows, msg = p.parse_tide_projections(ALERT_DESCRIPTION)
        self.assertEqual(rows, [])
        self.assertEqual(msg, "No Sandy Hook section in product text")

    def test_raw_product_yields_sandy_hook_rows(self):
        rows, msg = p.parse_tide_projections(_fixture())
        self.assertEqual(msg, "ok")
        self.assertRows(rows, EXPECTED_ROWS)

    def test_block_stops_at_next_gauge_not_at_delimiter(self):
        # Watson Creek at Manasquan follows Sandy Hook inside the same
        # `&&` block; its 23/06 PM row is 6.0 ft and must not leak in.
        block = p.find_station_block(_fixture())
        self.assertIn("Sandy Hook Bay at Sandy Hook", block)
        self.assertNotIn("Watson Creek", block)
        rows, _ = p.parse_tide_projections(_fixture())
        self.assertEqual([r["total_mllw_ft"] for r in rows],
                         [5.9, 6.9, 6.4, 7.2, 7.2, 7.5])

    def test_issuance_fallback_when_header_is_absent(self):
        text = _fixture()
        block = text[text.index("Sandy Hook Bay at Sandy Hook"):]
        block = block[:block.index("Watson Creek")]
        self.assertIsNone(p.find_issuance_date(block))
        rows, msg = p.parse_tide_projections(block)
        self.assertEqual(rows, [])
        self.assertIn("issuance date", msg)
        rows, msg = p.parse_tide_projections(block, issued=(9, 23, 2026))
        self.assertRows(rows, EXPECTED_ROWS)

    def test_bare_sandy_hook_prose_is_not_a_gauge_header(self):
        text = ("...WHERE...along Sandy Hook Bay and the Raritan Bay shore...\n"
                "* WHEN...tonight.\n")
        self.assertIsNone(p.find_station_block(text))

    def test_legacy_inline_layout_still_parses(self):
        rows, msg = p.parse_tide_projections(p.SAMPLE_TEXT)
        self.assertEqual(msg, "ok")
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[1]["cat"], "Moderate")

    def test_month_rollover_dates_next_month(self):
        text = ("1030 PM EDT Tue Sep 29 2026\n\n"
                "Sandy Hook Bay at Sandy Hook\n"
                "MLLW Categories - Minor 6.7 ft, Moderate 7.7 ft, Major 8.7 ft\n"
                " 30/07 PM     7.0        1.8        1.9      Minor\n"
                " 01/08 AM     7.1        1.9        2.0      Minor\n")
        rows, _ = p.parse_tide_projections(text)
        self.assertEqual([r["when"].date().isoformat() for r in rows],
                         ["2026-09-30", "2026-10-01"])

    def test_issued_local_date_converts_utc_to_station_time(self):
        # 03:30Z on the 24th is still the 23rd in New Jersey (EDT).
        self.assertEqual(
            p.issued_local_date({"issuanceTime": "2026-09-24T03:30:00+00:00"}),
            (9, 23, 2026))


class ProductSelectionTests(unittest.TestCase):
    def test_alert_product_first_then_newest_within_age_window(self):
        newer_other_zone = {"id": "z", "issuanceTime": "2026-09-23T09:00:00+00:00"}
        ordered = p.select_candidate_products(
            [PRODUCT_STALE, PRODUCT_0153Z, newer_other_zone, PRODUCT_0828Z],
            [ALERT])
        self.assertEqual([x["id"] for x in ordered],
                         ["a06e2985", "z", "c1cc4985"])

    def test_no_alerts_means_newest_first_without_age_cut(self):
        ordered = p.select_candidate_products(
            [PRODUCT_STALE, PRODUCT_0828Z], [])
        self.assertEqual([x["id"] for x in ordered], ["a06e2985", "stale"])


class LiveEntryPointTests(unittest.TestCase):
    def test_not_active_when_no_coastal_flood_alert(self):
        with mock.patch.object(p, "get_active_coastal_flood", return_value=[]):
            active, rows, text, msg = p.get_surge_forecast()
        self.assertFalse(active)
        self.assertEqual(rows, [])
        self.assertIsNone(text)

    def test_raw_product_used_when_alert_text_lacks_table(self):
        fetched = []

        def fake_fetch(product_id):
            fetched.append(product_id)
            return _fixture()

        with mock.patch.object(p, "get_active_coastal_flood",
                               return_value=[ALERT]), \
                mock.patch.object(p, "list_cfw_products",
                                  return_value=[PRODUCT_0153Z, PRODUCT_0828Z]), \
                mock.patch.object(p, "fetch_product_text", side_effect=fake_fetch):
            active, rows, text, msg = p.get_surge_forecast()

        self.assertTrue(active)
        self.assertEqual(fetched, ["a06e2985"])   # the alert's own product
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[1]["total_mllw_ft"], 6.9)
        self.assertEqual(
            msg, "6 Sandy Hook rows from CFW KPHI issued 2026-09-23T08:28:00+00:00")
        self.assertIn("Sandy Hook Bay at Sandy Hook", text)

    def test_every_candidate_failure_is_named_when_no_table_found(self):
        with mock.patch.object(p, "get_active_coastal_flood",
                               return_value=[ALERT]), \
                mock.patch.object(p, "list_cfw_products",
                                  return_value=[PRODUCT_0828Z, PRODUCT_0153Z]), \
                mock.patch.object(p, "fetch_product_text",
                                  return_value=ALERT_DESCRIPTION):
            active, rows, text, msg = p.get_surge_forecast()

        self.assertTrue(active)
        self.assertEqual(rows, [])
        self.assertIn("alert text: No Sandy Hook section", msg)
        self.assertIn("CFW 2026-09-23T08:28:00+00:00: No Sandy Hook section", msg)
        self.assertIn("CFW 2026-09-23T01:53:00+00:00: No Sandy Hook section", msg)

    def test_product_list_failure_stays_active_and_is_reported(self):
        with mock.patch.object(p, "get_active_coastal_flood",
                               return_value=[ALERT]), \
                mock.patch.object(p, "list_cfw_products",
                                  side_effect=OSError("offline")):
            active, rows, _, msg = p.get_surge_forecast()
        self.assertTrue(active)
        self.assertEqual(rows, [])
        self.assertIn("CFW product list fetch failed: offline", msg)

    def test_one_bad_product_fetch_does_not_stop_the_search(self):
        def fake_fetch(product_id):
            if product_id == "a06e2985":
                raise OSError("502")
            return _fixture()

        with mock.patch.object(p, "get_active_coastal_flood",
                               return_value=[ALERT]), \
                mock.patch.object(p, "list_cfw_products",
                                  return_value=[PRODUCT_0828Z, PRODUCT_0153Z]), \
                mock.patch.object(p, "fetch_product_text", side_effect=fake_fetch):
            active, rows, _, msg = p.get_surge_forecast()
        self.assertEqual(len(rows), 6)
        self.assertIn("issued 2026-09-23T01:53:00+00:00", msg)


if __name__ == "__main__":
    unittest.main()
