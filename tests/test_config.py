"""Config-flow validation without network access or real credentials."""

import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import homeassistant  # noqa: F401  # Install HA's probatio adapter before voluptuous.

sys.path.insert(0, sys.argv.pop(1))
flow_module = importlib.import_module("custom_components.anam_assist.config_flow")


class ConfigTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = flow_module.AnamConfigFlow()
        self.flow.hass = SimpleNamespace()
        self.flow._async_current_entries = Mock(return_value=[])
        self.flow.async_show_form = Mock(side_effect=lambda **kw: kw)
        self.flow.async_create_entry = Mock(side_effect=lambda **kw: kw)
        self.flow.async_update_reload_and_abort = Mock(
            side_effect=lambda *args, **kw: kw
        )

    async def test_new_setup_validates_portrait_without_exposing_key(self):
        request = AsyncMock(return_value={"sessionToken": "short-lived-test-token"})
        with patch.object(flow_module, "request", request):
            result = await self.flow._configure(
                "user", {"api_key": "test-secret", "orientation": "portrait"}
            )
        self.assertEqual(result["data"]["orientation"], "portrait")
        self.assertEqual(request.call_args.args[3]["sessionOptions"]["videoWidth"], 768)

    async def test_reconfigure_keeps_key_and_updates_orientation(self):
        entry = SimpleNamespace(data={"api_key": "saved-test-secret"})
        with patch.object(
            flow_module, "request", AsyncMock(return_value={"sessionToken": "token"})
        ):
            result = await self.flow._configure(
                "reconfigure", {"orientation": "landscape"}, entry
            )
        self.assertEqual(result["data"]["api_key"], "saved-test-secret")
        self.flow.async_create_entry.assert_not_called()

    async def test_saved_key_not_in_form_defaults(self):
        result = await self.flow._configure(
            "reconfigure", None, SimpleNamespace(data={"api_key": "saved-test-secret"})
        )
        self.assertNotIn("saved-test-secret", str(result))
        self.assertNotIn("api_key", result["data_schema"]({}))

    async def test_invalid_key_has_specific_error(self):
        with patch.object(
            flow_module,
            "request",
            AsyncMock(side_effect=flow_module.InvalidAuth("secret upstream response")),
        ):
            result = await self.flow._configure("user", {"api_key": "test-secret"})
        self.assertEqual(result["errors"], {"base": "invalid_auth"})
        self.assertNotIn("secret", str(result))

    async def test_missing_token_never_saves_entry(self):
        with patch.object(flow_module, "request", AsyncMock(return_value={})):
            result = await self.flow._configure("user", {"api_key": "test-secret"})
        self.assertEqual(result["errors"], {"base": "cannot_connect"})
        self.flow.async_create_entry.assert_not_called()

    async def test_invalid_persona_never_contacts_provider(self):
        request = AsyncMock()
        with patch.object(flow_module, "request", request):
            result = await self.flow._configure(
                "user", {"api_key": "test-secret", "persona_id": "../unexpected"}
            )
        self.assertEqual(result["errors"], {"persona_id": "invalid_persona"})
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
