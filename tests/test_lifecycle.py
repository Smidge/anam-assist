"""Exercise real HA flow results and lifecycle without credentials or a running home."""

import asyncio
import importlib
import sys
import tempfile
import unittest
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

sys.path.insert(0, sys.argv.pop(1))
bridge = importlib.import_module("custom_components.anam_assist")
flows = importlib.import_module("custom_components.anam_assist.config_flow")


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        self.hass.data[bridge.DOMAIN] = {"sessions": {}}
        self.flow = flows.AnamConfigFlow()
        self.flow.hass = self.hass
        self.flow.context = {"source": "user"}

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)
        self.directory.cleanup()

    def entry(self):
        entry = ConfigEntry(
            domain=bridge.DOMAIN,
            data={
                "api_key": "synthetic-key",
                "persona_id": "",
                "orientation": "portrait",
            },
            title="Anam Assist",
            version=1,
            minor_version=1,
            source="user",
            unique_id=None,
            options={},
            discovery_keys=MappingProxyType({}),
            subentries_data=None,
        )
        self.hass.config_entries._entries[entry.entry_id] = entry
        return entry

    async def test_real_form_and_create_result(self):
        form = await self.flow.async_step_user()
        self.assertEqual(form["type"], FlowResultType.FORM)
        validated = form["data_schema"]({"api_key": "synthetic-key"})
        self.assertEqual(validated["orientation"], "portrait")
        with patch.object(
            flows,
            "request",
            AsyncMock(return_value={"sessionToken": "synthetic-token"}),
        ):
            result = await self.flow.async_step_user(validated)
        self.assertEqual(result["type"], FlowResultType.CREATE_ENTRY)
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["data"]["api_key"], "synthetic-key")

    async def test_second_instance_aborts_without_provider_request(self):
        self.entry()
        with patch.object(flows, "request", AsyncMock()) as request:
            result = await self.flow.async_step_user({"api_key": "synthetic-key"})
        self.assertEqual(result["reason"], "single_instance_allowed")
        request.assert_not_called()

    async def test_reconfigure_updates_real_entry_and_schedules_reload(self):
        entry = self.entry()
        self.flow.context = {"source": "reconfigure", "entry_id": entry.entry_id}
        with (
            patch.object(
                flows, "request", AsyncMock(return_value={"sessionToken": "token"})
            ),
            patch.object(self.hass.config_entries, "async_schedule_reload") as reload,
        ):
            result = await self.flow.async_step_reconfigure(
                {"orientation": "landscape"}
            )
        self.assertEqual(result["type"], FlowResultType.ABORT)
        self.assertEqual(result["reason"], "reconfigure_successful")
        self.assertEqual(entry.data["api_key"], "synthetic-key")
        self.assertEqual(entry.data["orientation"], "landscape")
        reload.assert_called_once_with(entry.entry_id)

    async def test_reauth_updates_real_entry(self):
        entry = self.entry()
        self.flow.context = {"source": "reauth", "entry_id": entry.entry_id}
        form = await self.flow.async_step_reauth(entry.data)
        self.assertNotIn("synthetic-key", str(form))
        with (
            patch.object(
                flows, "request", AsyncMock(return_value={"sessionToken": "token"})
            ),
            patch.object(self.hass.config_entries, "async_schedule_reload"),
        ):
            result = await self.flow.async_step_reauth_confirm(
                {"api_key": "replacement-key"}
            )
        self.assertEqual(result["reason"], "reauth_successful")
        self.assertEqual(entry.data["api_key"], "replacement-key")

    async def test_unload_revokes_bridges_and_close_callbacks(self):
        connection = SimpleNamespace(subscriptions={1: Mock()})
        self.hass.data[bridge.DOMAIN].update(
            entry=self.entry(),
            sessions={"id": {"connection": connection, "subscription_id": 1}},
        )
        with patch.object(bridge.frontend, "async_remove_panel") as remove:
            self.assertTrue(await bridge.async_unload_entry(self.hass, None))
        self.assertFalse(connection.subscriptions)
        self.assertFalse(self.hass.data[bridge.DOMAIN]["sessions"])
        self.assertNotIn("entry", self.hass.data[bridge.DOMAIN])
        remove.assert_called_once_with(self.hass, "anam-assist")

    async def test_cancelled_start_releases_reservation(self):
        self.hass.data[bridge.DOMAIN]["entry"] = self.entry()
        connection = SimpleNamespace(
            subscriptions={}, user=SimpleNamespace(id="test", is_admin=True)
        )
        entered = asyncio.Event()

        async def stalled(*args):
            entered.set()
            await asyncio.Event().wait()

        with patch.object(bridge, "get_api", stalled):
            task = asyncio.create_task(
                bridge.ws_start.__wrapped__.__wrapped__(
                    self.hass,
                    connection,
                    {"id": 1, "allow_control": False, "area_id": ""},
                )
            )
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertFalse(self.hass.data[bridge.DOMAIN]["sessions"])
        self.assertFalse(connection.subscriptions)

    async def test_socket_close_revokes_pending_start(self):
        self.hass.data[bridge.DOMAIN]["entry"] = self.entry()
        connection = SimpleNamespace(
            subscriptions={}, user=SimpleNamespace(id="test", is_admin=True)
        )

        async def disconnected(*args):
            for callback in connection.subscriptions.values():
                callback()
            connection.subscriptions.clear()
            raise asyncio.CancelledError

        with (
            patch.object(bridge, "get_api", disconnected),
            self.assertRaises(asyncio.CancelledError),
        ):
            await bridge.ws_start.__wrapped__.__wrapped__(
                self.hass, connection, {"id": 1, "allow_control": False, "area_id": ""}
            )
        self.assertFalse(self.hass.data[bridge.DOMAIN]["sessions"])
        self.assertFalse(connection.subscriptions)

    async def test_actual_ha_light_tool_name_is_allowed(self):
        from homeassistant.components.light import intent as light_intent
        from homeassistant.components.light import llm as light_llm

        await self.prepare_exposure()
        await light_intent.async_setup_intents(self.hass)
        tools = light_llm.async_get_tools(self.hass, self.llm_context, "assist")
        self.assertIsNotNone(tools)
        self.assertEqual([tool.name for tool in tools.tools], ["light__HassLightSet"])
        self.assertIn(tools.tools[0].name, bridge.WRITE_TOOLS)
        self.assertEqual(
            bridge.tool_label(tools.tools[0].name), "Change light settings"
        )

    async def prepare_exposure(self):
        from homeassistant.components.homeassistant import exposed_entities
        from homeassistant.core import Context
        from homeassistant.helpers import (
            area_registry,
            device_registry,
            entity_registry,
            llm,
        )

        await area_registry.async_load(self.hass)
        device_registry.async_setup(self.hass)
        await device_registry.async_load(self.hass)
        await entity_registry.async_load(self.hass)
        exposed = exposed_entities.ExposedEntities(self.hass)
        self.hass.data[exposed_entities.DATA_EXPOSED_ENTITIES] = exposed
        await exposed.async_initialize()
        self.hass.states.async_set(
            "light.visible", "on", {"friendly_name": "Visible lamp"}
        )
        self.hass.states.async_set(
            "light.hidden", "off", {"friendly_name": "Hidden lamp"}
        )
        exposed_entities.async_expose_entity(
            self.hass, "conversation", "light.visible", True
        )
        exposed_entities.async_expose_entity(
            self.hass, "conversation", "light.hidden", False
        )
        self.llm_context = llm.LLMContext(
            platform=bridge.DOMAIN,
            context=Context(user_id="test"),
            language="en",
            assistant="conversation",
            device_id=None,
        )

    async def test_actual_ha_context_never_returns_hidden_entities(self):
        from homeassistant.components.homeassistant.llm import GetLiveContextTool
        from homeassistant.helpers.llm import ToolInput

        await self.prepare_exposure()
        result = await GetLiveContextTool().async_call(
            self.hass,
            ToolInput(tool_name="homeassistant__GetLiveContext", tool_args={}),
            self.llm_context,
        )
        self.assertIn("Visible lamp", str(result.data))
        self.assertNotIn("Hidden lamp", str(result.data))
        filtered = await GetLiveContextTool().async_call(
            self.hass,
            ToolInput(
                tool_name="homeassistant__GetLiveContext",
                tool_args={"name": "Hidden lamp"},
            ),
            self.llm_context,
        )
        self.assertNotIn("off", str(filtered.data))

    async def test_actual_ha_matching_rejects_hidden_light(self):
        from homeassistant.helpers.intent import (
            MatchTargetsConstraints,
            async_match_targets,
        )

        await self.prepare_exposure()
        hidden = async_match_targets(
            self.hass,
            MatchTargetsConstraints(
                name="Hidden lamp", domains={"light"}, assistant="conversation"
            ),
        )
        self.assertFalse(hidden.is_match)
        visible = async_match_targets(
            self.hass,
            MatchTargetsConstraints(
                name="Visible lamp", domains={"light"}, assistant="conversation"
            ),
        )
        self.assertTrue(visible.is_match)

    async def test_actual_light_intent_cannot_control_hidden_light(self):
        from homeassistant.components.light import intent as light_intent
        from homeassistant.components.light import llm as light_llm
        from homeassistant.helpers import intent, llm

        await self.prepare_exposure()
        await light_intent.async_setup_intents(self.hass)
        tools = light_llm.async_get_tools(self.hass, self.llm_context, "assist")
        tool = tools.tools[0]
        calls = []

        async def record_call(call):
            calls.append(call.data)

        self.hass.services.async_register("light", "turn_on", record_call)
        with self.assertRaises(intent.MatchFailedError):
            await tool.async_call(
                self.hass,
                llm.ToolInput(
                    tool_name=tool.name,
                    tool_args={"name": "Hidden lamp", "brightness": 40},
                ),
                self.llm_context,
            )
        await self.hass.async_block_till_done()
        self.assertEqual(calls, [])
        await tool.async_call(
            self.hass,
            llm.ToolInput(
                tool_name=tool.name,
                tool_args={"name": "Visible lamp", "brightness": 40},
            ),
            self.llm_context,
        )
        await self.hass.async_block_till_done()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["entity_id"], "light.visible")
        self.assertEqual(calls[0]["brightness_pct"], 40)

    async def test_panel_registration_failure_leaves_entry_inactive(self):
        entry = self.entry()
        with (
            patch.object(
                bridge.panel_custom,
                "async_register_panel",
                AsyncMock(side_effect=RuntimeError("synthetic registration failure")),
            ),
            self.assertRaises(RuntimeError),
        ):
            await bridge.async_setup_entry(self.hass, entry)
        self.assertNotIn("entry", self.hass.data[bridge.DOMAIN])

    async def test_panel_registration_success_activates_entry(self):
        entry = self.entry()
        with patch.object(
            bridge.panel_custom, "async_register_panel", AsyncMock()
        ) as register:
            self.assertTrue(await bridge.async_setup_entry(self.hass, entry))
        self.assertIs(self.hass.data[bridge.DOMAIN]["entry"], entry)
        self.assertTrue(register.call_args.kwargs["require_admin"])
        self.assertRegex(
            register.call_args.kwargs["module_url"],
            r"/anam_assist/panel.js\?v=[a-f0-9]{16}$",
        )

    async def test_concurrent_setup_cannot_create_second_entry(self):
        async def validate_and_complete_other_flow(*args):
            self.entry()
            return {"sessionToken": "synthetic-token"}

        with patch.object(flows, "request", validate_and_complete_other_flow):
            result = await self.flow.async_step_user({"api_key": "synthetic-key"})
        self.assertEqual(result["type"], FlowResultType.ABORT)
        self.assertEqual(result["reason"], "single_instance_allowed")


if __name__ == "__main__":
    unittest.main()
