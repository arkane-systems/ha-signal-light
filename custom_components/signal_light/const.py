"""Constants for the Signal Light integration.

All string literals that appear in more than one place, or that carry semantic
meaning beyond a plain dictionary key, are centralised here so that they can be
updated in one place without hunting through the rest of the codebase.
"""

# ── Integration identity ───────────────────────────────────────────────────────

# The domain string used throughout Home Assistant to identify this integration.
DOMAIN = "signal_light"

# The HA platform names used by this integration.
PLATFORMS = ["light", "sensor"]

# ── Config-entry data keys ─────────────────────────────────────────────────────

# The entity_id of the underlying physical light (or light group) that this
# signal-light instance will control.
CONF_UNDERLYING_ENTITY_ID = "underlying_entity_id"

# ── hass.data keys ─────────────────────────────────────────────────────────────

# Under hass.data[DOMAIN][config_entry.entry_id] we store the coordinator.
DATA_COORDINATOR = "coordinator"

# ── Service names ──────────────────────────────────────────────────────────────

# Signal-layer services — add/remove a named signal from the priority queue.
SERVICE_SET_SIGNAL   = "set_signal"
SERVICE_CLEAR_SIGNAL = "clear_signal"

# Accent-layer services — add/remove a named accent from the priority stack.
SERVICE_SET_ACCENT   = "set_accent"
SERVICE_CLEAR_ACCENT = "clear_accent"

# ── Service field names ────────────────────────────────────────────────────────

# Name string that uniquely identifies a signal within a signal-light instance.
ATTR_SIGNAL_NAME = "signal_name"

# Name string that uniquely identifies an accent within a signal-light instance.
ATTR_ACCENT_NAME = "accent_name"

# Integer priority — higher numbers take precedence.
ATTR_PRIORITY = "priority"

# ── Sensor unique-ID suffixes ──────────────────────────────────────────────────

# Name of the currently-active signal (highest priority), or "none".
SENSOR_ACTIVE_SIGNAL = "active_signal"

# Name of the currently-active accent (highest priority), or "none".
SENSOR_ACTIVE_ACCENT = "active_accent"

# Count of signals currently in the queue, with full queue as an attribute.
SENSOR_SIGNAL_QUEUE = "signal_queue"

# Count of accents currently on the stack, with full stack as an attribute.
SENSOR_ACCENT_STACK = "accent_stack"

# ── Defaults ───────────────────────────────────────────────────────────────────

# Priority used when the caller does not supply one explicitly.
DEFAULT_PRIORITY = 50
