"""Tests for preview URI parsing — the QR payload contract."""

import os
import sys
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from app.config import PREVIEW_PROTOCOL_VERSION, RENDERER_PROTOCOL_VERSION  # noqa: E402
from app.preview.models import Endpoint  # noqa: E402
from app.preview.uri import (  # noqa: E402
    PreviewUriError, normalise_uri, parse_preview_uri,
)


def build_uri(**overrides) -> str:
    params = {
        "host": "192.168.1.20",
        "port": "8597",
        "session": "abc-123",
        "token": "s3cret-token",
        "protocol": str(PREVIEW_PROTOCOL_VERSION),
        "renderer": str(RENDERER_PROTOCOL_VERSION),
        "project": "local.deadbeef",
        "name": "My Project",
    }
    params.update({k: str(v) for k, v in overrides.items()
                   if v is not None})
    for key, value in list(overrides.items()):
        if value is None:
            params.pop(key, None)
    return "pydrud://preview/connect?" + urllib.parse.urlencode(params)


class TestPreviewUri(unittest.TestCase):
    def test_parses_a_valid_uri(self):
        target = parse_preview_uri(build_uri())
        self.assertEqual(target.host, "192.168.1.20")
        self.assertEqual(target.port, 8597)
        self.assertEqual(target.session_id, "abc-123")
        self.assertEqual(target.token, "s3cret-token")
        self.assertEqual(target.project_name, "My Project")
        self.assertEqual(target.describe(), "192.168.1.20:8597")

    def test_roundtrips_urlencoded_names(self):
        target = parse_preview_uri(build_uri(name="My Fancy Project & Co"))
        self.assertEqual(target.project_name, "My Fancy Project & Co")

    def test_rejects_wrong_scheme(self):
        with self.assertRaises(PreviewUriError) as ctx:
            parse_preview_uri("https://preview/connect?host=x")
        self.assertEqual(ctx.exception.code, "invalid_uri")

    def test_rejects_wrong_authority(self):
        with self.assertRaises(PreviewUriError):
            parse_preview_uri(
                "pydrud://other/connect?" + urllib.parse.urlencode(
                    {"host": "h", "port": "1", "session": "s", "token": "t",
                     "protocol": "1", "renderer": "2"}))

    def test_rejects_missing_parameter(self):
        for missing in ("host", "port", "session", "token", "protocol",
                        "renderer"):
            with self.assertRaises(PreviewUriError) as ctx:
                parse_preview_uri(build_uri(**{missing: None}))
            self.assertEqual(ctx.exception.code, "invalid_uri",
                             msg=f"missing {missing}")

    def test_rejects_preview_protocol_mismatch(self):
        with self.assertRaises(PreviewUriError) as ctx:
            parse_preview_uri(build_uri(protocol=2))
        self.assertEqual(ctx.exception.code, "unsupported_version")

    def test_rejects_renderer_protocol_mismatch(self):
        with self.assertRaises(PreviewUriError) as ctx:
            parse_preview_uri(build_uri(renderer=1))
        self.assertEqual(ctx.exception.code, "unsupported_renderer")

    def test_rejects_unconnectable_host(self):
        for host in ("0.0.0.0", "::", "bad host", "host/slash"):
            with self.assertRaises(PreviewUriError, msg=host):
                parse_preview_uri(build_uri(host=host))

    def test_rejects_bad_port(self):
        for port in ("0", "99999", "abc"):
            with self.assertRaises(PreviewUriError, msg=port):
                parse_preview_uri(build_uri(port=port))

    def test_accepts_ipv6_and_hostnames(self):
        self.assertEqual(parse_preview_uri(
            build_uri(host="fe80::1")).host, "fe80::1")
        self.assertEqual(parse_preview_uri(
            build_uri(host="dev.local")).host, "dev.local")

    def test_normalise_strips_noise(self):
        noisy = "  'pydrud://preview/connect?host=h'  "
        self.assertTrue(normalise_uri(noisy).startswith("pydrud://"))
        self.assertEqual(normalise_uri(""), "")
        self.assertEqual(normalise_uri(None), "")

    def test_normalise_restores_scheme(self):
        trimmed = "preview/connect?host=h"
        self.assertEqual(normalise_uri(trimmed), "pydrud://preview/connect?host=h")


class TestEndpoint(unittest.TestCase):
    def test_describe(self):
        endpoint = Endpoint(host="10.0.0.5", port=8597, session_id="s",
                            token="t")
        self.assertEqual(endpoint.describe(), "10.0.0.5:8597")


if __name__ == "__main__":
    unittest.main()
