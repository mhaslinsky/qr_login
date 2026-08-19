"""Kill switch entity for QR Login."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data.get(DOMAIN)
    if data is None:
        return
    switch = QRLoginEnabledSwitch(hass, data)
    data.kill_switch = switch
    async_add_entities([switch])


class QRLoginEnabledSwitch(SwitchEntity, RestoreEntity):
    """Kill switch: when off, no new QR login sessions are created."""

    _attr_has_entity_name = True
    _attr_name = "QR Login Enabled"
    _attr_unique_id = f"{DOMAIN}_enabled"
    _attr_icon = "mdi:qrcode-scan"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, data) -> None:
        """Initialize the switch."""
        self.hass = hass
        self._data = data
        self._attr_is_on = data.config.get("enabled", True)

    async def async_added_to_hass(self) -> None:
        """Restore last known state on HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
            self._data.config["enabled"] = self._attr_is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self._data.config["enabled"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off and drop any request still in flight."""
        self._attr_is_on = False
        self._data.config["enabled"] = False
        self._data.sessions.clear()
        self.async_write_ha_state()
