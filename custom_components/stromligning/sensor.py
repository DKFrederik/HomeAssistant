"""Support for Stromligning sensors."""

from __future__ import annotations

from datetime import timedelta
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components import sensor
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_utils
from homeassistant.util import slugify as util_slugify
from jinja2 import pass_context
from pystromligning.exceptions import InvalidAPIResponse, TooManyRequests

from .api import StromligningAPI
from .base import StromligningSensorEntityDescription
from .const import CONF_TEMPLATE, DEFAULT_TEMPLATE, DOMAIN, UPDATE_SIGNAL

LOGGER = logging.getLogger(__name__)

SENSORS = [
    StromligningSensorEntityDescription(
        key="current_price_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_current(True),
        suggested_display_precision=2,
        entity_registry_enabled_default=True,
        translation_key="current_price_vat",
    ),
    StromligningSensorEntityDescription(
        key="current_price_ex_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_current(False),
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        translation_key="current_price_ex_vat",
    ),
    StromligningSensorEntityDescription(
        key="spotprice_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:transmission-tower-import",
        value_fn=lambda stromligning: stromligning.get_spot(True),
        suggested_display_precision=2,
        entity_registry_enabled_default=True,
        translation_key="spotprice_vat",
    ),
    StromligningSensorEntityDescription(
        key="spotprice_ex_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:transmission-tower-import",
        value_fn=lambda stromligning: stromligning.get_spot(False),
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        translation_key="spotprice_ex_vat",
    ),
    StromligningSensorEntityDescription(
        key="electricity_tax_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:currency-eur",
        value_fn=lambda stromligning: stromligning.get_electricitytax(True),
        suggested_display_precision=2,
        entity_registry_enabled_default=True,
        translation_key="electricity_tax_vat",
    ),
    StromligningSensorEntityDescription(
        key="electricity_tax_ex_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:currency-eur",
        value_fn=lambda stromligning: stromligning.get_electricitytax(False),
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        translation_key="electricity_tax_ex_vat",
    ),
    StromligningSensorEntityDescription(
        key="today_min_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_specific_today("min", True),
        suggested_display_precision=2,
        entity_registry_enabled_default=True,
        translation_key="today_min_vat",
    ),
    StromligningSensorEntityDescription(
        key="today_min_ex_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_specific_today("min", False),
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        translation_key="today_min_ex_vat",
    ),
    StromligningSensorEntityDescription(
        key="today_max_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_specific_today("max", True),
        suggested_display_precision=2,
        entity_registry_enabled_default=True,
        translation_key="today_max_vat",
    ),
    StromligningSensorEntityDescription(
        key="today_max_ex_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_specific_today("max", False),
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        translation_key="today_max_ex_vat",
    ),
    StromligningSensorEntityDescription(
        key="today_mean_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_specific_today("mean", True),
        suggested_display_precision=2,
        entity_registry_enabled_default=True,
        translation_key="today_mean_vat",
    ),
    StromligningSensorEntityDescription(
        key="today_mean_ex_vat",
        entity_category=None,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        value_fn=lambda stromligning: stromligning.get_specific_today("mean", False),
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        translation_key="today_mean_ex_vat",
    ),
]


async def async_setup_entry(hass, entry: ConfigEntry, async_add_devices):
    """Setup sensors."""
    sensors = []

    for sensor in SENSORS:
        entity = StromligningSensor(sensor, hass, entry)
        LOGGER.debug(
            "Added sensor with entity_id '%s'",
            entity.entity_id,
        )
        sensors.append(entity)

    async_add_devices(sensors)


class StromligningSensor(SensorEntity):
    """Representation of a Stromligning Sensor."""

    _attr_has_entity_name = True
    _attr_available = True

    def __init__(
        self,
        description: StromligningSensorEntityDescription,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize a Stromligning Sensor."""
        super().__init__()

        self.entity_description = description
        self._config = entry
        self._hass = hass
        self.api: StromligningAPI = hass.data[DOMAIN][entry.entry_id]
        self._cost_template = entry.options.get(CONF_TEMPLATE)

        self._attr_unique_id = util_slugify(
            f"{self.entity_description.key}_{self._config.entry_id}"
        )
        self._attr_should_poll = True

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._config.entry_id)},
            "name": self._config.data.get(CONF_NAME),
            "manufacturer": "Strømligning",
        }

        self._attr_native_unit_of_measurement = "kr/kWh"

        async_dispatcher_connect(
            self._hass,
            util_slugify(UPDATE_SIGNAL),
            self.handle_update,
        )

        self.entity_id = sensor.ENTITY_ID_FORMAT.format(
            util_slugify(
                f"{self._config.data.get(CONF_NAME)}_{self.entity_description.key}"
            )
        )

        if not isinstance(self._cost_template, Template):
            if self._cost_template in (None, ""):
                self._cost_template = DEFAULT_TEMPLATE
            self._cost_template = cv.template(self._cost_template)
        else:
            if self._cost_template.template in ("", None):
                self._cost_template = cv.template(DEFAULT_TEMPLATE)

    async def handle_attributes(self) -> None:
        """Handle attributes."""
        if self.entity_description.key == "current_price_vat":
            self._attr_extra_state_attributes = {}
            price_set: list = []
            for price in self.api.prices_today:
                price_set.append(
                    {
                        "start": price["date"],
                        "end": price["date"] + timedelta(hours=1),
                        "price": price["price"]["total"],
                    }
                )

            self._attr_extra_state_attributes.update({"prices": price_set})
        if self.entity_description.key == "current_price_ex_vat":
            self._attr_extra_state_attributes = {}
            price_set: list = []
            for price in self.api.prices_today:
                price_set.append(
                    {
                        "start": price["date"],
                        "end": price["date"] + timedelta(hours=1),
                        "price": price["price"]["value"],
                    }
                )

            self._attr_extra_state_attributes.update({"prices": price_set})
        elif self.entity_description.key == "today_min_vat":
            self._attr_extra_state_attributes = {}
            self._attr_extra_state_attributes.update(
                {"at": self.api.get_specific_today("min", date=True, vat=True)}
            )
        elif self.entity_description.key == "today_min_ex_vat":
            self._attr_extra_state_attributes = {}
            self._attr_extra_state_attributes.update(
                {"at": self.api.get_specific_today("min", date=True, vat=False)}
            )
        elif self.entity_description.key == "today_max_vat":
            self._attr_extra_state_attributes = {}
            self._attr_extra_state_attributes.update(
                {"at": self.api.get_specific_today("max", date=True, vat=True)}
            )
        elif self.entity_description.key == "today_max_ex_vat":
            self._attr_extra_state_attributes = {}
            self._attr_extra_state_attributes.update(
                {"at": self.api.get_specific_today("max", date=True, vat=False)}
            )

    async def handle_update(self) -> None:
        """Handle data update."""
        try:
            self._attr_native_value = self.entity_description.value_fn(
                self._hass.data[DOMAIN][self._config.entry_id]
            )

            template_value = self._cost_template.async_render()

            if not isinstance(template_value, int | float):
                try:
                    template_value = float(template_value)
                except (TypeError, ValueError):
                    LOGGER.exception(
                        "Failed to convert %s %s to float",
                        template_value,
                        type(template_value),
                    )
                    raise

            self._attr_native_value += template_value

            LOGGER.debug(
                "Setting value for '%s' to: %s",
                self.entity_id,
                self._attr_native_value,
            )
            await self.handle_attributes()
            self._attr_available = True
        except TooManyRequests:
            if self._attr_available:
                LOGGER.warning(
                    "You made too many requests to the API and have been banned for 15 minutes."
                )
            self._attr_available = False
        except InvalidAPIResponse:
            if self._attr_available:
                LOGGER.error("The Stromligning API made an invalid response.")
            self._attr_available = False

    async def async_added_to_hass(self):
        await self.handle_update()
        return await super().async_added_to_hass()