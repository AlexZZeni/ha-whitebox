"""Sensores de um medidor White Box."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WhiteboxConfigEntry
from .api import BASE_URL, series_last, total_consumption
from .const import CONF_CODE, CONF_SERIAL, DOMAIN
from .coordinator import WhiteboxCoordinator, WhiteboxData

PHASES = ("a", "b", "c")


@dataclass(frozen=True, kw_only=True)
class WhiteboxSensorDescription(SensorEntityDescription):
    """Descreve como extrair o valor de um sensor."""

    value_fn: Callable[[WhiteboxData], float | None]


def _last(key: str, name: str) -> Callable[[WhiteboxData], float | None]:
    return lambda data: series_last(data.day, key, name)


def _active_total(data: WhiteboxData) -> float | None:
    values = [series_last(data.day, "ativa", f"Fase {p.upper()}") for p in PHASES]
    if any(v is None for v in values):
        return None
    return round(sum(values), 1)  # type: ignore[arg-type]


def _per_phase(
    prefix: str, key: str, unit: str, device_class: SensorDeviceClass, precision: int
) -> list[WhiteboxSensorDescription]:
    return [
        WhiteboxSensorDescription(
            key=f"{prefix}_{p}",
            translation_key=f"{prefix}_{p}",
            native_unit_of_measurement=unit,
            device_class=device_class,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=precision,
            value_fn=_last(key, f"Fase {p.upper()}"),
        )
        for p in PHASES
    ]


SENSORS: tuple[WhiteboxSensorDescription, ...] = (
    WhiteboxSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: total_consumption(data.day),
    ),
    WhiteboxSensorDescription(
        key="energy_month",
        translation_key="energy_month",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda data: total_consumption(data.month),
    ),
    *_per_phase("voltage", "tensaofn", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, 1),
    *_per_phase("current", "corrente", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, 2),
    WhiteboxSensorDescription(
        key="current_neutral",
        translation_key="current_neutral",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_last("corrente", "Neutro calculado"),
    ),
    *_per_phase("power", "ativa", UnitOfPower.WATT, SensorDeviceClass.POWER, 0),
    WhiteboxSensorDescription(
        key="power_total",
        translation_key="power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_active_total,
    ),
    *_per_phase(
        "apparent_power", "aparente", UnitOfApparentPower.VOLT_AMPERE, SensorDeviceClass.APPARENT_POWER, 0
    ),
    WhiteboxSensorDescription(
        key="apparent_power_total",
        translation_key="apparent_power_total",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_last("aparente", "Soma vetorial"),
    ),
    *_per_phase(
        "reactive_power", "reativa", UnitOfReactivePower.VOLT_AMPERE_REACTIVE, SensorDeviceClass.REACTIVE_POWER, 0
    ),
    WhiteboxSensorDescription(
        key="reactive_power_total",
        translation_key="reactive_power_total",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_last("reativa", "Soma vetorial"),
    ),
    *[
        WhiteboxSensorDescription(
            key=f"power_factor_{p}",
            translation_key=f"power_factor_{p}",
            device_class=SensorDeviceClass.POWER_FACTOR,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
            value_fn=_last("fator", f"Fase {p.upper()}"),
        )
        for p in PHASES
    ],
    WhiteboxSensorDescription(
        key="power_factor_avg",
        translation_key="power_factor_avg",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_last("fator", "Média vetorial"),
    ),
    WhiteboxSensorDescription(
        key="frequency",
        translation_key="frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_last("frequencia", "Frequência"),
    ),
    WhiteboxSensorDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=_last("temperatura", "Temperatura do equipamento"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WhiteboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cria os sensores de um medidor."""
    coordinator = entry.runtime_data
    async_add_entities(WhiteboxSensor(coordinator, entry, description) for description in SENSORS)


class WhiteboxSensor(CoordinatorEntity[WhiteboxCoordinator], SensorEntity):
    """Uma grandeza do medidor."""

    _attr_has_entity_name = True
    entity_description: WhiteboxSensorDescription

    def __init__(
        self,
        coordinator: WhiteboxCoordinator,
        entry: WhiteboxConfigEntry,
        description: WhiteboxSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        code = entry.data[CONF_CODE]
        self._attr_unique_id = f"{code}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, code)},
            name=entry.title,
            manufacturer="ISSO Digital",
            model="White Box",
            serial_number=entry.data.get(CONF_SERIAL),
            configuration_url=f"{BASE_URL}/{code}/",
        )

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)
