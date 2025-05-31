# custom_components/router_traffic_sensor/config_flow.py

import logging
import voluptuous as vol
import base64 # Para codificar as credenciais
import asyncio # Para timeout

from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_SCAN_INTERVAL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL_SECONDS, CONF_HOST
from .api_client import RouterApiClient # Vamos criar este cliente na próxima seção

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=5, max=3600, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="seconds"
        )
    ),
})

class RouterTrafficSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Router Traffic Sensor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS)

            try:
                session = async_get_clientsession(self.hass)
                api_client = RouterApiClient(host, username, password, session)
                
                # Tentar autenticar e obter os dados iniciais
                # Isso valida as credenciais e a acessibilidade da API
                await api_client.async_get_stats()
                
                return self.async_create_entry(
                    title=f"Router ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_SCAN_INTERVAL: scan_interval,
                    },
                )
            except Exception as e:
                _LOGGER.exception("Error connecting or authenticating with router at %s", host)
                errors["base"] = "cannot_connect"
                if "401" in str(e): # Se houver uma forma de identificar erro 401
                    errors["base"] = "invalid_auth"
                elif isinstance(e, asyncio.TimeoutError):
                    errors["base"] = "timeout_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(self, config_entry):
        """Get the options flow for this handler."""
        return RouterTrafficSensorOptionsFlowHandler(config_entry)


class RouterTrafficSensorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a Router Traffic Sensor options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=3600, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="seconds"
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )