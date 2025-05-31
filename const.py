# custom_components/router_traffic_sensor/const.py

# Importe as constantes padrão do Home Assistant aqui
from homeassistant.const import (
    CONF_HOST,          # A constante CONF_HOST também deve vir do HA core, não definida aqui
    CONF_USERNAME,      # O valor disto é "username"
    CONF_PASSWORD,      # O valor disto é "password"
    CONF_SCAN_INTERVAL, # O valor disto é "scan_interval"
)

DOMAIN = "HA_MEO_router_traffic_monitor" # Mantenha o seu domínio consistente com a pasta!
DEFAULT_SCAN_INTERVAL_SECONDS = 5 # 5 minutos (300 segundos) como padrão

# Nomes das colunas na API (ajuste conforme necessário)
# ... (seus índices da tabela HTML)
API_RX_BYTES_IDX = 0
API_TX_BYTES_IDX = 8
API_INTERFACE_NAME_IDX = 0 # Adicionei este para consistência, se não tiver, pode remover