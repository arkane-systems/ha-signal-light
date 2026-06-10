# Copilot Instructions for Signal Light

Signal Light is a Home Assistant custom integration that manages accent and notification lights using a three-layer priority model (signal, accent, base).

## High-level Architecture

### Three-Layer Model

The integration wraps a single physical light entity in a **priority-sorted stack**:

1. **Signal Layer** — Short-lived notifications (doorbell, timer, etc.). Stored as a priority queue; highest priority active signal controls the light.
2. **Accent Layer** — Long-lived overrides (movie mode, holiday theme, etc.). Stored as a priority stack; highest priority active accent controls when no signal is active.
3. **Base Layer** — Default ambient state, exposed as a standard HA `light` entity.

State evaluation is top-down: only the highest-priority non-empty layer's state is applied to the physical light.

### Core Components

- **Coordinator** (`coordinator.py`) — Owns all mutable state. Manages the three layers, computes effective state, applies to physical light, notifies listeners.
- **Light Entity** (`light.py`) — Exposes the base layer as a standard HA light for user/automation control. Extends `RestoreEntity` for state persistence.
- **Sensor Entities** (`sensor.py`) — Four sensors reporting active signal/accent names and queue/stack contents.
- **Services** (via `__init__.py`) — Domain services `set_signal`, `clear_signal`, `set_accent`, `clear_accent` registered as entity services on the light platform.
- **Config Flow** (`config_flow.py`) — UI setup for creating Signal Light instances.

### Domain

- **Domain name:** `signal_light`
- **Platforms:** `light`, `sensor`
- **No external dependencies** — uses only Home Assistant core.

## Integration Structure

```
custom_components/signal_light/
├── __init__.py           # Setup/unload, service registration
├── coordinator.py        # Central state management
├── light.py             # Base-layer light entity + entity services
├── sensor.py            # Four sensor entities
├── config_flow.py       # UI configuration
├── const.py             # All string literals and constants
├── services.yaml        # Service schema definitions
├── strings.json         # UI translation strings
├── manifest.json        # Integration metadata
└── translations/        # Localization files
```

## Key Conventions

### Data Structures

**Accent/Signal entries** are stored as plain dicts with this structure:
```python
{
    "name": str,          # unique identifier within this instance
    "priority": int,      # higher values take precedence
    "attrs": dict,        # light attributes (hs_color, brightness, etc.)
}
```

Both stacks are **sorted by priority descending**, so index 0 is always the active entry. Insertion/deletion are O(n) — acceptable given expected < 10 entries per instance.

### Constants and Naming

All string literals appear in `const.py`. This centralizes configuration keys, service names, sensor suffixes, and defaults. Use these constants everywhere—never hardcode strings that appear in multiple places.

### Entity Services vs Domain Services

The four services are registered as **entity services** on the `light` platform (not as domain-level services). This means:
- HA automatically validates and routes the `entity_id` target.
- Services delegate to the matching `SignalBaseLight` entity's methods.
- Multiple instances are fully isolated.

### State Persistence

- **Base layer** — Persisted via `RestoreEntity`. The last known base-layer state is restored on startup.
- **Accent/Signal layers** — **Not** persisted. They are ephemeral by design; automations repopulate them on startup (e.g., via `homeassistant.start` triggers).

### Listener Callbacks

Entities register a callback with the coordinator in `async_added_to_hass` and deregister in `async_will_remove_from_hass`. The coordinator calls all listeners (with no arguments) after every state mutation, triggering `write_ha_state()` on each entity.

### Physical Light Control

Every state mutation calls `_async_apply_state()` in the coordinator, which evaluates the effective state top-down and calls `light.turn_on()` or `light.turn_off()` on the underlying entity with `blocking=True` to ensure consistency.

### Entity IDs and Suffixes

For a Signal Light named "Living Room", the integration creates:
- `light.living_room_base` — Base-layer light entity
- `sensor.living_room_active_signal` — Current signal name
- `sensor.living_room_active_accent` — Current accent name
- `sensor.living_room_signal_queue` — Signal count + full queue in attributes
- `sensor.living_room_accent_stack` — Accent count + full stack in attributes

### Configuration Entry Data

The `config_entry.data` dict stores one key: `CONF_UNDERLYING_ENTITY_ID` — the `entity_id` of the physical light to control.

## Code Style and Patterns

### Docstrings

Modules have detailed module-level docstrings explaining purpose and key concepts. Classes and public methods have docstrings with Args/Returns. Use type hints throughout.

### Logging

Use `_LOGGER = logging.getLogger(__name__)` at module level. Log at DEBUG level for routine operations and INFO/ERROR for notable events.

### Validation

Use `voluptuous` for schema validation. Schemas are defined at module level (not inline). Light-attribute validation is shared via `_LIGHT_ATTR_SCHEMA` dict in both `__init__.py` and `light.py`.

### Async

All HA integration code is async. Use `async def`, `await`, and the `@callback` decorator from `homeassistant.core` for synchronous callbacks.

## No Build, Test, or Lint Commands

This is a pure Home Assistant integration with no build, test, or lint pipeline. Development is typically done by:
1. Copying the `custom_components/signal_light` directory to a HA test instance.
2. Testing via the HA UI and automations.
3. Checking for errors in HA's log.

There are no unit tests, no build artifacts, and no linting requirements configured. Code is validated only via Home Assistant's integration loader at runtime.

## Common Development Scenarios

### Adding a New Service

1. Define the service constant in `const.py` (e.g., `SERVICE_NEW_ACTION`).
2. Define the schema in `__init__.py` (use voluptuous).
3. Register the service in `async_setup_entry()` in `__init__.py`.
4. Implement the handler method in the appropriate entity class (usually `SignalBaseLight` in `light.py`).
5. The handler calls corresponding coordinator methods to mutate state.
6. Update `services.yaml` with the service schema for HA's service UI.

### Modifying State Persistence

Remember: only the base layer persists. If you add state that should survive restarts, extend `RestoreEntity` on the appropriate entity class and use its `async_get_last_state()` callback.

### Adding a New Sensor

Extend `SensorEntity` in `sensor.py`, register in `async_setup_entry()`, and add a constant for the unique-ID suffix in `const.py`. Sensors should register a listener with the coordinator and call `write_ha_state()` when notified.

### Debugging State Issues

Check the coordinator's `_accent_stack` and `_signal_queue` lists directly (in HA shell or via a custom dev service). Verify that entries are sorted by priority descending. Use the four sensor entities to inspect active layers and queue/stack contents from dashboards.
