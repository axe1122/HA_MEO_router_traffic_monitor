# custom_components/router_traffic_sensor/sensor.py

import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfDataRate, UnitOfInformation

from .const import DOMAIN, API_RX_BYTES_IDX, API_TX_BYTES_IDX
from .__init__ import RouterTrafficSensorCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Router Traffic Sensor platform."""
    coordinator: RouterTrafficSensorCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    
    # O `coordinator.data` terá a estrutura:
    # {
    #   "eth0": {"download": <bytes/s>, "upload": <bytes/s>, "raw": [...]},
    #   "eth1": {"download": <bytes/s>, "upload": <bytes/s>, "raw": [...]},
    #   ...
    # }

    # Criar entidades de velocidade para cada interface detetada
    for interface_name, interface_data in coordinator.data.items():
        # Entidade de Download (Rx)
        entities.append(
            RouterTrafficSpeedSensor(
                coordinator,
                interface_name,
                "download",
                f"Router {interface_name} Download Speed",
                UnitOfDataRate.BYTES_PER_SECOND, # Velocidade em bytes/segundo
                SensorDeviceClass.DATA_RATE,
                SensorStateClass.MEASUREMENT,
            )
        )
        # Entidade de Upload (Tx)
        entities.append(
            RouterTrafficSpeedSensor(
                coordinator,
                interface_name,
                "upload",
                f"Router {interface_name} Upload Speed",
                UnitOfDataRate.BYTES_PER_SECOND,
                SensorDeviceClass.DATA_RATE,
                SensorStateClass.MEASUREMENT,
            )
        )
        
        # Opcional: Criar entidades para os bytes totais acumulados
        # Útil para o painel de energia ou estatísticas de longo prazo
        # Apenas se a API retornar os contadores acumulados que se comportem como TOTAL_INCREASING
        # (isto é, só aumentam ou reiniciam para zero)
        
        # Entidade de Rx Bytes Totais
        entities.append(
            RouterTrafficTotalBytesSensor(
                coordinator,
                interface_name,
                API_RX_BYTES_IDX, # O índice do Rx Bytes no array 'data'
                f"Router {interface_name} Total Download",
                UnitOfInformation.BYTES,
                SensorDeviceClass.DATA_SIZE,
                SensorStateClass.TOTAL_INCREASING, # Importante para contadores
            )
        )
        # Entidade de Tx Bytes Totais
        entities.append(
            RouterTrafficTotalBytesSensor(
                coordinator,
                interface_name,
                API_TX_BYTES_IDX, # O índice do Tx Bytes no array 'data'
                f"Router {interface_name} Total Upload",
                UnitOfInformation.BYTES,
                SensorDeviceClass.DATA_SIZE,
                SensorStateClass.TOTAL_INCREASING, # Importante para contadores
            )
        )

    async_add_entities(entities)


class RouterTrafficSensorBase(CoordinatorEntity):
    """Base class for router traffic sensors."""

    def __init__(self, coordinator: RouterTrafficSensorCoordinator, interface: str, name: str, **kwargs) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._interface = interface
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{self.coordinator.config_entry.entry_id}_{interface}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = kwargs.get("device_class")
        self._attr_state_class = kwargs.get("state_class")
        self._attr_unit_of_measurement = kwargs.get("unit_of_measurement")

        # Criar um dispositivo HA para o router, se desejar agrupar entidades
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "model": "Generic Router", # Pode tentar descobrir o modelo se a API permitir
            "manufacturer": "Unknown",
        }


class RouterTrafficSpeedSensor(RouterTrafficSensorBase, SensorEntity):
    """Represents a router traffic speed sensor."""

    def __init__(self, coordinator: RouterTrafficSensorCoordinator, interface: str, data_key: str, name: str, unit: str, device_class: SensorDeviceClass, state_class: SensorStateClass) -> None:
        """Initialize the speed sensor."""
        super().__init__(coordinator, interface, name, unit_of_measurement=unit, device_class=device_class, state_class=state_class)
        self._data_key = data_key # 'download' or 'upload'

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # O coordenador.data contém as velocidades calculadas
        # Ex: coordinator.data['eth0']['download']
        return self.coordinator.data.get(self._interface, {}).get(self._data_key, 0)

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._data_key == "download":
            return "mdi:arrow-down-bold"
        return "mdi:arrow-up-bold"

class RouterTrafficTotalBytesSensor(RouterTrafficSensorBase, SensorEntity):
    """Represents a router total bytes sensor (for accumulated traffic)."""

    def __init__(self, coordinator: RouterTrafficSensorCoordinator, interface: str, data_index: int, name: str, unit: str, device_class: SensorDeviceClass, state_class: SensorStateClass) -> None:
        """Initialize the total bytes sensor."""
        super().__init__(coordinator, interface, name, unit_of_measurement=unit, device_class=device_class, state_class=state_class)
        self._data_index = data_index # O índice no array 'raw' data

    @property
    def native_value(self):
        """Return the state of the sensor (total bytes)."""
        # O coordenador.data['interface']['raw'] contém os dados brutos atuais
        raw_data = self.coordinator.data.get(self._interface, {}).get("raw", [])
        if self._data_index < len(raw_data):
            return raw_data[self._data_index]
        return 0

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._data_index == API_RX_BYTES_IDX:
            return "mdi:download-box"
        return "mdi:upload-box"