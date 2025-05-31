# custom_components/HA_MEO_router_traffic_monitor/__init__.py

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_SCAN_INTERVAL

# Importe as constantes definidas na sua integração
from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL_SECONDS
# Importe o seu cliente de API personalizado
from .api_client import RouterApiClient

_LOGGER = logging.getLogger(__name__)

# Define as plataformas que a sua integração oferece (neste caso, apenas sensores)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura o sensor de tráfego do router a partir de uma entrada de configuração."""
    _LOGGER.debug("A configurar a entrada de configuração para %s", entry.entry_id)

    # Extrai os dados de configuração da entrada
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    
    # Obtém o intervalo de atualização das opções da entrada, ou usa o valor padrão
    # Nota: CONF_SCAN_INTERVAL vem do Home Assistant core, DEFAULT_SCAN_INTERVAL_SECONDS vem do seu const.py
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS)
    
    # Obtém uma sessão HTTP assíncrona do Home Assistant
    session = async_get_clientsession(hass)
    # Inicializa o seu cliente de API personalizado
    api_client = RouterApiClient(host, username, password, session)

    # Cria e inicializa o coordenador de atualização de dados
    coordinator = RouterTrafficSensorCoordinator(
        hass,
        entry,          # Passa a entrada de configuração diretamente para o coordenador
        api_client,
        scan_interval
    )
    
    # Realiza a primeira atualização de dados para verificar a conectividade e carregar dados iniciais
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error("Falha ao conectar ao router em %s: %s", host, e)
        # Se a primeira atualização falhar, a integração não deve ser configurada
        raise ConfigEntryNotReady(f"Falha ao conectar ou autenticar com o router: {e}") from e

    # Armazena o coordenador no objeto 'hass.data' para que as plataformas (sensores) possam aceder a ele
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Carrega as plataformas definidas (sensor.py neste caso)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Adiciona um listener para recarregar a integração quando as opções são alteradas
    entry.add_update_listener(async_reload_entry)

    _LOGGER.info("Integração do Sensor de Tráfego do Router para %s configurada com sucesso", host)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarrega uma entrada de configuração."""
    _LOGGER.debug("A descarregar a entrada de configuração para %s", entry.entry_id)
    # Descarrega as plataformas registadas
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Remove o coordenador dos dados do Home Assistant
        hass.data[DOMAIN].pop(entry.entry_id)
        # Se não houver mais entradas para este domínio, remove o domínio do hass.data
        if not hass.data[DOMAIN]: 
            hass.data.pop(DOMAIN)
        _LOGGER.info("Integração do Sensor de Tráfego do Router para %s descarregada com sucesso", entry.data[CONF_HOST])
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarrega a entrada de configuração quando as opções são alteradas."""
    _LOGGER.debug("A recarregar a entrada de configuração para %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


class RouterTrafficSensorCoordinator(DataUpdateCoordinator):
    """Coordenador de atualização de dados para o sensor de tráfego do router."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api_client: RouterApiClient, update_interval_seconds: int):
        """Inicializa o coordenador."""
        self.api_client = api_client
        self.config_entry = entry # Armazena a entrada de configuração para acesso posterior (ex: opções)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_seconds), # Define o intervalo de atualização
        )
        _LOGGER.debug("Coordenador inicializado com intervalo de atualização: %s segundos", update_interval_seconds)

    async def _async_update_data(self):
        """Busca dados da API do router. Este é o método chamado pelo coordenador."""
        try:
            _LOGGER.debug("A buscar dados do router via coordenador...")
            # Realiza a chamada à API usando o cliente
            data = await self.api_client.async_get_stats()
            _LOGGER.debug("Dados buscados com sucesso. Interfaces encontradas: %s", list(data.get("interfaces", {}).keys()))
            return data
        except Exception as err:
            _LOGGER.error("Erro na comunicação com o router: %s", err)
            # Lança UpdateFailed para sinalizar ao Home Assistant que a atualização falhou
            raise UpdateFailed(f"Erro na comunicação com o router: {err}")