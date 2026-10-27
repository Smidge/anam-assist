"""Deterministic public identifiers and bounded tool input."""

import hashlib
import json
import math

from homeassistant.exceptions import HomeAssistantError


def tool_bindings(names):
    """Keep original HA names server-side; never depend on provider rewriting."""
    bindings = {}
    for name in names:
        alias = "ha_" + hashlib.sha256(name.encode()).hexdigest()[:32]
        if alias in bindings:
            raise HomeAssistantError("Duplicate tool identifier. Session refused.")
        bindings[alias] = name
    return bindings


def validate_arguments(arguments):
    """Bound recursive work and cached input before validating the HA schema."""
    stack = [(arguments, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if depth > 8 or nodes > 512:
            raise HomeAssistantError("Tool arguments are too complex.")
        if isinstance(value, (dict, list)):
            # Reject broad containers before allocating one stack entry per item.
            if len(value) + nodes + len(stack) > 512:
                raise HomeAssistantError("Tool arguments are too complex.")
            if isinstance(value, dict):
                if any(not isinstance(key, str) for key in value):
                    raise HomeAssistantError("Tool argument keys must be strings.")
                stack.extend((item, depth + 1) for item in value.values())
            else:
                stack.extend((item, depth + 1) for item in value)
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise HomeAssistantError("Tool arguments must contain finite numbers.")
        elif value is not None and not isinstance(value, (str, int, bool)):
            raise HomeAssistantError("Tool arguments must contain JSON values.")
    if len(json.dumps(arguments, allow_nan=False).encode()) > 16384:
        raise HomeAssistantError("Tool arguments are too large.")
