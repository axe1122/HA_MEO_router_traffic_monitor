# custom_components/HA_MEO_router_traffic_monitor/__init__.py

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL_SECONDS
from .api_client import RouterApiClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"] # Define as plataformas que a integração oferece (neste caso, apenas sensor)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Router Traffic Sensor from a config entry."""
    _LOGGER.debug("Setting up config entry for %s", entry.entry_id)

    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    
    # Obter o intervalo de atualização das opções, ou usar o padrão
    # É importante aceder às opções via 'entry.options'
    scan_interval = entry.options.get(DEFAULT_SCAN_INTERVAL_SECONDS, DEFAULT_SCAN_INTERVAL_SECONDS) # Use DEFAULT_SCAN_INTERVAL_SECONDS como chave padrão
    
    session = async_get_clientsession(hass)
    api_client = RouterApiClient(host, username, password, session)

    # Coordenador de atualização de dados
    # MUDANÇA AQUI: Passar a 'entry' diretamente para o coordenador
    coordinator = RouterTrafficSensorCoordinator(hass, entry, api_client, scan_interval) 
    
    # Atualizar os dados pela primeira vez para verificar a conectividade
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error("Failed to connect to router at %s: %s", host, e)
        # Se a primeira atualização falhar, a integração não deve ser configurada
        raise ConfigEntryNotReady from e

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Carregar as plataformas (neste caso, o sensor)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Adicionar um listener para lidar com atualizações de opções da configuração
    entry.add_update_listener(async_reload_entry)

    _LOGGER.info("Router Traffic Sensor integration for %s setup successful", host)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry for %s", entry.entry_id)
    # Descarregar as plataformas (neste caso, o sensor)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Remover o coordenador dos dados do Home Assistant
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]: # Se não houver mais entradas para esta integração
            hass.data.pop(DOMAIN)
        _LOGGER.info("Router Traffic Sensor integration for %s unloaded successfully", entry.data[CONF_HOST])
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("Reloading config entry for %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


class RouterTrafficSensorCoordinator(DataUpdateCoordinator):
    """Router Traffic Sensor data update coordinator."""

    # MUDANÇA AQUI: Adicionar 'entry' como argumento e armazená-la
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api_client: RouterApiClient, update_interval_seconds: int):
        """Initialize my coordinator."""
        self.api_client = api_client
        self.config_entry = entry # <--- ARMAZENAR A ENTRADA DE CONFIGURAÇÃO DIRETAMENTE
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_seconds), # Define o intervalo de atualização
        )
        _LOGGER.debug("Coordinator initialized with update interval: %s seconds", update_interval_seconds)

    async def _async_update_data(self):
        """Fetch data from router API."""
        try:
            _LOGGER.debug("Fetching data from router via coordinator...")
            # Aqui é onde os dados são realmente buscados
            data = await self.api_client.async_get_stats()
            _LOGGER.debug("Data fetched successfully. Interfaces found: %s", list(data.get("interfaces", {}).keys()))
            return data
        except Exception as err:
            _LOGGER.error("Error communicating with router: %s", err)
            raise UpdateFailed(f"Error communicating with router: {err}")