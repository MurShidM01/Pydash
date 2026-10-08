"""The preview URI parser — Pydash's copy of the host's QR contract.

Every case the ``pydrud dev`` server would also refuse is covered here, so a
malformed or hostile code is rejected with the same machine-readable code on
both ends.
"""

import os
import sys
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from app.config import (  # noqa: E402
    PREVIEW_PROTOCOL_VERSION,
    RENDERER_PROTOCOL_VERSION,
)
from app.preview.models import Endpoint  # noqa: E402
from app.preview.uri import (  # noqa: E402
    PreviewUriError,
    build_uri,
    build_uri_from_endpoint,
    normalise_uri,
    parse_preview_uri,
)

_BASE = {
    "host": "192.168.1.20",
    "port": "8597",
    "session": "sess-1",
    "token": "tok-abc",
    "protocol": str(PREVIEW_PROTOCOL_VERSION),
    "renderer": str(RENDERER_PROTOCOL_VERSION),
    "project": "proj",
    "name": "Demo App",
}


def _raw(**overrides) -> str:
    """Compose a ``pydrud://`` URI with arbitrary query values."""
    query = dict(_BASE)
    query.update(overrides)
    return "pydrud://preview/connect?" + urllib.parse.urlencode(query)


class TestParsePreviewUri(unittest.TestCase):
    def test_parses_a_valid_code(self):
        target = parse_preview_uri(_raw())
        self.assertEqual(target.host, "192.168.1.20")
        self.assertEqual(target.port, 8597)
        self.assertEqual(target.session_id, "sess-1")
        self.assertEqual(target.token, "tok-abc")
        self.assertEqual(target.project_id, "proj")
        self.assertEqual(target.project_name, "Demo App")
        self.assertEqual(target.protocol_version, PREVIEW_PROTOCOL_VERSION)
        self.assertEqual(target.renderer_protocol_version,
                         RENDERER_PROTOCOL_VERSION)
        self.assertEqual(target.describe(), "192.168.1.20:8597")

    def test_rejects_anything_that_is_not_a_preview_uri(self):
        for bad in (
            "https://example.com/preview",
            "pydash://preview/connect?host=192.168.1.20",
            "pydrud://other/connect?host=192.168.1.20",
            "pydrud://preview/other?host=192.168.1.20",
            "just some text",
            "",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(PreviewUriError) as ctx:
                    parse_preview_uri(bad)
                self.assertEqual(ctx.exception.code, "invalid_uri")

    def test_rejects_a_missing_parameter(self):
        for name in ("host", "port", "session", "token", "protocol",
                     "renderer"):
            with self.subTest(missing=name):
                query = dict(_BASE)
                del query[name]
                uri = "pydrud://preview/connect?" + urllib.parse.urlencode(query)
                with self.assertRaises(PreviewUriError) as ctx:
                    parse_preview_uri(uri)
                self.assertEqual(ctx.exception.code, "invalid_uri")

    def test_rejects_a_duplicated_parameter(self):
        uri = _raw() + "&host=10.0.0.1"
        with self.assertRaises(PreviewUriError):
            parse_preview_uri(uri)

    def test_rejects_a_protocol_version_mismatch(self):
        with self.assertRaises(PreviewUriError) as ctx:
            parse_preview_uri(_raw(protocol="99"))
        self.assertEqual(ctx.exception.code, "unsupported_version")

    def test_rejects_a_renderer_version_mismatch(self):
        with self.assertRaises(PreviewUriError) as ctx:
            parse_preview_uri(_raw(renderer="99"))
        self.assertEqual(ctx.exception.code, "unsupported_renderer")

    def test_rejects_a_non_numeric_port(self):
        for port in ("abc", "", "70000", "0", "-1"):
            with self.subTest(port=port):
                with self.assertRaises(PreviewUriError) as ctx:
                    parse_preview_uri(_raw(port=port))
                self.assertEqual(ctx.exception.code, "invalid_uri")

    def test_rejects_an_unconnectable_host(self):
        for host in ("0.0.0.0", "::", "  ", "a b", "1.2.3.4/path"):
            with self.subTest(host=host):
                with self.assertRaises(PreviewUriError) as ctx:
                    parse_preview_uri(_raw(host=host))
                self.assertEqual(ctx.exception.code, "invalid_uri")

    def test_accepts_hostnames_and_bracketed_ipv6(self):
        self.assertEqual(parse_preview_uri(_raw(host="dev.local")).host,
                         "dev.local")
        self.assertEqual(parse_preview_uri(_raw(host="[fe80::1]")).host,
                         "fe80::1")


class TestNormaliseUri(unittest.TestCase):
    def test_strips_quotes_and_whitespace(self):
        self.assertEqual(normalise_uri('  "pydrud://x"  '), "pydrud://x")

    def test_restores_a_scheme_that_was_dropped_on_copy(self):
        self.assertEqual(
            normalise_uri("preview/connect?host=192.168.1.20"),
            "pydrud://preview/connect?host=192.168.1.20")

    def test_leaves_an_empty_string_alone(self):
        self.assertEqual(normalise_uri("   "), "")


class TestBuildUri(unittest.TestCase):
    def test_round_trips_through_the_parser(self):
        uri = build_uri(host="10.0.0.5", port=9000, session_id="s",
                        token="t", project_id="p", project_name="N")
        target = parse_preview_uri(uri)
        self.assertEqual(target.host, "10.0.0.5")
        self.assertEqual(target.port, 9000)
        self.assertEqual(target.project_name, "N")

    def test_round_trips_from_an_endpoint(self):
        endpoint = Endpoint(host="192.168.0.9", port=8597, session_id="sess",
                            token="tok", project_id="proj",
                            project_name="Demo")
        target = parse_preview_uri(build_uri_from_endpoint(endpoint))
        self.assertEqual(target.host, endpoint.host)
        self.assertEqual(target.port, endpoint.port)
        self.assertEqual(target.session_id, endpoint.session_id)
        self.assertEqual(target.token, endpoint.token)


if __name__ == "__main__":
    unittest.main()
