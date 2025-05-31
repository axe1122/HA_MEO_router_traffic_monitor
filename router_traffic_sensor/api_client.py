# custom_components/router_traffic_sensor/api_client.py

import logging
import base64
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class RouterApiClient:
    """Client for router API."""

    def __init__(self, host: str, username: str, password: str, session: aiohttp.ClientSession):
        """Initialize the client."""
        self._host = host
        self._username = username
        self._password = password
        self._session = session
        self._session_id: Optional[str] = None
        self._previous_stats: Dict[str, Any] = {} # Para guardar o estado anterior do tráfego
        self._last_update_time: Optional[datetime] = None


    async def _authenticate(self) -> None:
        """Perform authentication and get SESSIONID."""
        auth_string = f"{self._username}:{self._password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode("ascii")
        headers = {
            "Authorization": f"Basic {encoded_auth}"
        }
        auth_url = f"http://{self._host}/index.html"
        
        _LOGGER.debug("Attempting to authenticate to %s", auth_url)
        async with self._session.get(auth_url, headers=headers, allow_redirects=False, timeout=10) as response:
            if response.status == 200:
                 # Pode não haver set-cookie se já autenticado ou se for um router que não usa
                _LOGGER.warning("Authentication returned 200 OK without redirect. Check if SESSIONID is needed or obtained.")
            elif response.status == 302: # Redirecionamento indica sucesso na autenticação
                _LOGGER.debug("Authentication redirect detected.")
            else:
                response.raise_for_status() # Levanta exceção para outros erros HTTP

            set_cookie_header = response.headers.getall("Set-Cookie", [])
            _LOGGER.debug("Set-Cookie headers received: %s", set_cookie_header)

            session_cookie = next((c for c in set_cookie_header if "SESSIONID=" in c), None)
            if not session_cookie:
                raise ValueError("SESSIONID cookie not found in response headers.")
            
            # Extrair apenas o valor do SESSIONID
            match = re.search(r"SESSIONID=([^;]+)", session_cookie)
            if match:
                self._session_id = match.group(0) # Ex: SESSIONID=ca9373723...
                _LOGGER.debug("Successfully obtained SESSIONID: %s", self._session_id)
            else:
                raise ValueError("Failed to extract SESSIONID from cookie string.")

    async def _get_raw_stats(self) -> Dict[str, Any]:
        """Fetch raw statistics from the router."""
        if not self._session_id:
            await self._authenticate() # Autentica se não tiver SESSIONID

        headers = {
            "Cookie": self._session_id
        }
        stats_url = f"http://{self._host}/ss-json/fgw.lanstatistics.json"

        _LOGGER.debug("Fetching stats from %s with Cookie: %s", stats_url, self._session_id)
        async with self._session.get(stats_url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            data = await response.json()
            if "stats" not in data or not isinstance(data["stats"], str):
                raise ValueError("Unexpected API response format: 'stats' field missing or not a string.")
            return data

    def _parse_html_table(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse the HTML table from the 'stats' field."""
        soup = BeautifulSoup(f"<table>{html_content}</table>", "html.parser")
        result = []

        for row_tag in soup.find_all("tr"):
            tds = row_tag.find_all("td")
            if not tds:
                continue

            interface_name = tds[0].get_text(strip=True)
            
            # Extrair os dados numéricos
            data_values = []
            for i in range(1, len(tds)): # Começa do segundo <td>
                try:
                    data_values.append(int(tds[i].get_text(strip=True)))
                except ValueError:
                    data_values.append(0) # Default para 0 se não for um número

            result.append({
                "interface": interface_name,
                "data": data_values,
            })
        _LOGGER.debug("Parsed HTML table: %s", result)
        return result

    def _calculate_speed(self, current_stats: List[Dict[str, Any]], elapsed_seconds: float) -> Dict[str, Any]:
        """Calculate download and upload speeds."""
        speeds = {}
        
        for curr_row in current_stats:
            interface = curr_row["interface"]
            prev_row = self._previous_stats.get(interface)

            if not prev_row or elapsed_seconds <= 0:
                # Não há dados anteriores ou tempo decorrido inválido, não podemos calcular a velocidade
                speeds[interface] = {"download": 0, "upload": 0, "raw": curr_row["data"]}
                continue

            # ATENÇÃO: Confirme que estes são os índices corretos para Rx Bytes e Tx Bytes
            # no array 'data' (depois do parsing).
            # Baseado no seu HTML, é provável que Rx Bytes seja index 0 e Tx Bytes seja index 8.
            current_rx_bytes = curr_row["data"][0] if len(curr_row["data"]) > 0 else 0
            previous_rx_bytes = prev_row["data"][0] if len(prev_row["data"]) > 0 else 0

            current_tx_bytes = curr_row["data"][8] if len(curr_row["data"]) > 8 else 0
            previous_tx_bytes = prev_row["data"][8] if len(prev_row["data"]) > 8 else 0
            
            # Lidar com reinícios do contador (wraparound)
            # Se o contador atual for menor que o anterior, assumimos que reiniciou.
            # Isso é uma suposição para contadores de 32 bits que rolam.
            # Se forem de 64 bits ou maiores, a diferença sempre será positiva.
            download_diff = current_rx_bytes - previous_rx_bytes
            if download_diff < 0: # Contador reiniciou
                # Assumimos que o contador é de 32 bits (4.294.967.295) para este exemplo
                # Mas pode ser diferente para o seu router
                download_diff = (2**32 - previous_rx_bytes) + current_rx_bytes
                _LOGGER.warning("Rx Bytes counter for %s wrapped around. Old: %s, New: %s, Diff: %s", 
                                interface, previous_rx_bytes, current_rx_bytes, download_diff)


            upload_diff = current_tx_bytes - previous_tx_bytes
            if upload_diff < 0: # Contador reiniciou
                upload_diff = (2**32 - previous_tx_bytes) + current_tx_bytes
                _LOGGER.warning("Tx Bytes counter for %s wrapped around. Old: %s, New: %s, Diff: %s", 
                                interface, previous_tx_bytes, current_tx_bytes, upload_diff)
            
            speeds[interface] = {
                "download": download_diff / elapsed_seconds, # Bytes por segundo
                "upload": upload_diff / elapsed_seconds,     # Bytes por segundo
                "raw": curr_row["data"],                     # Dados brutos atuais
            }
        
        return speeds

    async def async_get_stats(self) -> Dict[str, Any]:
        """Fetch and process router statistics."""
        # Tentar obter o SESSIONID se ainda não tivermos um, ou se a chamada anterior falhou
        # e indicou que o SESSIONID pode ter expirado.
        # Por simplicidade, vamos re-autenticar se houver erro HTTP 401 ou se SESSIONID for None.
        if not self._session_id:
             try:
                 await self._authenticate()
             except Exception as e:
                 _LOGGER.error("Failed initial authentication: %s", e)
                 raise # Propagar a exceção

        try:
            raw_data = await self._get_raw_stats()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                _LOGGER.warning("Authentication failed (401). Retrying authentication.")
                self._session_id = None # Limpar SESSIONID para forçar nova autenticação
                await self._authenticate() # Tentar novamente
                raw_data = await self._get_raw_stats() # Tentar obter os dados novamente
            else:
                raise # Re-raise other HTTP errors
        except Exception as e:
            _LOGGER.error("Failed to get raw stats: %s", e)
            raise # Re-raise other network/parsing errors

        current_time = datetime.now()
        html_stats = raw_data.get("stats", "")
        parsed_current_stats = self._parse_html_table(html_stats)

        elapsed_seconds = 0
        if self._last_update_time:
            elapsed_seconds = (current_time - self._last_update_time).total_seconds()

        calculated_speeds = self._calculate_speed(parsed_current_stats, elapsed_seconds)

        # Atualizar o estado anterior para a próxima iteração
        new_previous_stats = {}
        for row in parsed_current_stats:
            new_previous_stats[row["interface"]] = row
        self._previous_stats = new_previous_stats
        self._last_update_time = current_time

        # Retornar os dados processados, incluindo velocidades e dados brutos
        return calculated_speeds