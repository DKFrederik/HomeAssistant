"""Easee charger binary sensor."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL_EQUALIZER
from .entity import ChargerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up binary sensor platform."""
    controller = hass.data[DOMAIN]["controller"]
    entities = controller.get_binary_sensor_entities()
    async_add_entities(entities)
    await controller.async_setup_done("binary_sensor")


class ChargerBinarySensor(ChargerEntity, BinarySensorEntity):
    """Easee charger binary sensor class."""

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        _LOGGER.debug("Getting state of %s", self._entity_name)
        return self._state


class EqualizerBinarySensor(ChargerEntity, BinarySensorEntity):
    """Easee equalizer binary sensor class."""

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        _LOGGER.debug("Getting state of %s", self._entity_name)
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.data.product.id)},
            serial_number=self.data.product.id,
            name=self.data.product.name,
            manufacturer=MANUFACTURER,
            model=MODEL_EQUALIZER,
            configuration_url=f"https://easee.cloud/mypage/products/{self.data.product.id}",
        )
