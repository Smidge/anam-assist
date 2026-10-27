"""Anam Assist constants."""

DOMAIN = "anam_assist"
API_URL = "https://api.anam.ai/v1"
READ_TOOLS = frozenset(
    {
        "GetLiveContext",
        "HassGetState",
        "homeassistant__GetLiveContext",
        "intent__HassGetState",
    }
)
WRITE_TOOLS = frozenset(
    {
        "HassTurnOn",
        "HassTurnOff",
        "HassLightSet",
        "intent__HassTurnOn",
        "intent__HassTurnOff",
        "intent__HassLightSet",
        "light__HassLightSet",
    }
)
SESSION_SECONDS = 600
