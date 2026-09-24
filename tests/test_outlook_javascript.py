"""Execute rendered chart scripts, not only their embedded JSON (2026-09-23)."""
import json
import re
import subprocess
import unittest

from forecast import flood_forecast_daily as ff  # facade initializes shared render imports
from forecast.outlook_page import render_outlook_page
from test_outlook import NOW, _build


class OutlookJavascriptTests(unittest.TestCase):
    def test_both_rendered_chart_scripts_initialize_with_fixture_data(self):
        forecast = {'outlook_7d': _build(), 'generated_utc': NOW.isoformat(),
                    'model_version': ff.CURRENT_MODEL_VERSION,
                    'forecast_schema_version': '1.0', 'input_health': {}}
        page = render_outlook_page(forecast)
        scripts = [s for s in re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', page, re.S)
                   if s.strip()]
        harness = """
const vm = require('node:vm');
const scripts = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const charts = [];
const context = vm.createContext({
  document: { getElementById: id => ({id}) },
  Chart: function(el, cfg) {
    charts.push({id: el.id, points: cfg.data.labels.length,
                 labels: cfg.data.datasets.map(d => d.label)});
  }
});
for (const script of scripts) vm.runInContext(script, context);
process.stdout.write(JSON.stringify(charts));
"""
        run = subprocess.run(['node', '-e', harness], input=json.dumps(scripts),
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        charts = {c['id']: c for c in json.loads(run.stdout)}
        self.assertEqual(set(charts), {'outlook-series-chart', 'outlook-peaks-chart'})
        self.assertGreater(charts['outlook-series-chart']['points'], 100)
        self.assertGreater(charts['outlook-peaks-chart']['points'], 7)
        self.assertIn("Burst scenario at this hour's tide (burst-capable hours)",
                      charts['outlook-series-chart']['labels'])
