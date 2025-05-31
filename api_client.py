# custom_components/router_traffic_sensor/api_client.py

import logging
import base64
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import aiohttp
from bs4 import BeautifulSoup

# --- ADICIONE ESTAS DUAS LINHAS ---
from .const import API_RX_BYTES_IDX, API_TX_BYTES_IDX 
# Certifique-se de que DOMAIN, CONF_HOST, etc., se forem usados aqui, também são importados de const.py
# --- FIM DA ADIÇÃO ---

_LOGGER = logging.getLogger(__name__)

# --- Mantém o restante da classe RouterApiClient igual até aqui ---

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
                 _LOGGER.warning("Authentication returned 200 OK without redirect. Check if SESSIONID is needed or obtained.")
            elif response.status == 302:
                _LOGGER.warning("Authentication redirect detected.")
            else:
                response.raise_for_status()

            set_cookie_header = response.headers.getall("Set-Cookie", [])
            _LOGGER.warning("Set-Cookie headers received: %s", set_cookie_header)

            session_cookie = next((c for c in set_cookie_header if "SESSIONID=" in c), None)
            if not session_cookie:
                raise ValueError("SESSIONID cookie not found in response headers.")
            
            match = re.search(r"SESSIONID=([^;]+)", session_cookie)
            if match:
                self._session_id = match.group(0)
                _LOGGER.warning("Successfully obtained SESSIONID: %s", self._session_id)
            else:
                raise ValueError("Failed to extract SESSIONID from cookie string.")

    async def _get_raw_stats(self) -> Dict[str, Any]:
        """Fetch raw statistics from the router."""
        if not self._session_id:
            await self._authenticate()

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
            
            data_values = []
            for i in range(1, len(tds)):
                try:
                    data_values.append(int(tds[i].get_text(strip=True)))
                except ValueError:
                    data_values.append(0)

            result.append({
                "interface": interface_name,
                "data": data_values,
            })
        _LOGGER.debug("Parsed HTML table: %s", result)
        return result

    def _calculate_and_categorize_stats(self, current_parsed_stats: List[Dict[str, Any]], elapsed_seconds: float) -> Dict[str, Any]:
        """
        Calculate speeds and categorize stats (per interface, wifi, ethernet, global).
        Returns a dictionary like:
        {
            "interfaces": { "eth0": {"download": X, "upload": Y, "raw": [...]}, ... },
            "totals": {
                "ethernet_download": Z, "ethernet_upload": W,
                "wifi_download": A, "wifi_upload": B,
                "global_download": C, "global_upload": D,
                "ethernet_raw_rx": E, "ethernet_raw_tx": F, # etc for all 16 raw indices
                ...
            }
        }
        """
        speeds_per_interface = {}
        
        # Initialize totals for this update cycle
        total_ethernet_download_speed = 0
        total_ethernet_upload_speed = 0
        total_wifi_download_speed = 0
        total_wifi_upload_speed = 0

        # Initialize raw byte totals
        # Assuming 16 raw data points per interface
        total_ethernet_raw_data = [0] * 16
        total_wifi_raw_data = [0] * 16
        

        for curr_row in current_parsed_stats:
            interface = curr_row["interface"]
            prev_row = self._previous_stats.get(interface)
            
            is_wifi = interface.startswith("wl") # Assumes Wi-Fi interfaces start with 'wl'
            
            # --- Calculate speeds for individual interfaces ---
            download_speed = 0
            upload_speed = 0

            # Only calculate speed if previous data exists and elapsed time is valid
            if prev_row and elapsed_seconds > 0:
                current_rx_bytes = curr_row["data"][API_RX_BYTES_IDX] if len(curr_row["data"]) > API_RX_BYTES_IDX else 0
                previous_rx_bytes = prev_row["data"][API_RX_BYTES_IDX] if len(prev_row["data"]) > API_RX_BYTES_IDX else 0

                current_tx_bytes = curr_row["data"][API_TX_BYTES_IDX] if len(curr_row["data"]) > API_TX_BYTES_IDX else 0
                previous_tx_bytes = prev_row["data"][API_TX_BYTES_IDX] if len(prev_row["data"]) > API_TX_BYTES_IDX else 0
                
                download_diff = current_rx_bytes - previous_rx_bytes
                if download_diff < 0: # Counter wrapped
                    download_diff = (2**32 - previous_rx_bytes) + current_rx_bytes
                    _LOGGER.warning("Rx Bytes counter for %s wrapped. Diff: %s", interface, download_diff)

                upload_diff = current_tx_bytes - previous_tx_bytes
                if upload_diff < 0: # Counter wrapped
                    upload_diff = (2**32 - previous_tx_bytes) + current_tx_bytes
                    _LOGGER.warning("Tx Bytes counter for %s wrapped. Diff: %s", interface, upload_diff)
                
                download_speed = ((upload_diff / (1024*1024)) / elapsed_seconds)   # Convert bytes to MB/s
                upload_speed = ((download_diff / (1024*1024)) / elapsed_seconds)  # Convert bytes to MB/s
            
            speeds_per_interface[interface] = {                                
                "download": download_speed ,  # Convert bytes to MB
                "upload": upload_speed,      # Convert bytes to MB
                "raw": curr_row["data"],
            }

            # --- Aggregate totals ---
            if is_wifi:
                total_wifi_download_speed += download_speed
                total_wifi_upload_speed += upload_speed
                for i, val in enumerate(curr_row["data"]):
                    total_wifi_raw_data[i] += val
            else: # Assuming it's Ethernet if not Wi-Fi
                total_ethernet_download_speed += download_speed
                total_ethernet_upload_speed += upload_speed
                for i, val in enumerate(curr_row["data"]):
                    total_ethernet_raw_data[i] += val
        
        # Calculate global totals
        total_global_download_speed = total_ethernet_download_speed + total_wifi_download_speed
        total_global_upload_speed = total_ethernet_upload_speed + total_wifi_upload_speed
        
        total_global_raw_data = [0] * 16
        for i in range(16):
            total_global_raw_data[i] = total_ethernet_raw_data[i] + total_wifi_raw_data[i]

        return {
            "interfaces": speeds_per_interface,
            "totals": {
                "ethernet_download_speed": total_ethernet_download_speed,
                "ethernet_upload_speed": total_ethernet_upload_speed,
                "wifi_download_speed": total_wifi_download_speed,
                "wifi_upload_speed": total_wifi_upload_speed,
                "global_download_speed": total_global_download_speed,
                "global_upload_speed": total_global_upload_speed,
                "ethernet_raw_data": total_ethernet_raw_data,
                "wifi_raw_data": total_wifi_raw_data,
                "global_raw_data": total_global_raw_data,
            }
        }


    async def async_get_stats(self) -> Dict[str, Any]:
        """Fetch and process router statistics."""
        if not self._session_id:
             try:
                 await self._authenticate()
             except Exception as e:
                 _LOGGER.error("Failed initial authentication: %s", e)
                 raise

        try:
            raw_data = await self._get_raw_stats()
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                _LOGGER.warning("Authentication failed (401). Retrying authentication.")
                self._session_id = None
                await self._authenticate()
                raw_data = await self._get_raw_stats()
            else:
                raise
        except Exception as e:
            _LOGGER.error("Failed to get raw stats: %s", e)
            raise

        current_time = datetime.now()
        html_stats = raw_data.get("stats", "")
        parsed_current_stats = self._parse_html_table(html_stats)

        elapsed_seconds = 0
        if self._last_update_time:
            elapsed_seconds = (current_time - self._last_update_time).total_seconds()

        # Call the new calculation and categorization method
        processed_data = self._calculate_and_categorize_stats(parsed_current_stats, elapsed_seconds)

        # Update previous stats for the next cycle
        new_previous_stats = {}
        for row in parsed_current_stats:
            new_previous_stats[row["interface"]] = row
        self._previous_stats = new_previous_stats
        self._last_update_time = current_time

        return processed_data