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
    
    # Criar entidades de velocidade para cada interface detetada
    # As interfaces individuais estão em coordinator.data["interfaces"]
    for interface_name, interface_data in coordinator.data["interfaces"].items():
        # Entidade de Download (Rx)
        entities.append(
            RouterTrafficSpeedSensor(
                coordinator,
                interface_name,
                "download",
                f"Router {interface_name} Download Speed",
                UnitOfDataRate.MEGABYTES_PER_SECOND,
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
                UnitOfDataRate.MEGABYTES_PER_SECOND,
                SensorDeviceClass.DATA_RATE,
                SensorStateClass.MEASUREMENT,
            )
        )
        
        # Entidade de Rx Bytes Totais
        entities.append(
            RouterTrafficTotalBytesSensor(
                coordinator,
                interface_name,
                API_RX_BYTES_IDX,
                f"Router {interface_name} Total Download",
                UnitOfInformation.BYTES,
                SensorDeviceClass.DATA_SIZE,
                SensorStateClass.TOTAL_INCREASING,
            )
        )
        # Entidade de Tx Bytes Totais
        entities.append(
            RouterTrafficTotalBytesSensor(
                coordinator,
                interface_name,
                API_TX_BYTES_IDX,
                f"Router {interface_name} Total Upload",
                UnitOfInformation.BYTES,
                SensorDeviceClass.DATA_SIZE,
                SensorStateClass.TOTAL_INCREASING,
            )
        )

    # --- NOVOS SENSORES DE TOTAIS ---
    
    # Total de Velocidade Ethernet
    entities.append(
        RouterTotalTrafficSpeedSensor(
            coordinator,
            "ethernet",
            "download_speed",
            "Router Ethernet Download Speed",
            UnitOfDataRate.BYTES_PER_SECOND,
            SensorDeviceClass.DATA_RATE,
            SensorStateClass.MEASUREMENT,
        )
    )
    entities.append(
        RouterTotalTrafficSpeedSensor(
            coordinator,
            "ethernet",
            "upload_speed",
            "Router Ethernet Upload Speed",
            UnitOfDataRate.BYTES_PER_SECOND,
            SensorDeviceClass.DATA_RATE,
            SensorStateClass.MEASUREMENT,
        )
    )

    # Total de Velocidade Wi-Fi
    entities.append(
        RouterTotalTrafficSpeedSensor(
            coordinator,
            "wifi",
            "download_speed",
            "Router Wi-Fi Download Speed",
            UnitOfDataRate.BYTES_PER_SECOND,
            SensorDeviceClass.DATA_RATE,
            SensorStateClass.MEASUREMENT,
        )
    )
    entities.append(
        RouterTotalTrafficSpeedSensor(
            coordinator,
            "wifi",
            "upload_speed",
            "Router Wi-Fi Upload Speed",
            UnitOfDataRate.BYTES_PER_SECOND,
            SensorDeviceClass.DATA_RATE,
            SensorStateClass.MEASUREMENT,
        )
    )

    # Total de Velocidade Global
    entities.append(
        RouterTotalTrafficSpeedSensor(
            coordinator,
            "global",
            "download_speed",
            "Router Global Download Speed",
            UnitOfDataRate.BYTES_PER_SECOND,
            SensorDeviceClass.DATA_RATE,
            SensorStateClass.MEASUREMENT,
        )
    )
    entities.append(
        RouterTotalTrafficSpeedSensor(
            coordinator,
            "global",
            "upload_speed",
            "Router Global Upload Speed",
            UnitOfDataRate.BYTES_PER_SECOND,
            SensorDeviceClass.DATA_RATE,
            SensorStateClass.MEASUREMENT,
        )
    )

    # Total de Bytes Acumulados Ethernet
    entities.append(
        RouterTotalRawBytesSensor(
            coordinator,
            "ethernet",
            API_RX_BYTES_IDX,
            "Router Ethernet Total Download",
            UnitOfInformation.BYTES,
            SensorDeviceClass.DATA_SIZE,
            SensorStateClass.TOTAL_INCREASING,
        )
    )
    entities.append(
        RouterTotalRawBytesSensor(
            coordinator,
            "ethernet",
            API_TX_BYTES_IDX,
            "Router Ethernet Total Upload",
            UnitOfInformation.BYTES,
            SensorDeviceClass.DATA_SIZE,
            SensorStateClass.TOTAL_INCREASING,
        )
    )

    # Total de Bytes Acumulados Wi-Fi
    entities.append(
        RouterTotalRawBytesSensor(
            coordinator,
            "wifi",
            API_RX_BYTES_IDX,
            "Router Wi-Fi Total Download",
            UnitOfInformation.BYTES,
            SensorDeviceClass.DATA_SIZE,
            SensorStateClass.TOTAL_INCREASING,
        )
    )
    entities.append(
        RouterTotalRawBytesSensor(
            coordinator,
            "wifi",
            API_TX_BYTES_IDX,
            "Router Wi-Fi Total Upload",
            UnitOfInformation.BYTES,
            SensorDeviceClass.DATA_SIZE,
            SensorStateClass.TOTAL_INCREASING,
        )
    )

    # Total de Bytes Acumulados Global
    entities.append(
        RouterTotalRawBytesSensor(
            coordinator,
            "global",
            API_RX_BYTES_IDX,
            "Router Global Total Download",
            UnitOfInformation.BYTES,
            SensorDeviceClass.DATA_SIZE,
            SensorStateClass.TOTAL_INCREASING,
        )
    )
    entities.append(
        RouterTotalRawBytesSensor(
            coordinator,
            "global",
            API_TX_BYTES_IDX,
            "Router Global Total Upload",
            UnitOfInformation.BYTES,
            SensorDeviceClass.DATA_SIZE,
            SensorStateClass.TOTAL_INCREASING,
        )
    )


    async_add_entities(entities)


class RouterTrafficSensorBase(CoordinatorEntity, SensorEntity): # <--- Adicione SensorEntity aqui
    """Base class for router traffic sensors."""

    def __init__(
        self,
        coordinator: RouterTrafficSensorCoordinator,
        unique_suffix: str,
        name: str,
        unit_of_measurement: str, # <--- Adicione aqui
        device_class: SensorDeviceClass, # <--- Adicione aqui
        state_class: SensorStateClass # <--- Adicione aqui
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.config_entry.entry_id}_{unique_suffix}"
        
        # --- ATUALIZE ESTAS LINHAS ---
        self._attr_unit_of_measurement = unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        # --- FIM DA ATUALIZAÇÃO ---

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "model": "Generic Router",
            "manufacturer": "Unknown",
        }

class RouterTrafficSpeedSensor(RouterTrafficSensorBase, SensorEntity):
    """Represents a router traffic speed sensor."""

    def __init__(self, coordinator: RouterTrafficSensorCoordinator, interface: str, data_key: str, name: str, unit: str, device_class: SensorDeviceClass, state_class: SensorStateClass) -> None:
        """Initialize the speed sensor."""
        # Note que a unit_of_measurement está a ser passada para o super().__init__
        super().__init__(coordinator, f"{interface}_{data_key}_speed", name, unit_of_measurement=unit, device_class=device_class, state_class=state_class)
        self._interface = interface
        self._data_key = data_key
        # Armazenar a unidade para referência, se necessário na lógica de arredondamento
        self._unit = unit 

    @property
    def native_value(self):
        """Return the state of the sensor, rounded."""
        # Aceder aos dados da interface individual
        raw_value = self.coordinator.data.get("interfaces", {}).get(self._interface, {}).get(self._data_key, 0)
        
        # Verificar se o valor não é None e se é numérico antes de arredondar
        if isinstance(raw_value, (int, float)):
            # Determine o arredondamento com base na unidade ou nos valores esperados.
            # Se a unidade for B/s (Bytes por segundo), talvez não precise de casas decimais
            # para números grandes, ou 2 casas para valores menores.
            if self._unit == UnitOfDataRate.BYTES_PER_SECOND: # Exemplo: 'B/s'
                # Você pode optar por arredondar para o número inteiro mais próximo
                return round(raw_value)
            elif self._unit == UnitOfDataRate.MEGABYTES_PER_SECOND: # Exemplo: 'MB/s'
                # Se o valor já estiver em MB/s e quer 2 casas decimais
                return round(raw_value, 2)
            elif self._unit == UnitOfDataRate.KILOBYTES_PER_SECOND: # Exemplo: 'kB/s'
                # Se o valor já estiver em kB/s e quer 2 casas decimais
                return round(raw_value, 2)
            # Adicione mais condições conforme as unidades que você passa.
            # Se não houver uma condição específica, arredonde para 2 casas decimais por padrão para velocidades
            return round(raw_value, 2) 
        return 0

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
        super().__init__(coordinator, f"{interface}_raw_{data_index}_total", name, unit_of_measurement=unit, device_class=device_class, state_class=state_class)
        self._interface = interface
        self._data_index = data_index

    @property
    def native_value(self):
        """Return the state of the sensor (total bytes)."""
        raw_data = self.coordinator.data.get("interfaces", {}).get(self._interface, {}).get("raw", [])
        if self._data_index < len(raw_data):
            return raw_data[self._data_index]
        return 0

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._data_index == API_RX_BYTES_IDX:
            return "mdi:download-box"
        return "mdi:upload-box"


class RouterTotalTrafficSpeedSensor(RouterTrafficSensorBase, SensorEntity):
    """Represents a total traffic speed sensor (Ethernet, Wi-Fi, Global)."""

    def __init__(self, coordinator: RouterTrafficSensorCoordinator, category: str, data_key: str, name: str, unit: str, device_class: SensorDeviceClass, state_class: SensorStateClass) -> None:
        """Initialize the total speed sensor."""
        # Unique suffix agora inclui a categoria (ethernet, wifi, global)
        super().__init__(coordinator, f"total_{category}_{data_key}", name, unit_of_measurement=unit, device_class=device_class, state_class=state_class)
        self._category = category # 'ethernet', 'wifi', 'global'
        self._data_key = f"{category}_{data_key}" # ex: 'ethernet_download_speed'

    @property
    def native_value(self):
        """Return the state of the total speed sensor."""
        return self.coordinator.data.get("totals", {}).get(self._data_key, 0)

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if "download" in self._data_key:
            return "mdi:arrow-down-bold"
        return "mdi:arrow-up-bold"


class RouterTotalRawBytesSensor(RouterTrafficSensorBase, SensorEntity):
    """Represents a total accumulated raw bytes sensor (Ethernet, Wi-Fi, Global)."""

    def __init__(self, coordinator: RouterTrafficSensorCoordinator, category: str, data_index: int, name: str, unit: str, device_class: SensorDeviceClass, state_class: SensorStateClass) -> None:
        """Initialize the total raw bytes sensor."""
        # Unique suffix agora inclui a categoria
        super().__init__(coordinator, f"total_{category}_raw_{data_index}", name, unit_of_measurement=unit, device_class=device_class, state_class=state_class)
        self._category = category
        self._data_index = data_index
        # A chave para os dados brutos totais no coordenador.data
        self._total_raw_key = f"{category}_raw_data"

    @property
    def native_value(self):
        """Return the state of the total raw bytes sensor."""
        # Aceder aos dados brutos totais na categoria específica
        total_raw_data = self.coordinator.data.get("totals", {}).get(self._total_raw_key, [])
        if self._data_index < len(total_raw_data):
            return total_raw_data[self._data_index]
        return 0

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._data_index == API_RX_BYTES_IDX:
            return "mdi:download-box"
        return "mdi:upload-box"