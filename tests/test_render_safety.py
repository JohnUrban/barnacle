import unittest

from forecast import flood_forecast_daily as ff


class RenderSafetyTests(unittest.TestCase):
    def test_external_nws_alert_text_is_html_escaped(self):
        forecast = {
            "pluvial_risk": {
                "level": "elevated",
                "nws_flood_alerts": [{
                    "event": '<img src=x onerror="boom">',
                    "severity": "Severe & urgent",
                    "headline": "Flood <script>alert(1)</script>",
                }],
            }
        }
        rendered = ff._render_pluvial_advisory_html(forecast)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("Severe &amp; urgent", rendered)


if __name__ == "__main__":
    unittest.main()
