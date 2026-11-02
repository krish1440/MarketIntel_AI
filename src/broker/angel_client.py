import logging
import pyotp
import requests
from typing import Dict, Any, Optional
from SmartApi import SmartConnect
from src.config.settings import settings

logger = logging.getLogger(__name__)

class AngelClient:
    """
    Automated Angel One SmartAPI client with automated TOTP session management.
    """
    INSTRUMENT_DUMP_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"

    def __init__(self):
        self.api_key = settings.ANGEL_API_KEY
        self.client_code = settings.ANGEL_CLIENT_CODE
        self.pin = settings.ANGEL_PIN
        self.totp_secret = settings.ANGEL_TOTP_SECRET
        
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.session_data: Optional[Dict[str, Any]] = None
        self.feed_token: Optional[str] = None

    def login(self) -> bool:
        """Generates dynamic TOTP and authenticates session."""
        try:
            if not self.totp_secret:
                raise ValueError("ANGEL_TOTP_SECRET is not configured.")
            
            totp = pyotp.TOTP(self.totp_secret).now()
            logger.info(f"Generated TOTP for {self.client_code}")
            
            data = self.smart_api.generateSession(self.client_code, self.pin, totp)
            if data and data.get("status"):
                self.session_data = data.get("data")
                self.feed_token = self.smart_api.getfeedToken()
                logger.info("Angel One SmartAPI authentication successful!")
                return True
            else:
                logger.error(f"Failed to authenticate: {data.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Error during Angel One login: {e}")
            return False

    def get_profile(self) -> Optional[Dict[str, Any]]:
        """Fetch user profile details."""
        if not self.session_data:
            if not self.login():
                return None
        return self.smart_api.getProfile(self.session_data.get("refreshToken"))

    def download_instrument_master(self) -> list:
        """
        Downloads official Angel One complete instrument dump containing all NSE and BSE scrips,
        tokens, symbols, lotsize, ticksize, and ISINs.
        """
        logger.info(f"Downloading instrument master from {self.INSTRUMENT_DUMP_URL}...")
        response = requests.get(self.INSTRUMENT_DUMP_URL, timeout=30)
        response.raise_for_status()
        instruments = response.json()
        logger.info(f"Downloaded {len(instruments)} instruments from Angel One.")
        return instruments

    def get_historical_candles(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str,
        max_retries: int = 3
    ) -> Optional[list]:
        """
        Fetch historical candle bars with auto-retry and exponential backoff for rate limits.
        interval: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, ONE_HOUR, ONE_DAY
        date format: 'YYYY-MM-DD HH:MM'
        """
        import time

        if not self.session_data:
            if not self.login():
                return None
        
        historic_param = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.smart_api.getCandleData(historic_param)
                if response and response.get("status"):
                    return response.get("data", [])
                else:
                    msg = response.get("message", "") if response else ""
                    err_code = response.get("errorCode", "") if response else ""
                    if err_code == "AG8001" or "invalid token" in msg.lower():
                        logger.warning("Angel One session token expired. Auto-renewing session via TOTP...")
                        if self.login():
                            time.sleep(1.0)
                            continue
                    if "exceeding access rate" in msg.lower() or "rate" in msg.lower():
                        sleep_time = 5.0 * attempt
                        logger.warning(f"Rate limited by SmartAPI. Sleeping {sleep_time:.1f}s before retry ({attempt}/{max_retries})...")
                        time.sleep(sleep_time)
                        continue
                    return None
            except Exception as e:
                err_str = str(e).lower()
                if "invalid token" in err_str or "ag8001" in err_str:
                    logger.warning("Token exception detected. Auto-renewing session via TOTP...")
                    if self.login():
                        time.sleep(2.0)
                        continue
                if "exceeding access rate" in err_str or "access denied" in err_str:
                    sleep_time = 5.0 * attempt
                    logger.warning(f"Rate limit triggered. Sleeping {sleep_time:.1f}s before retry ({attempt}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Error fetching candle data for {symbol_token}: {e}")
                    return None
                    
        return None

