# custom_components/router_traffic_sensor/__init__.py

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL_SECONDS, CONF_HOST
from .api_client import RouterApiClient # Importar o cliente da API

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Router Traffic Sensor from a config entry."""
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))

    session = async_get_clientsession(hass)
    api_client = RouterApiClient(host, username, password, session)

    coordinator = RouterTrafficSensorCoordinator(
        hass,
        api_client=api_client,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.add_update_listener(async_reload_entry)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options changed."""
    await hass.config_entries.async_reload(entry.entry_id)


class RouterTrafficSensorCoordinator(DataUpdateCoordinator):
    """Coordinador para gerir a obtenção de dados do router."""

    def __init__(self, hass: HomeAssistant, api_client: RouterApiClient, update_interval: timedelta) -> None:
        """Initialize my coordinator."""
        self._api_client = api_client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from router API."""
        try:
            # O cliente API já gere a autenticação e o parsing
            data = await self._api_client.async_get_stats()
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with router: {err}") from err