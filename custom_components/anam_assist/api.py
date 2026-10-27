"""Server-side Anam API calls; never return credentials or upstream error bodies."""

import json

from aiohttp import ClientError, ClientTimeout
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_URL

MAX_RESPONSE_BYTES = 1024 * 1024


class InvalidAuth(HomeAssistantError):
    """The configured credential is no longer accepted."""


def session_options(orientation="portrait"):
    options = {"dataRetention": {"recording": False, "transcripts": False}}
    if orientation == "portrait":
        options.update(videoWidth=768, videoHeight=1152)
    return options


async def request(hass, key, path, payload=None):
    try:
        async with async_get_clientsession(hass).request(
            "POST" if payload is not None else "GET",
            API_URL + path,
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=ClientTimeout(total=25),
            allow_redirects=False,
        ) as response:
            if response.status in (401, 403):
                raise InvalidAuth(
                    "Anam rejected the API key or its permissions. Reconfigure Anam Assist."
                )
            if response.status != 200:
                raise HomeAssistantError(
                    f"Anam returned HTTP {response.status}. Check the API key, persona and account access."
                )
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise HomeAssistantError("Anam returned an oversized response.")
            result = json.loads(body)
            if not isinstance(result, dict):
                raise HomeAssistantError("Anam returned an unexpected response.")
            return result
    except (TimeoutError, ClientError, ValueError) as err:
        raise HomeAssistantError("Could not reach Anam. Try again shortly.") from err


def persona_config(persona):
    avatar = persona.get("avatar") or {}
    voice = persona.get("voice") or {}
    if (
        not isinstance(avatar, dict)
        or not isinstance(voice, dict)
        or not all(
            isinstance(value, str) and value
            for value in (avatar.get("id"), voice.get("id"), persona.get("llmId"))
        )
    ):
        raise HomeAssistantError(
            "Choose a published Anam persona with an avatar, voice and LLM."
        )
    result = {
        "name": "Home",
        "avatarId": avatar["id"],
        "voiceId": voice["id"],
        "llmId": persona["llmId"],
    }
    for field in ("avatarModel", "voiceSpeed"):
        if persona.get(field) is not None:
            result[field] = persona[field]
    return result


def default_config():
    """Public example persona from Anam's API key quickstart."""
    return {
        "name": "Home",
        "avatarId": "071b0286-4cce-4808-bee2-e642f1062de3",
        "voiceId": "de23e340-1416-4dd8-977d-065a7ca11697",
        "llmId": "a7cf662c-2ace-4de1-a21e-ef0fbf144bb7",
    }
