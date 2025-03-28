"""Entity base definitions."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription

from .api import StromligningAPI
from .const import UPDATE_SIGNAL


@dataclass
class StromligningBaseEntityDescriptionMixin:
    """Describes a basic Stromligning entity."""

    value_fn: Callable[[StromligningAPI], bool | str | int | float]


@dataclass
class StromligningSensorEntityDescription(
    SensorEntityDescription, StromligningBaseEntityDescriptionMixin
):
    """Describes a Stromligning sensor."""

    unit_fn: Callable[[StromligningAPI], None] = None
    update_signal: str = UPDATE_SIGNAL


@dataclass
class StromligningBinarySensorEntityDescription(
    BinarySensorEntityDescription, StromligningBaseEntityDescriptionMixin
):
    """Describes a Stromligning sensor."""

    unit_fn: Callable[[StromligningAPI], None] = None
