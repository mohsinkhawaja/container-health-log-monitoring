"""End-to-end checks that connect to the Docker Engine and HTTP server."""

import json
import os
import subprocess
import sys
import unittest

from monitor.checks import check_http


@unittest.skipUnless(os.getenv("MONITOR_LIVE") == "1", "requires a running disposable Compose stack")
class LiveTests(unittest.TestCase):
    def setUp(self):
        self.base_url = f"http://127.0.0.1:{os.getenv('DEMO_PORT', '8080')}"

    def test_live_cli_reports_all_checks(self):
        result = subprocess.run(
            [sys.executable, "-m", "monitor.cli",
             "--project", os.getenv("MONITOR_PROJECT", "qa-health-lab"),
             "--url", f"{self.base_url}/health"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual({item["name"] for item in payload["checks"]},
                         {"container_state", "http", "container_logs"})

    def test_live_unknown_route_returns_404(self):
        check = check_http(f"{self.base_url}/missing", expected_code=404)
        self.assertTrue(check.passed, check.detail)
