"""Synthetic boundary tests; no credentials, network or physical devices."""

import importlib
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from homeassistant.exceptions import HomeAssistantError

sys.path.insert(0, sys.argv.pop(1))
api = importlib.import_module("custom_components.anam_assist.api")
security = importlib.import_module("custom_components.anam_assist.security")


class Response:
    def __init__(self, status=200, chunks=()):
        self.status = status
        self.chunks = chunks
        self.content = self
        self.read_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk


class SecurityTests(unittest.IsolatedAsyncioTestCase):
    def test_nonfinite_numbers_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(HomeAssistantError):
                security.validate_arguments({"brightness": value})

    def test_non_json_types_rejected(self):
        for value in ({1: "value"}, {"value": object()}, {"value": (1, 2)}):
            with self.subTest(value=value), self.assertRaises(HomeAssistantError):
                security.validate_arguments(value)

    def test_broad_container_rejected(self):
        with self.assertRaises(HomeAssistantError):
            security.validate_arguments({"values": [0] * 513})

    def test_json_arguments_accepted(self):
        security.validate_arguments(
            {
                "name": "Example",
                "domain": ["light"],
                "value": 0.5,
                "on": True,
                "x": None,
            }
        )

    def test_malformed_persona_rejected(self):
        for value in (
            {"avatar": "unexpected"},
            {"avatar": {"id": 123}, "voice": {"id": "voice"}, "llmId": "llm"},
        ):
            with self.subTest(value=value), self.assertRaises(HomeAssistantError):
                api.persona_config(value)

    async def request(self, response):
        session = SimpleNamespace(request=Mock(return_value=response))
        with patch.object(api, "async_get_clientsession", return_value=session):
            result = await api.request(
                object(), "synthetic-secret", "/auth/session-token", {}
            )
        self.assertFalse(session.request.call_args.kwargs["allow_redirects"])
        return result

    async def test_json_response(self):
        self.assertEqual(
            await self.request(Response(chunks=[b'{"ok":', b"true}"])), {"ok": True}
        )

    async def test_oversized_response_stops_reading(self):
        response = Response(chunks=[b"x" * 65536] * 18)
        with self.assertRaisesRegex(HomeAssistantError, "oversized"):
            await self.request(response)
        self.assertEqual(response.read_count, 17)

    async def test_error_bodies_never_read(self):
        for status in (301, 401, 403, 500):
            response = Response(status=status, chunks=[b"synthetic-secret"])
            with (
                self.subTest(status=status),
                self.assertRaises(HomeAssistantError) as raised,
            ):
                await self.request(response)
            self.assertNotIn("synthetic-secret", str(raised.exception))
            self.assertEqual(response.read_count, 0)

    async def test_invalid_response_does_not_echo_body(self):
        for body in (b"synthetic-secret", json.dumps(["synthetic-secret"]).encode()):
            with (
                self.subTest(body=body),
                self.assertRaises(HomeAssistantError) as raised,
            ):
                await self.request(Response(chunks=[body]))
            self.assertNotIn("synthetic-secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
