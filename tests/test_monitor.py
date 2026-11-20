"""Offline examples use fake Docker objects and HTTP responses."""

import io
import json
import unittest
from email.message import Message
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from demo_service import route
from monitor.checks import check_http, check_logs, check_state, error_lines
from monitor.cli import compose_container, http_url


def response(status, body, content_type="application/json"):
    result = Mock()
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    result.status = status
    result.headers = Message()
    result.headers["Content-Type"] = content_type
    result.read.return_value = body
    return result


class ContainerStateTests(unittest.TestCase):
    def test_running_and_healthy(self):
        self.assertTrue(check_state({"Status": "running", "Health": {"Status": "healthy"}}).passed)

    def test_exited_even_with_stale_health(self):
        self.assertFalse(check_state({"Status": "exited", "Health": {"Status": "healthy"}}).passed)

    def test_starting_is_not_healthy(self):
        self.assertFalse(check_state({"Status": "running", "Health": {"Status": "starting"}}).passed)

    def test_no_healthcheck_has_readable_result(self):
        result = check_state({"Status": "running"})
        self.assertFalse(result.passed)
        self.assertIn("health=missing", result.detail)

    def test_project_and_service_scope(self):
        client = Mock()
        container = client.containers.list.return_value = [Mock()]
        self.assertIs(compose_container(client, "my-lab", "demo"), container[0])
        container[0].reload.assert_called_once()
        client.containers.list.assert_called_once_with(all=True, filters={"label": [
            "com.docker.compose.project=my-lab",
            "com.docker.compose.service=demo",
            "com.docker.compose.oneoff=False",
        ]})

    def test_missing_or_ambiguous_container(self):
        for matches in ([], [Mock(), Mock()]):
            with self.subTest(matches=len(matches)):
                client = Mock()
                client.containers.list.return_value = matches
                with self.assertRaisesRegex(ValueError, f"found {len(matches)}"):
                    compose_container(client, "my-lab", "demo")


class LogTests(unittest.TestCase):
    def test_structured_and_plain_error_positions(self):
        raw = b'{"level":"info"}\n{"severity":" error "}\n  [CRITICAL] setup failed\nFATAL failure\n'
        self.assertEqual(error_lines(raw), [2, 3, 4])

    def test_warning_and_error_word_in_info_are_ignored(self):
        raw = b'{"level":"INFO","message":"error count is zero"}\nINFO no ERROR\nWARNING test\n'
        self.assertTrue(check_logs(raw).passed)

    def test_malformed_lines_and_non_strings(self):
        raw = b'{"level":1}\n["ERROR"]\n\xff\nerror trace\n'
        self.assertEqual(error_lines(raw), [4])

    def test_raw_log_messages_are_not_in_report(self):
        result = check_logs(b"ERROR private example message")
        self.assertFalse(result.passed)
        self.assertIn("1 error signature(s)", result.detail)
        self.assertNotIn("private example message", result.detail)


class HttpTests(unittest.TestCase):
    url = "http://127.0.0.1:8080/health"

    @patch("monitor.checks.build_opener")
    def test_good_readiness(self, build):
        build.return_value.open.return_value = response(200, b'{"status":"ok"}')
        self.assertTrue(check_http(self.url).passed)

    @patch("monitor.checks.build_opener")
    def test_wrong_body_is_rejected(self, build):
        for body in (b"not JSON", b'{"status":"starting"}', b'["ok"]'):
            with self.subTest(body=body):
                build.return_value.open.return_value = response(200, body)
                self.assertFalse(check_http(self.url).passed)

    @patch("monitor.checks.build_opener")
    def test_oversized_body_is_rejected(self, build):
        build.return_value.open.return_value = response(200, b'{"status":"ok"}' + b" " * 16_385)
        self.assertIn("16 KiB", check_http(self.url).detail)

    @patch("monitor.checks.build_opener")
    def test_non_json_content_type_is_rejected(self, build):
        build.return_value.open.return_value = response(200, b'{"status":"ok"}', "text/plain")
        self.assertFalse(check_http(self.url).passed)

    @patch("monitor.checks.build_opener")
    def test_non_200_codes_use_expected_value(self, build):
        for expected in (200, 404):
            with self.subTest(expected=expected):
                build.return_value.open.side_effect = HTTPError(
                    self.url, 404, "Not found", Message(), io.BytesIO()
                )
                self.assertEqual(check_http(self.url, expected).passed, expected == 404)

    @patch("monitor.checks.build_opener")
    def test_transport_error_is_a_failed_check(self, build):
        build.return_value.open.side_effect = URLError("example transport fault")
        result = check_http(self.url)
        self.assertFalse(result.passed)
        self.assertIn("URLError", result.detail)

    def test_rejects_non_http_and_embedded_credentials(self):
        import argparse
        for url in ("file:///tmp/log", "https://user:example@localhost/health"):
            with self.subTest(url=url), self.assertRaises(argparse.ArgumentTypeError):
                http_url(url)


class DemoTests(unittest.TestCase):
    def test_accepts_health_with_query(self):
        self.assertEqual(route("/health?probe=1"), (200, {"status": "ok", "service": "qa-demo"}))

    def test_unknown_route_is_404(self):
        self.assertEqual(route("/missing")[0], 404)
