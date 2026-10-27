"""Run inside the Home Assistant image against its installed APIs."""

import asyncio
import importlib
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import probatio
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import llm

sys.path.insert(0, sys.argv.pop(1))
bridge = importlib.import_module("custom_components.anam_assist")


class Connection:
    user = SimpleNamespace(id="test-user", is_admin=True)

    def send_result(self, mid, result=None):
        self.result = result

    def send_error(self, mid, code, message):
        self.result = {"error": code, "message": message}


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = Connection()
        self.session = {
            "connection": self.connection,
            "expires": time.monotonic() + 30,
            "allow_control": False,
            "calls": {},
            "lock": asyncio.Lock(),
            "tools": bridge.tool_bindings(bridge.READ_TOOLS | bridge.WRITE_TOOLS),
        }
        self.hass = SimpleNamespace(
            data={"anam_assist": {"sessions": {"session": self.session}}}
        )
        self.tool = SimpleNamespace(
            name="GetLiveContext", parameters=probatio.Schema({})
        )
        self.api = SimpleNamespace(
            tools=[self.tool],
            async_call_tool=AsyncMock(
                return_value=llm.ToolResult(data={"temperature": 21})
            ),
        )
        self.handler = bridge.ws_tool.__wrapped__.__wrapped__
        self.msg = {
            "id": 1,
            "bridge_id": "session",
            "call_id": "call",
            "name": "GetLiveContext",
            "arguments": {},
        }

    async def call(self):
        with patch.object(bridge, "get_api", AsyncMock(return_value=self.api)):
            message = dict(self.msg)
            message["name"] = next(
                (
                    alias
                    for alias, original in self.session["tools"].items()
                    if original == message["name"]
                ),
                message["name"],
            )
            await self.handler(self.hass, self.connection, message)

    async def test_current_ha_namespaced_tool(self):
        self.msg["name"] = self.tool.name = "homeassistant__GetLiveContext"
        await self.call()
        self.assertFalse(self.connection.result["error"])

    async def test_write_cannot_unlock_via_turn_on(self):
        self.session["allow_control"] = True
        self.msg["name"] = self.tool.name = "intent__HassTurnOn"
        self.tool.parameters = probatio.Schema({probatio.Optional("domain"): [str]})
        self.msg["arguments"] = {"domain": ["lock"]}
        await self.call()
        self.assertTrue(self.connection.result["error"])
        self.api.async_call_tool.assert_not_called()

    async def test_write_defaults_to_safe_domains(self):
        self.session["allow_control"] = True
        self.msg["name"] = self.tool.name = "intent__HassTurnOn"
        await self.call()
        args = self.api.async_call_tool.call_args[0][0].tool_args
        self.assertEqual(args["domain"], ["light"])

    async def test_queued_request_expires_without_execution(self):
        await self.session["lock"].acquire()
        real_timeout = asyncio.timeout
        try:
            with patch.object(bridge.asyncio, "timeout", lambda _: real_timeout(0.01)):
                await self.call()
        finally:
            self.session["lock"].release()
        self.assertEqual(self.connection.result["error"], "tool_timeout")
        self.api.async_call_tool.assert_not_called()

    async def test_read_returns_real_result(self):
        await self.call()
        self.assertEqual(
            self.connection.result, {"error": False, "data": {"temperature": 21}}
        )

    async def test_read_only_denies_write(self):
        self.msg["name"] = "HassTurnOn"
        await self.call()
        self.assertEqual(self.connection.result["error"], "tool_failed")
        self.api.async_call_tool.assert_not_called()

    async def test_replay_does_not_repeat_action(self):
        await self.call()
        await self.call()
        self.api.async_call_tool.assert_awaited_once()

    async def test_reused_id_cannot_change_arguments(self):
        await self.call()
        self.msg["arguments"] = {"new": True}
        await self.call()
        self.assertEqual(self.connection.result["error"], "tool_failed")

    async def test_other_connection_denied(self):
        self.connection = Connection()
        await self.call()
        self.assertEqual(self.connection.result["error"], "tool_failed")

    async def test_expired_denied(self):
        self.session["expires"] = 0
        await self.call()
        self.assertEqual(self.connection.result["error"], "tool_failed")

    async def test_unknown_tool_denied_even_with_control(self):
        self.session["allow_control"] = True
        self.msg["name"] = "HassUnlock"
        await self.call()
        self.api.async_call_tool.assert_not_called()

    async def test_timeout_cached(self):
        self.api.async_call_tool.side_effect = TimeoutError()
        await self.call()
        await self.call()
        self.assertTrue(self.connection.result["error"])
        self.api.async_call_tool.assert_awaited_once()

    async def test_bad_arguments_rejected(self):
        self.msg["arguments"] = {"unexpected": "value"}
        await self.call()
        self.assertTrue(self.connection.result["error"])
        self.api.async_call_tool.assert_not_called()

    async def test_session_stopped_during_api_lookup_cannot_execute(self):
        async def stop_during_lookup(*args):
            self.hass.data["anam_assist"]["sessions"].clear()
            return self.api

        with patch.object(bridge, "get_api", stop_during_lookup):
            await self.handler(
                self.hass,
                self.connection,
                {
                    **self.msg,
                    "name": next(iter(bridge.tool_bindings(["GetLiveContext"]))),
                },
            )
        self.api.async_call_tool.assert_not_called()
        self.assertTrue(self.connection.result["error"])

    async def test_scene_and_switch_control_denied(self):
        self.session["allow_control"] = True
        self.msg["name"] = self.tool.name = "intent__HassTurnOn"
        self.tool.parameters = probatio.Schema({probatio.Optional("domain"): [str]})
        for domain in ["scene", "switch"]:
            self.msg["call_id"] = domain
            self.msg["arguments"] = {"domain": [domain]}
            await self.call()
            self.assertTrue(self.connection.result["error"])
        self.api.async_call_tool.assert_not_called()

    async def test_large_input_denied(self):
        self.msg["arguments"] = {"value": "x" * 20000}
        await self.call()
        self.assertEqual(self.connection.result["error"], "tool_failed")
        self.api.async_call_tool.assert_not_called()

    async def test_deep_input_denied(self):
        value = {}
        for _ in range(10):
            value = {"nested": value}
        self.msg["arguments"] = value
        await self.call()
        self.assertEqual(self.connection.result["error"], "tool_failed")
        self.api.async_call_tool.assert_not_called()

    def test_distinct_names_do_not_collapse(self):
        bindings = bridge.tool_bindings(["catalog__lookup", "catalog_lookup"])
        self.assertEqual(len(bindings), 2)
        self.assertTrue(
            all("__" not in alias and len(alias) <= 64 for alias in bindings)
        )

    def test_duplicate_names_fail_closed(self):
        with self.assertRaises(HomeAssistantError):
            bridge.tool_bindings(["same", "same"])

    def test_websocket_commands_require_admin(self):
        connection = SimpleNamespace(user=SimpleNamespace(is_admin=False))
        for handler in (
            bridge.ws_info,
            bridge.ws_start,
            bridge.ws_tool,
            bridge.ws_stop,
        ):
            with self.assertRaises(Unauthorized):
                handler(self.hass, connection, {"id": 1})

    def test_portrait_is_default(self):
        self.assertEqual(bridge.session_options()["videoWidth"], 768)
        self.assertEqual(bridge.session_options()["videoHeight"], 1152)
        self.assertNotIn("videoWidth", bridge.session_options("landscape"))


if __name__ == "__main__":
    unittest.main()
