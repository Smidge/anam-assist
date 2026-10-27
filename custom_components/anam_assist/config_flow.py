"""Configure credentials without returning saved secrets to the browser."""

import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import InvalidAuth, default_config, persona_config, request, session_options
from .const import DOMAIN


class AnamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self._configure("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._configure(
            "reconfigure", user_input, self._get_reconfigure_entry()
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._configure(
            "reauth_confirm", user_input, self._get_reauth_entry()
        )

    async def _configure(self, step, user_input, entry=None):
        errors = {}
        existing = dict(entry.data) if entry else {}
        if user_input is not None:
            try:
                persona_id = user_input.get("persona_id", "").strip()
                if persona_id:
                    persona_id = str(uuid.UUID(persona_id))
                key = user_input.get("api_key", "").strip() or existing.get(
                    "api_key", ""
                )
                if not key:
                    raise InvalidAuth("An API key is required.")
                orientation = user_input.get("orientation", "portrait")
                config = (
                    persona_config(
                        await request(self.hass, key, f"/personas/{persona_id}")
                    )
                    if persona_id
                    else default_config()
                )
                token = await request(
                    self.hass,
                    key,
                    "/auth/session-token",
                    {
                        "personaConfig": config,
                        "sessionOptions": session_options(orientation),
                    },
                )
                if (
                    not isinstance(token.get("sessionToken"), str)
                    or not token["sessionToken"]
                ):
                    raise HomeAssistantError("Missing session token.")
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ValueError:
                errors["persona_id"] = "invalid_persona"
            except HomeAssistantError:
                errors["base"] = "cannot_connect"
            else:
                data = {
                    "api_key": key,
                    "persona_id": persona_id,
                    "orientation": orientation,
                }
                if entry:
                    return self.async_update_reload_and_abort(entry, data=data)
                if self._async_current_entries():
                    return self.async_abort(reason="single_instance_allowed")
                return self.async_create_entry(title="Anam Assist", data=data)
        key_field = vol.Optional("api_key") if entry else vol.Required("api_key")
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(
                {
                    key_field: selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                    vol.Optional(
                        "persona_id", default=existing.get("persona_id", "")
                    ): str,
                    vol.Optional(
                        "orientation", default=existing.get("orientation", "portrait")
                    ): vol.In(["portrait", "landscape"]),
                }
            ),
            errors=errors,
        )
