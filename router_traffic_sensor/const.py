# custom_components/router_traffic_sensor/const.py

DOMAIN = "router_traffic_sensor"
DEFAULT_SCAN_INTERVAL_SECONDS = 5 # Intervalo de atualização. 10 segundos é um bom compromisso para tráfego.

CONF_HOST = "192.168.1.254"
CONF_USERNAME = "meo"
CONF_PASSWORD = "meo"

# Nomes das colunas na API (ajuste conforme necessário)
# Assumindo a ordem das colunas no HTML como:
# 0: Interface Name (eth0, eth1, etc.)
# 1: Rx Bytes (Received Bytes)
# 2: Rx Packets
# 3: Rx Errors
# 4: Rx Dropped
# 5: Tx Bytes (Transmitted Bytes) - O que você chamou de "Download"
# 6: Tx Packets
# 7: Tx Errors
# 8: Tx Dropped
# ... e o resto dos 8 campos para completar 16

# ATENÇÃO: As posições de download/upload que você sugeriu no JS (data[0] para download e data[8] para upload)
# não correspondem ao exemplo HTML que você forneceu.
# No HTML, as colunas são:
# <td class='hd'>eth0</td>
# <td>1284674331</td> <- Index 0 (Rx Bytes)
# <td>12041400</td> <- Index 1 (Rx Packets)
# ...
# <td>1186628879</td> <- Index 8 (Tx Bytes)

# Ajustarei para Rx Bytes (Index 0) e Tx Bytes (Index 8) no array `data` PARSED.
# Considere "Download" como Rx Bytes e "Upload" como Tx Bytes.
# Confirme estas posições no seu router!

# Mapeamento para as colunas relevantes no array `data` depois do parsing do HTML
# Rx Bytes (recebido - download)
API_RX_BYTES_IDX = 0
# Tx Bytes (transmitido - upload)
API_TX_BYTES_IDX = 8